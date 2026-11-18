"""Lab 8.1 "Try it yourself" - add an ARBITER to the replica set.

Deploys  data node + data node + arbiter, proves the arbiter stores no data,
shows the arbiter's vote electing a new primary when the primary is stopped,
and explains why an arbiter is useful.

Run:  python lab_8_1_try_it_arbiter.py
Needs: Docker Desktop running, `pip install pymongo`.
"""

import os
import shutil
import socket
import subprocess
import sys
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, "docker-compose.yml")
PROJECT = "mongo-rs-lab"          # same project name in every activity folder
RS_NAME = "rs0"
# Members talk to each other by CONTAINER NAME on Docker's private network
# (e.g. mongo-rs0-1:27017).  Every container listens on 27017 inside Docker;
# Docker publishes them on localhost:27017 / 27018 / 27019 for this script.


# ----------------------------------------------------------------- helpers
def banner(text):
    line = "=" * 66
    print(f"\n{line}\n  {text}\n{line}")


def step(text):
    print(f"\n--- {text} ---")


def require_docker():
    if shutil.which("docker") is None:
        sys.exit("[ERROR] Docker is not on PATH. Install / start Docker Desktop.")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("[ERROR] Docker daemon is not running. Start Docker Desktop and retry.")


def compose(*args):
    """Run docker compose (v2) or docker-compose (v1) on this folder's file."""
    if subprocess.run(["docker", "compose", "version"],
                      capture_output=True).returncode == 0:
        base = ["docker", "compose"]
    elif shutil.which("docker-compose"):
        base = ["docker-compose"]
    else:
        sys.exit("[ERROR] Docker Compose not found.")
    cmd = base + ["-p", PROJECT, "-f", COMPOSE_FILE] + list(args)
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def direct(port, timeout_ms=3000):
    """Connect to ONE specific member (no replica-set discovery)."""
    return MongoClient("localhost", port, directConnection=True,
                       serverSelectionTimeoutMS=timeout_ms)


def port_in_use(port):
    s = socket.socket()
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def check_ports_free(ports, wait=8):
    """Stop early (with a clear message) if another program already uses a port."""
    deadline = time.time() + wait
    while True:
        busy = [p for p in ports if port_in_use(p)]
        if not busy:
            return
        if time.time() > deadline:
            sys.exit("[ERROR] Port(s) %s on this PC are already in use by another program,\n"
                     "        so the Docker containers cannot use them. Close that program\n"
                     "        (find it with:  netstat -ano | findstr :%d ) and run again."
                     % (", ".join(map(str, busy)), busy[0]))
        time.sleep(1)


def wait_for_mongod(ports, timeout=90):
    deadline = time.time() + timeout
    for p in ports:
        while True:
            try:
                cl = direct(p, 1500)
                cl.admin.command("ping")
                argv = cl.admin.command("getCmdLineOpts").get("argv", [])
                if "--replSet" not in argv:
                    sys.exit(f"[ERROR] localhost:{p} answers, but it is NOT one of this lab's "
                             "Docker containers\n        (another MongoDB is using that port). "
                             "Stop it or free the port, then run again.")
                print(f"  [OK] lab container on localhost:{p} is up")
                break
            except PyMongoError:
                if time.time() > deadline:
                    sys.exit(f"[ERROR] mongod on port {p} did not start in time.")
                time.sleep(1)


def run_mongosh_file(port, js_name, env=None):
    """Copy a .js file into the container and execute it with mongosh --file.

    `env` values are passed to the script by prepending `var KEY_ARG = "value";`
    to a temporary copy (the original .js file is not modified)."""
    import json
    import tempfile
    container = NODES[port]
    js_path = os.path.join(HERE, js_name)
    remote = f"/tmp/{js_name}"
    with open(js_path, encoding="utf-8") as f:
        code = f.read()
    prelude = "".join(f"var {k}_ARG = {json.dumps(v)};\n" for k, v in (env or {}).items())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_js = os.path.join(tmp, js_name)
        with open(tmp_js, "w", encoding="utf-8") as f:
            f.write(prelude + code)
        subprocess.run(["docker", "cp", tmp_js, f"{container}:{remote}"], check=True)
    cmd = ["docker", "exec", container, "mongosh", "--quiet",
           "--port", "27017", "--file", remote]
    print(f"$ mongosh --file {js_name}   (inside {container})")
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).rstrip()
    print(out)
    return out


