#!/usr/bin/env python3
"""
Bonus (chapter topic: Durability & Journaling).
Modes:  inspect | write | verify
Used by durability_demo.sh, which kill -9's mongod between 'write' and 'verify'.
"""
import os
import sys

from pymongo import WriteConcern

from common import DB_NAME, Checker, banner, get_client

COLL = "durability_demo"
EXPECTED = {"journaled-write", "committed-txn-1", "committed-txn-2"}


def inspect(client):
    banner("Journaling / storage-engine information")
    ss = client.admin.command("serverStatus")
    print("  storageEngine:", ss.get("storageEngine"))
    wtlog = ss.get("wiredTiger", {}).get("log", {})
    for k in ("log sync operations", "log write operations", "log flush operations",
              "log records processed by log scan"):
        if k in wtlog:
            print(f"  wiredTiger.log['{k}'] = {wtlog[k]}")
    jdir = "/data/db/journal"
    if os.path.isdir(jdir):
        print(f"  journal directory {jdir}:")
        for name in sorted(os.listdir(jdir)):
            print(f"    {name}  ({os.path.getsize(os.path.join(jdir, name))} bytes)")
    print("  (WiredTiger journaling is always on; journal is flushed ~every 100 ms,"
          " or immediately for j:true / w:'majority' writes.)")


def write(client):
    banner("WRITE phase: three durable writes + one UNCOMMITTED transaction")
    db = client[DB_NAME]
    db.drop_collection(COLL)
    db.create_collection(COLL)

    durable = db.get_collection(COLL, write_concern=WriteConcern(w=1, j=True))
    durable.insert_one({"_id": "journaled-write"})
    print("  inserted 'journaled-write' with writeConcern {w:1, j:true}")

    with client.start_session() as s:
        s.start_transaction(write_concern=WriteConcern("majority"))
        db[COLL].insert_one({"_id": "committed-txn-1"}, session=s)
        db[COLL].insert_one({"_id": "committed-txn-2"}, session=s)
        s.commit_transaction()
    print("  committed a transaction with 2 inserts (writeConcern majority)")

    s = client.start_session()
    s.start_transaction()
    db[COLL].insert_one({"_id": "UNCOMMITTED-txn"}, session=s)
    print("  started a transaction, inserted 'UNCOMMITTED-txn' and exited WITHOUT commit")
    sys.stdout.flush()
    os._exit(0)  # no commit, no abort, no cleanup


def verify(client):
    banner("VERIFY phase: after kill -9 + restart + journal recovery")
    chk = Checker()
    ids = {d["_id"] for d in client[DB_NAME][COLL].find()}
    print("  documents found:", sorted(ids))
    chk.check(EXPECTED <= ids, "all journaled / committed writes survived the crash (DURABILITY)")
    chk.check("UNCOMMITTED-txn" not in ids, "uncommitted transaction left no trace (ATOMICITY)")
    sys.exit(chk.summary("Durability summary"))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "inspect"
    c = get_client()
    {"inspect": inspect, "write": write, "verify": verify}[mode](c)
