"""Lab 13.1 step 4: continuous writes/reads through a primary step-down.

Usage:  python tools/failover_test.py [--duration 40] [--stepdown-after 8]
A background thread calls replSetStepDown on the primary; the main loop keeps
writing (w=majority, retryable writes) and reading, and reports any gap.
"""
import argparse, os, threading, time
from datetime import datetime, timezone
from pymongo import MongoClient, WriteConcern
from pymongo.errors import PyMongoError

p = argparse.ArgumentParser()
p.add_argument("--duration", type=int, default=40)
p.add_argument("--stepdown-after", type=int, default=8, help="seconds before stepping down (0 = never)")
a = p.parse_args()

URI = os.getenv("MONGO_URI") or (
    f"mongodb://{os.getenv('MONGO_ADMIN_USER','admin')}:{os.getenv('MONGO_ADMIN_PASSWORD','AdminPass123')}"
    "@prod-mongo-1:27017,prod-mongo-2:27017,prod-mongo-3:27017/?replicaSet=rs0&authSource=admin")

client = MongoClient(URI, retryWrites=True, retryReads=True, serverSelectionTimeoutMS=30000)
coll = client.lab13.failover_test.with_options(write_concern=WriteConcern(w="majority"))
ts = lambda: datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]

def stepdown():
    time.sleep(a.stepdown_after)
    admin = MongoClient(URI, serverSelectionTimeoutMS=30000).admin
    print(f"\n[{ts()}] >>> rs.stepDown() on {admin.client.primary}\n", flush=True)
    try:
        admin.command("replSetStepDown", 20, secondaryCatchUpPeriodSecs=10)
    except PyMongoError as e:           # the connection is closed by the stepping-down primary
        print(f"[{ts()}] stepDown returned: {type(e).__name__} (expected)", flush=True)

if a.stepdown_after > 0:
    threading.Thread(target=stepdown, daemon=True).start()

ok = fail = 0; last_primary = None; last_ok = time.time(); max_gap = 0.0
end = time.time() + a.duration; seq = 0
while time.time() < end:
    seq += 1
    try:
        coll.insert_one({"seq": seq, "ts": datetime.now(timezone.utc)})
        n = coll.count_documents({})
        ok += 1
        now = time.time(); max_gap = max(max_gap, now - last_ok); last_ok = now
        prim = client.primary
        if prim != last_primary:
            print(f"[{ts()}] primary is now {prim}", flush=True); last_primary = prim
        print(f"[{ts()}] write #{seq} OK   docs={n}", flush=True)
    except PyMongoError as e:
        fail += 1
        print(f"[{ts()}] write #{seq} FAILED: {type(e).__name__}", flush=True)
    time.sleep(0.5)

print(f"\nSUMMARY  successful writes={ok}  failed={fail}  longest gap={max_gap:.1f}s")
print("RESULT:", "PASS - writes resumed after failover" if ok > 0 and last_ok > end - 10 else "CHECK LOGS")