def get_status():
    """replSetGetStatus from the first reachable member (None if not initiated)."""
    for p in NODES:
        try:
            return direct(p, 1500).admin.command("replSetGetStatus")
        except PyMongoError:
            continue
    return None


def split_host(name):
    """'mongo-rs0-2:27017' -> ('mongo-rs0-2', 27018)  (port = the localhost port)."""
    host = name.rsplit(":", 1)[0]
    for port, container in NODES.items():
        if container == host:
            return host, port
    return host, int(name.rsplit(":", 1)[1])


def primary_port(status):
    for m in status["members"]:
        if m["stateStr"] == "PRIMARY":
            return split_host(m["name"])[1]
    return None


def wait_for_primary(timeout=60, not_port=None):
    """Poll until a PRIMARY exists (optionally one different from not_port)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = get_status()
        if st:
            p = primary_port(st)
            if p and p != not_port:
                return p
        time.sleep(0.5)
    return None


def print_status(status):
    print(f"  {'MEMBER':<30}{'STATE':<26}{'HEALTH':<8}")
    for m in sorted(status["members"], key=lambda x: x["_id"]):
        health = "1 (up)" if m["health"] == 1 else "0 (down)"
        print(f"  {m['name']:<30}{m['stateStr']:<26}{health:<8}")


# ---------------------------------------------------------------- lab code
from pymongo import WriteConcern

NODES = {28017: "mongo-rs0-1", 28018: "mongo-rs0-2", 28019: "mongo-arbiter"}
JS_FILE = "lab_8_1_arbiter.js"
ARBITER_PORT = 28019

WHY_ARBITER = """
WHY AN ARBITER IS USEFUL
  * Elections need a strict MAJORITY of voting members. With only 2 voters, losing
    either one leaves 1 of 2 votes -> no majority -> no primary -> no writes.
  * Adding a 3rd voter makes the count ODD (3). Now any 2 members form a majority,
    so if the primary dies the surviving secondary + arbiter can elect a new primary.
  * An arbiter does not replicate data: it keeps no copy of your collections and no
    oplog, so it needs no storage for your data and very little RAM/CPU. You get the
    voting benefit of a 3rd member without paying for a full data-bearing node
    (storage for the data + bigger hardware + backups).
  * Trade-off: an arbiter holds no copy of the data, so it adds no redundancy, and
    w:"majority" writes cannot be acknowledged while a data node is down. For
    production prefer 3 data-bearing members; arbiters are a cost-saving compromise.
