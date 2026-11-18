"""Initiate the 3-node replica set (idempotent: safe to run more than once)."""
from pymongo.errors import OperationFailure

from common import NODES, PORT, banner, direct_client, replica_set_members, healthy_data_members, wait_until


def main():
    banner("Setup: initiate replica set rs0 (3 data-bearing members)")
    first = direct_client(NODES[0], timeout_ms=3000)

    print("Waiting for mongod on", NODES[0], "...")
    if not wait_until(lambda: first.admin.command("ping")["ok"] == 1, 90, 2):
        raise SystemExit("[FAIL] mongod did not start. Did you run: docker compose up -d ?")

    try:
        first.admin.command("replSetGetStatus")
        print("[OK] Replica set already initiated - reusing it.")
    except OperationFailure as e:
        if e.code != 94:  # 94 = NotYetInitialized
            raise
        cfg = {
            "_id": "rs0",
            # chaining off => every secondary replicates directly from the primary,
            # which makes the partition lab behave predictably
            "settings": {"chainingAllowed": False},
            "members": [{"_id": i, "host": f"{n}:{PORT}"} for i, n in enumerate(NODES)],
        }
        first.admin.command("replSetInitiate", cfg)
        print("[OK] replSetInitiate sent:", [m["host"] for m in cfg["members"]])

    def ready():
        members = replica_set_members(first)
        states = sorted(m["state"] for m in healthy_data_members(members))
        return states == sorted(["PRIMARY"] + ["SECONDARY"] * (len(NODES) - 1))

    print("Waiting for election and for all members to be healthy ...")
    if not wait_until(ready, 120, 2):
        raise SystemExit("[FAIL] Replica set did not become healthy in 120s. Try: docker compose logs mongo1")

    print()
    for m in replica_set_members(first):
        print(f"  {m['name']:<14} {m['state']:<10} health={m['health']}")
    print("\n[OK] Replica set rs0 is ready (1 PRIMARY + 2 SECONDARY).")
    first.close()


if __name__ == "__main__":
    main()
