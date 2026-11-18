"""Lab 9.2 - Simulate a Network Partition

Uses `docker network disconnect/connect` to isolate secondaries of a 3-node
replica set, writes with w:1 and w:majority at each stage, watches the replica
set with an observer thread (the Lab 8.2 "failover observer" idea), and records
a timestamped timeline.

Stages
  1  Baseline            - healthy set, all writes succeed
  2  Isolate secondary 1 - primary + 1 secondary = majority -> everything still works
  3  Isolate secondary 2 - primary alone, NO majority -> w:majority times out,
                           primary steps down, set becomes read-only
  4  Reconnect both      - election, rejoin, catch-up, check what happened to the
                           writes made without a majority
"""
import datetime
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pymongo import MongoClient, ReadPreference, WriteConcern
from pymongo.errors import (NotPrimaryError, PyMongoError, ServerSelectionTimeoutError,
                            WriteConcernError, WTimeoutError)
from pymongo.read_concern import ReadConcern

from common import NODES, PORT, RS_URI, banner, direct_client, save_json

DB, COLL = "partition_lab", "events"
NETWORK = os.getenv("LAB_NETWORK", "lab09_net")

T0 = time.time()
EVENTS, OPS = [], []
LOCK = threading.Lock()
DIRECT = {}


# ---------------------------------------------------------------- logging
def log(msg, kind="info"):
    with LOCK:
        t = time.time() - T0
        EVENTS.append({"t": round(t, 1), "clock": time.strftime("%H:%M:%S"), "kind": kind, "event": msg})
        print(f"[T+{t:6.1f}s] {msg}", flush=True)


def now():
    return time.time() - T0


# ---------------------------------------------------------------- docker
def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def net_disconnect(node):
    r = docker("network", "disconnect", NETWORK, node)
    if r.returncode != 0:
        raise RuntimeError(f"docker network disconnect {node} failed: {r.stderr.strip()}")
    log(f"NETWORK: {node} DISCONNECTED from {NETWORK}  <-- partition", "partition")


def net_connect(node):
    r = docker("network", "connect", "--alias", node, NETWORK, node)
    if r.returncode != 0 and "already exists" not in r.stderr:
        raise RuntimeError(f"docker network connect {node} failed: {r.stderr.strip()}")
    if r.returncode == 0:
        log(f"NETWORK: {node} RECONNECTED to {NETWORK}  <-- partition healed", "partition")


def own_view(node):
    """What the node itself believes (runs mongosh INSIDE the container, so it works while partitioned)."""
    js = "print(JSON.stringify(rs.status().members.map(m=>({n:m.name,s:m.stateStr,h:m.health}))))"
    r = docker("exec", node, "mongosh", "--quiet", "--port", str(PORT), "--eval", js)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except ValueError:
        return None


def log_own_view(node, why):
    view = own_view(node)
    if view is None:
        log(f"{node}'s own view ({why}): could not be read")
        return
    txt = ", ".join(f"{m['n'].split(':')[0]}={m['s']}" for m in view)
    log(f"{node}'s OWN view ({why}): {txt}")


# ---------------------------------------------------------------- state helpers
def state_of(node):
    try:
        h = DIRECT[node].admin.command("hello")
        if h.get("isWritablePrimary"):
            return "PRIMARY"
        if h.get("secondary"):
            return "SECONDARY"
        return "OTHER"
    except Exception:
        return "UNREACHABLE"


def find_primary():
    for n in NODES:
        if state_of(n) == "PRIMARY":
            return n
    return None


def sees_primary(node):
    """Does `node` currently see some member as PRIMARY in its own replica-set status?"""
    try:
        st = DIRECT[node].admin.command("replSetGetStatus")
        return any(m["stateStr"] == "PRIMARY" for m in st["members"])
    except Exception:
        return False


