"""Activity 7.2 - report WiredTiger cache hit ratio every 10 s AND look for new threat reports
in jacobdjwilson/awesome-annual-security-reports that are not yet in the DB (collection `reports`).
Usage: python labs/lab72_monitor.py [--once]"""
import os, sys, re, time
import requests
from pymongo import MongoClient
README = "https://raw.githubusercontent.com/jacobdjwilson/awesome-annual-security-reports/main/README.md"
c = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017")); d = c[os.getenv("MONGO_DB", "cti")]

def snap():
    w = c.admin.command("serverStatus")["wiredTiger"]["cache"]
    return w["pages requested from the cache"], w["pages read into cache"], w["bytes currently in the cache"]

def new_reports():
    try: md = requests.get(README, timeout=20).text
    except Exception as e: print("  [reports] fetch failed:", e); return
    found = {u: t for t, u in re.findall(r"\[([^\]]{4,})\]\((https?://[^)\s]+)\)", md) if "github.com/jacobdjwilson" not in u}
    known = {r["_id"] for r in d.reports.find({}, {"_id": 1})}
    fresh = [{"_id": u, "title": t} for u, t in found.items() if u not in known]
    if fresh and known: print(f"  [reports] {len(fresh)} NEW:", *[f['title'] for f in fresh[:5]], sep="\n    ")
    elif fresh: print(f"  [reports] first run, storing {len(fresh)} baseline reports")
    if fresh: d.reports.insert_many(fresh)

prev, tick = snap(), 0
while True:
    if tick % 6 == 0: new_reports()            # GitHub check once a minute
    time.sleep(10 if "--once" not in sys.argv else 1); cur = snap(); tick += 1
    req, rd = cur[0] - prev[0], cur[1] - prev[1]
    print(f"{time.strftime('%H:%M:%S')} cache={cur[2]/2**20:.1f} MiB hit_ratio={(1 - rd/req) if req else 1:.2%} (requests={req}, disk reads={rd})", flush=True)
    prev = cur
    if "--once" in sys.argv: break