"""


def count_docs(container):
    """Number of documents in labdb.arbiter_test as seen by mongosh inside a container."""
    r = subprocess.run(
        ["docker", "exec", container, "mongosh", "--quiet", "--port", "27017", "--eval",
         "db.getMongo().setReadPref('secondaryPreferred');"
         "print('COUNT=' + db.getSiblingDB('labdb').arbiter_test.countDocuments({}))"],
        capture_output=True, text=True)
    text = r.stdout + r.stderr
    return text.split("COUNT=")[-1].split()[0] if "COUNT=" in text else None


def main():
    banner("Lab 8.1 Try-it-yourself - Replica Set with an ARBITER")
    require_docker()

    step("Step 1: Start Primary-candidate, Secondary-candidate and Arbiter containers")
    compose("down", "-v", "--remove-orphans")
    check_ports_free(NODES.keys())
    compose("up", "-d")
    wait_for_mongod(NODES.keys())

    step("Step 2: Initialise the replica set (member 2 is arbiterOnly) via mongosh")
    run_mongosh_file(28017, JS_FILE)

    step("Step 3: Member roles from PyMongo")
    p_port = wait_for_primary()
    if p_port is None:
        sys.exit("[ERROR] No primary was elected.")
    print_status(get_status())

    step("Step 4: Prove the arbiter stores NO data")
    hello = direct(ARBITER_PORT).admin.command("hello")
    print(f"  hello.arbiterOnly on localhost:{ARBITER_PORT} -> {hello.get('arbiterOnly')}")

    doc = {"message": "Hello from replica set with arbiter", "lab": "8.1-arbiter",
           "padding": "x" * 200000}                       # ~200 KB so sizes differ
    direct(p_port).labdb.arbiter_test.insert_one(doc)
    for _ in range(3):
        direct(p_port).labdb.arbiter_test.insert_one({"padding": "x" * 200000})
    print(f"  Inserted test data on PRIMARY localhost:{p_port}")
    time.sleep(2)

    try:
        direct(ARBITER_PORT).labdb.arbiter_test.find_one()
        print("  [UNEXPECTED] arbiter returned data")
    except PyMongoError as e:
        print(f"  [OK] reading from the arbiter is refused: {str(e)[:90]}")

    print("\n  Documents stored in labdb.arbiter_test, member by member:")
    for port, name in NODES.items():
        if port == ARBITER_PORT:
            print(f"    {name:<16}  no data - the arbiter refuses reads (shown above)")
        else:
            print(f"    {name:<16}  {count_docs(name)} document(s)   (data-bearing)")

    step("Step 5: w:'majority' write with all 3 voters healthy")
    r = direct(p_port).labdb.arbiter_test.with_options(
        write_concern=WriteConcern("majority", wtimeout=5000)
    ).insert_one({"note": "majority write"})
    print(f"  [OK] majority write acknowledged, _id={r.inserted_id}")

    step("Step 6: Stop the PRIMARY - can the secondary + arbiter elect a new one?")
    old_container = NODES[p_port]
    compose_stop = ["docker", "stop", old_container]
    print("$ " + " ".join(compose_stop))
    subprocess.run(compose_stop, check=True, capture_output=True)
    new_port = None
    deadline = time.time() + 60
    survivor = [p for p in (28017, 28018) if p != p_port][0]
    while time.time() < deadline:
        try:
            st = direct(survivor, 1500).admin.command("replSetGetStatus")
            if primary_port(st) == survivor:
                new_port = survivor
                break
        except PyMongoError:
            pass
        time.sleep(1)
    if new_port:
        print(f"  [OK] localhost:{new_port} was elected PRIMARY with the arbiter's vote")
        print_status(direct(new_port).admin.command("replSetGetStatus"))
    else:
        print("  [FAIL] no new primary within 60 s")

    step("Step 7: With one data node DOWN - normal write vs w:'majority' write")
    target = new_port or survivor
    deadline = time.time() + 30                      # a new primary needs a moment
    while time.time() < deadline:                    # before it accepts writes
        try:
            if direct(target, 1500).admin.command("hello").get("isWritablePrimary"):
                break
        except PyMongoError:
            pass
        time.sleep(0.5)
    try:
        direct(target).labdb.arbiter_test.insert_one({"note": "w:1 write while degraded"})
        print("  [OK] normal (w:1) write succeeded - the set still accepts writes")
    except PyMongoError as e:
        print(f"  [FAIL] normal write failed: {str(e)[:100]}")
    try:
        direct(target).labdb.arbiter_test.with_options(
            write_concern=WriteConcern("majority", wtimeout=3000)
        ).insert_one({"note": "majority write while degraded"})
        print("  w:'majority' write was acknowledged")
    except PyMongoError as e:
        print(f"  [EXPECTED] w:'majority' write NOT acknowledged ({type(e).__name__}): "
              f"{str(e)[:80]}")
        print("  -> the arbiter votes in elections, but it cannot hold or confirm data.")

    step("Step 8: Restart the stopped node and let it rejoin")
    subprocess.run(["docker", "start", old_container], check=True, capture_output=True)
    time.sleep(15)
    st = get_status()
    if st:
        print_status(st)

    print(WHY_ARBITER)
    banner("Lab 8.1 Try-it-yourself complete")


if __name__ == "__main__":
    main()
