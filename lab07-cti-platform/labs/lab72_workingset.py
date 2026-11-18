"""Lab 7.2 - working set analysis. Needs a real mongod (WiredTiger).
Usage: python labs/lab72_workingset.py [--docs 100000] [--reads 200000]  -> reports/lab72_report.md"""
import os, sys, random, time, argparse, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pymongo import MongoClient
ap = argparse.ArgumentParser(); ap.add_argument("--docs", type=int, default=100000)
ap.add_argument("--reads", type=int, default=200000); ap.add_argument("--batch", type=int, default=20000); a = ap.parse_args()
c = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017")); coll = c[os.getenv("MONGO_DB", "cti")].workingset_test

def cache():
    w = c.admin.command("serverStatus")["wiredTiger"]["cache"]
    return {"max": w["maximum bytes configured"], "used": w["bytes currently in the cache"],
            "req": w["pages requested from the cache"], "read": w["pages read into cache"]}

coll.drop(); pad = "x" * 1700            # ~2 KB per document
for i in range(0, a.docs, 5000):
    coll.insert_many([{"_id": n, "report": f"Annual security report #{n}", "year": 2015 + n % 11, "pad": pad} for n in range(i, i + 5000)])
stats = c[coll.database.name].command("collstats", "workingset_test")
b = cache(); L = ["# Lab 7.2 - Working set analysis", f"_Generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC_", "",
    f"- Documents: {a.docs}, avg object size: {stats['avgObjSize']} B, data size: {stats['size']/2**20:.1f} MiB, storage size: {stats['storageSize']/2**20:.1f} MiB",
    f"- WiredTiger cache max: {b['max']/2**20:.0f} MiB; in cache: {b['used']/2**20:.1f} MiB ({b['used']/b['max']:.1%} of cache)",
    f"- Collection data / cache max: {stats['size']/b['max']:.1%} -> {'fits' if stats['size'] < b['max']*0.8 else 'does NOT fit'} in cache", "",
    "## Random reads", "", "| Reads so far | Cache hit ratio (this batch) |", "|---|---|"]
done, prev = 0, cache()
while done < a.reads:
    for _ in range(a.batch): coll.find_one({"_id": random.randrange(a.docs)})
    done += a.batch; cur = cache()
    ratio = 1 - (cur["read"] - prev["read"]) / max(cur["req"] - prev["req"], 1); prev = cur
    L.append(f"| {done} | {ratio:.2%} |"); print(L[-1])
L += ["", "A rising ratio means the working set is being loaded; a persistently low ratio means data is larger than cache."]
os.makedirs("reports", exist_ok=True); open("reports/lab72_report.md", "w").write("\n".join(L) + "\n")