def log_members_from(node, why):
    st = DIRECT[node].admin.command("replSetGetStatus")
    for m in st["members"]:
        name = m["name"].split(":")[0]
        log(f"rs.status() on {node} ({why}): {name:<7} {m['stateStr']:<28} health={m['health']}")


class Observer(threading.Thread):
    """Polls every node once per second and logs every state change (Lab 8.2 style)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = threading.Event()
        self.last = {}

    def run(self):
        with ThreadPoolExecutor(max_workers=len(NODES)) as pool:
            while not self.stop_flag.is_set():
                states = dict(zip(NODES, pool.map(state_of, NODES)))
                for n, s in states.items():
                    old = self.last.get(n)
                    if old is None:
                        log(f"OBSERVER: {n} is {s}", "observer")
                    elif old != s:
                        log(f"OBSERVER: {n} {old} -> {s}", "observer")
                self.last = states
                self.stop_flag.wait(1.0)


# ---------------------------------------------------------------- writes
def do_insert(client, phase, tag, w, wtimeout=5000, via="replica-set client"):
    wc = WriteConcern(w=w, wtimeout=wtimeout)
    col = client[DB].get_collection(COLL, write_concern=wc)
    wlabel = f"w:{w}"
    t = time.perf_counter()
    outcome, detail = "SUCCESS", ""
    try:
        col.insert_one({"phase": phase, "tag": tag, "w": str(w),
                        "at": datetime.datetime.now(datetime.timezone.utc)})
    except WTimeoutError:
        outcome = "TIMEOUT"
        detail = "write applied on primary but NOT acknowledged by a majority"
    except WriteConcernError as e:
        outcome, detail = "WRITE-CONCERN ERROR", str(e)[:100]
    except NotPrimaryError:
        outcome, detail = "REJECTED", "node is not primary"
    except ServerSelectionTimeoutError:
        outcome, detail = "FAILED", "no primary available"
    except PyMongoError as e:
        outcome, detail = "FAILED", type(e).__name__
    ms = (time.perf_counter() - t) * 1000
    OPS.append({"t": round(now(), 1), "phase": phase, "write_concern": wlabel, "tag": tag,
                "via": via, "outcome": outcome, "ms": round(ms, 1), "detail": detail})
    log(f"INSERT {wlabel:<11} [{tag}] via {via}: {outcome} in {ms:.0f} ms" + (f"  ({detail})" if detail else ""), "write")
    return outcome


def count_tags(client, tag, read_concern=None, pref=None):
    kw = {}
    if read_concern:
        kw["read_concern"] = read_concern
    if pref:
        kw["read_preference"] = pref
    return client[DB].get_collection(COLL, **kw).count_documents({"tag": tag})


# ---------------------------------------------------------------- main
def main():
    global T0
    banner("Lab 9.2: Simulate a Network Partition")

    if docker("version", "--format", "{{.Client.Version}}").returncode != 0:
        raise SystemExit("[FAIL] Docker CLI not usable. The lab service must mount /var/run/docker.sock.")
    for n in NODES:
        if docker("inspect", n).returncode != 0:
            raise SystemExit(f"[FAIL] Container '{n}' not found. Run: docker compose up -d  and  lab setup")

    for n in NODES:
        DIRECT[n] = direct_client(n)
    rs = MongoClient(RS_URI, serverSelectionTimeoutMS=5000)
    T0 = time.time()
    observer = None
    disconnected = set()

    try:
        # ---------------- Stage 0: pre-checks
        primary = find_primary()
        if not primary:
            raise SystemExit("[FAIL] No primary found. Run: lab setup")
        secondaries = [n for n in NODES if n != primary]
        s1, s2 = secondaries
        log(f"Replica set rs0: PRIMARY={primary}, SECONDARIES={s1}, {s2}", "stage")
        log_members_from(primary, "before partition")
        rs[DB].drop_collection(COLL)
        rs[DB].create_collection(COLL)

        observer = Observer()
        observer.start()
        time.sleep(2)

        # ---------------- Stage 1: baseline
        log("STAGE 1: baseline - healthy replica set", "stage")
        for i in range(3):
            do_insert(rs, "1-baseline", f"P1_w1_{i}", 1)
        for i in range(3):
            do_insert(rs, "1-baseline", f"P1_wmajority_{i}", "majority")

        # ---------------- Stage 2: isolate first secondary
        log(f"STAGE 2: isolate secondary {s1} (primary + {s2} still form a majority)", "stage")
        net_disconnect(s1); disconnected.add(s1)
        log("waiting 15s so the replica set notices the missing member ...")
        time.sleep(15)
        log_members_from(primary, f"{s1} partitioned")
        log_own_view(s1, "isolated node")
        for i in range(3):
            do_insert(rs, "2-one-secondary-down", f"P2_w1_{i}", 1)
        for i in range(3):
            do_insert(rs, "2-one-secondary-down", f"P2_wmajority_{i}", "majority")

        # ---------------- Stage 3: isolate second secondary -> no majority
        log(f"STAGE 3: isolate secondary {s2} too -> {primary} is alone, NO majority possible", "stage")
        net_disconnect(s2); disconnected.add(s2)
        t_lost_majority = now()
        do_insert(rs, "3-no-majority", "P3_w1_no_majority", 1)
        do_insert(rs, "3-no-majority", "P3_wmajority_marker", "majority", wtimeout=5000)

        log(f"waiting for {primary} to step down (it cannot see a majority) ...")
        t_stepdown = None
        while now() - t_lost_majority < 90:
            if state_of(primary) != "PRIMARY":
                t_stepdown = now()
                break
            time.sleep(0.5)
        if t_stepdown is None:
            log("WARNING: primary did not step down within 90s", "warn")
        else:
            log(f"*** {primary} STEPPED DOWN at T+{t_stepdown:.1f}s "
                f"({t_stepdown - t_lost_majority:.1f}s after majority was lost) -> no PRIMARY, set is read-only ***", "stepdown")
        log_own_view(s2, "isolated node")

        do_insert(DIRECT[primary], "3-no-majority", "P3_w1_after_stepdown", 1,
                  via=f"direct to {primary} (former primary)")
        do_insert(rs, "3-no-majority", "P3_w1_after_stepdown_rs", 1, wtimeout=5000)
        try:
            n_docs = DIRECT[primary].get_database(DB, read_preference=ReadPreference.SECONDARY_PREFERRED)[COLL].count_documents({})
            log(f"READ on {primary} (now SECONDARY) still works: {n_docs} documents visible -> set is read-only, not down")
        except PyMongoError as e:
            log(f"READ on {primary} failed: {type(e).__name__}")

        # ---------------- Stage 4: heal
        log("STAGE 4: reconnect both secondaries and watch the election", "stage")
        t_heal = now()
        net_connect(s1); disconnected.discard(s1)
        net_connect(s2); disconnected.discard(s2)

        first_seen, elected, former_sees = {}, None, None
        while now() - t_heal < 150:
            for n in NODES:
                st = state_of(n)
                if n in (s1, s2) and n not in first_seen and st != "UNREACHABLE":
                    first_seen[n] = now()
                    log(f"{n} reachable again (state {st}) at T+{now():.1f}s ({now() - t_heal:.1f}s after reconnect)", "rejoin")
                if st == "PRIMARY" and elected is None:
                    elected = (n, now())
                    log(f"*** NEW PRIMARY ELECTED: {n} at T+{now():.1f}s ({now() - t_heal:.1f}s after reconnect) ***", "election")
            if former_sees is None and sees_primary(primary):
                former_sees = now()
                log(f"former primary {primary} REJOINED (it now sees a primary) at T+{former_sees:.1f}s", "rejoin")
            if elected and len(first_seen) == 2 and former_sees:
                break
            time.sleep(1)
        if not elected:
            log("WARNING: no primary elected within 150s", "warn")

        new_primary = elected[0] if elected else None
        regained = (new_primary == primary)
        if new_primary:
            log(f"former primary {primary} {'REGAINED' if regained else 'did NOT regain'} the primary role "
                f"(new primary = {new_primary})", "election")

        # wait until every member has caught up
        t_caught = None
        if new_primary:
            log("waiting for all members to be healthy and fully caught up ...")
            end = now() + 90
            while now() < end:
                try:
                    st = DIRECT[new_primary].admin.command("replSetGetStatus")
                    ok = all(m["health"] == 1 and m["stateStr"] in ("PRIMARY", "SECONDARY") for m in st["members"])
                    optimes = {m["optimeDate"] for m in st["members"]} if ok else set()
                    if ok and len(optimes) == 1:
                        t_caught = now()
                        break
                except PyMongoError:
                    pass
                time.sleep(1)
            if t_caught:
                log(f"all 3 members healthy and caught up at T+{t_caught:.1f}s", "rejoin")
                log_members_from(new_primary, "after recovery")
            else:
                log("WARNING: members did not fully converge in 90s", "warn")
            time.sleep(3)

        # ---------------- Stage 5: what survived?
        log("STAGE 5: which writes survived?", "stage")
        survived = {}
        majority_rc = ReadConcern("majority")
        for tag in ("P3_w1_no_majority", "P3_wmajority_marker"):
            try:
                survived[tag] = count_tags(rs, tag, read_concern=majority_rc) > 0
            except PyMongoError as e:
                survived[tag] = None
                log(f"could not check {tag}: {type(e).__name__}")
        for tag, ok in survived.items():
            verdict = "SURVIVED (replicated to a majority)" if ok else ("ROLLED BACK (lost)" if ok is False else "unknown")
            log(f"write [{tag}] made while no majority existed: {verdict}", "result")
        per_node = {}
        for n in NODES:
            try:
                per_node[n] = DIRECT[n].get_database(DB, read_preference=ReadPreference.SECONDARY_PREFERRED)[COLL].count_documents({})
            except PyMongoError:
                per_node[n] = None
        log("document count per node: " + ", ".join(f"{n}={c}" for n, c in per_node.items()) + "  (equal => converged)")

        summary = {
            "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "initial_primary": primary, "isolated_first": s1, "isolated_second": s2,
            "t_lost_majority": round(t_lost_majority, 1),
            "t_stepdown": round(t_stepdown, 1) if t_stepdown else None,
            "stepdown_after_s": round(t_stepdown - t_lost_majority, 1) if t_stepdown else None,
            "t_heal": round(t_heal, 1),
            "new_primary": new_primary,
            "election_after_heal_s": round(elected[1] - t_heal, 1) if elected else None,
            "former_primary_regained_role": regained if new_primary else None,
            "former_primary_rejoined_after_heal_s": round(former_sees - t_heal, 1) if former_sees else None,
            "caught_up_after_heal_s": round(t_caught - t_heal, 1) if t_caught else None,
            "writes_survived": survived, "docs_per_node": per_node,
            "events": EVENTS, "operations": OPS,
        }
        save_json("lab_02_results.json", summary)
        with open(os.path.join(os.getenv("RESULTS_DIR", "/results"), "lab_02_timeline.txt"), "w", encoding="utf-8") as f:
            for e in EVENTS:
                f.write(f"[T+{e['t']:6.1f}s {e['clock']}] {e['event']}\n")
        print("\n[OK] Timeline saved to results/lab_02_timeline.txt and lab_02_results.json")
    finally:
        # ALWAYS heal the network, even if something above crashed
        for n in list(disconnected):
            docker("network", "connect", "--alias", n, NETWORK, n)
        if observer:
            observer.stop_flag.set()
        rs.close()

    banner("Lab 9.2 Complete")


if __name__ == "__main__":
    main()
