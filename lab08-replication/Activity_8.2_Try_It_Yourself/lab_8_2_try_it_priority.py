"""Lab 8.2 "Try it yourself" - priorities and election prediction.

Sets priorities 27017=1, 27018=5, 27019=3, PREDICTS the next primary before
rs.stepDown(), then runs stepDown and verifies the prediction.

Run:  python lab_8_2_try_it_priority.py
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
NODES = {28017: "mongo-rs0-1", 28018: "mongo-rs0-2", 28019: "mongo-rs0-3"}
JS_FILE = "lab_8_2_priority.js"

# Priorities we will configure (port -> priority)
PRIORITIES = {28017: 1, 28018: 5, 28019: 3}


def ensure_replica_set():
    """Re-use a running 3-data-node replica set; otherwise deploy a fresh one."""
    st = get_status()
    if st and primary_port(st) and len(st["members"]) == 3 \
            and all(m["stateStr"] != "ARBITER" for m in st["members"]):
        print("  Re-using the replica set that is already running.")
        return
    print("  No suitable replica set found - deploying a fresh one.")
    compose("down", "-v", "--remove-orphans")
    check_ports_free(NODES.keys())
    compose("up", "-d")
    wait_for_mongod(NODES.keys())
    cfg = {"_id": RS_NAME,
           "members": [{"_id": i, "host": f"{name}:27017"}
                       for i, name in enumerate(NODES.values())]}
    direct(28017).admin.command("replSetInitiate", cfg)
    if wait_for_primary() is None:
        sys.exit("[ERROR] No primary was elected.")


def predict_next_primary(current_primary):
    """Rule: among healthy, voting, data-bearing SECONDARIES, the one with the
    HIGHEST priority wins the next election. (The old primary is excluded: it is
    frozen for the stepDown period.)"""
    p = direct(current_primary)
    cfg = p.admin.command("replSetGetConfig")["config"]
    status = p.admin.command("replSetGetStatus")
    healthy = {m["name"] for m in status["members"]
               if m["health"] == 1 and m["stateStr"] == "SECONDARY"}
    candidates = [(m["priority"], m["host"]) for m in cfg["members"]
                  if m["host"] in healthy and m["priority"] > 0
                  and not m.get("arbiterOnly")]
    candidates.sort(reverse=True)
    return candidates, split_host(candidates[0][1])[1]


def main():
    banner("Lab 8.2 Try-it-yourself - Priorities and Election Prediction")
    require_docker()

    step("Step 1: Make sure the 3-node replica set is running")
    ensure_replica_set()
    print_status(get_status())

    step("Step 2: Configure priorities  mongo-rs0-1=1   mongo-rs0-2=5   mongo-rs0-3=3")
    p = primary_port(get_status())
    run_mongosh_file(p, JS_FILE, env={"PHASE": "reconfig"})

    step("Step 3: Wait for the highest-priority member (mongo-rs0-2, priority 5) to become PRIMARY")
    print("  (MongoDB performs a 'priority takeover' automatically; up to 90 s)")
    target = max(PRIORITIES, key=PRIORITIES.get)
    deadline = time.time() + 90
    while time.time() < deadline:
        st = get_status()
        if st and primary_port(st) == target:
            break
        time.sleep(2)
    st = get_status()
    print_status(st)
    current = primary_port(st)
    print(f"\n  Current PRIMARY: localhost:{current}  (priority {PRIORITIES[current]})")

    step("Step 4: PREDICTION - made BEFORE running stepDown()")
    candidates, predicted = predict_next_primary(current)
    print("  Healthy secondaries (priority, host):")
    for pri, host in candidates:
        print(f"    priority {pri}  {host}")
    print(f"\n  >>> PREDICTION: localhost:{predicted} "
          f"(priority {PRIORITIES[predicted]}) will win the election")

    step("Step 5: Run rs.stepDown() and verify")
    run_mongosh_file(current, JS_FILE, env={"PHASE": "stepdown"})
    actual = wait_for_primary(not_port=current, timeout=40)
    print(f"\n  PREDICTED : localhost:{predicted}")
    print(f"  ACTUAL    : localhost:{actual}")
    print("  RESULT    : " + ("PREDICTION CORRECT" if actual == predicted
                              else "PREDICTION WRONG - see notes below"))

    step("Step 6: Priority takeover - does the top-priority node reclaim PRIMARY?")
    print("  localhost:%d is frozen for 20 s after stepDown, then it should take over" % current)
    t0 = time.time()
    got_back = False
    while time.time() - t0 < 90:
        st = get_status()
        if st and primary_port(st) == current:
            got_back = True
            break
        time.sleep(2)
    if got_back:
        print(f"  [OK] localhost:{current} (priority {PRIORITIES[current]}) became "
              f"PRIMARY again after ~{time.time() - t0:.0f} s")
    else:
        print("  Original primary did not reclaim the role within 90 s (not an error:"
              " takeover also needs the node to be fully caught up).")
    print_status(get_status())

    print("""
NOTES
  * priority is a BIAS, not a guarantee: only healthy, up-to-date, non-frozen
    members can win. A priority-0 member can never become primary.
  * The member that stepped down is ineligible for the stepDown period, so the
    winner is the highest-priority REMAINING member.
""")
    banner("Lab 8.2 Try-it-yourself complete")


if __name__ == "__main__":
    main()
