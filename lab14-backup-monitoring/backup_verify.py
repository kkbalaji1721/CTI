#!/usr/bin/env python3
"""
Lab 14.2 - Automated backup and restore verification.

Sub-commands:
  backup          one mongodump into a timestamped directory (+ retention cleanup)
  schedule        run backup every hour with the 'schedule' library
  retention       delete backups older than N days (default 7)
  retention-demo  proves the 7-day policy with fake old backups
  verify          insert -> backup -> modify -> restore -> assert original data is back
  benchmark       time backup/restore for 1,000 / 10,000 / 100,000 documents, print RPO/RTO
"""
import argparse
import datetime
import os
import shutil
import subprocess
import time

import schedule
from pymongo import MongoClient
from tabulate import tabulate

DEFAULT_URI = "mongodb://localhost:27017/?directConnection=true"
LAB_DB = "labdb"


# ---------------------------------------------------------------- backup / restore
def run_backup(uri, out_root, db=None):
    """mongodump into out_root/backup_YYYYmmdd_HHMMSS. Returns (path, seconds)."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(out_root, f"backup_{ts}")
    os.makedirs(dest, exist_ok=True)
    cmd = ["mongodump", "--uri", uri, "--out", dest, "--quiet"]
    if db:
        cmd += ["--db", db]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    secs = time.time() - t0
    if r.returncode != 0:
        raise RuntimeError(f"mongodump failed (rc={r.returncode}): {r.stderr}")
    print(f"[backup] OK -> {dest} ({secs:.2f}s, return code {r.returncode})")
    return dest, secs


def run_restore(uri, backup_dir, ns_include=None):
    cmd = ["mongorestore", "--uri", uri, "--drop", "--quiet"]
    if ns_include:
        cmd.append(f"--nsInclude={ns_include}")
    cmd.append(backup_dir)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    secs = time.time() - t0
    if r.returncode != 0:
        raise RuntimeError(f"mongorestore failed (rc={r.returncode}): {r.stderr}")
    print(f"[restore] OK from {backup_dir} ({secs:.2f}s)")
    return secs


def apply_retention(out_root, days=7):
    """Delete backup_* folders older than `days` days (by creation/modification time)."""
    if not os.path.isdir(out_root):
        return []
    cutoff = time.time() - days * 86400
    folders = sorted(
        (d for d in os.listdir(out_root) if d.startswith("backup_")),
        key=lambda d: os.path.getmtime(os.path.join(out_root, d)),
    )
    deleted = []
    for d in folders:
        path = os.path.join(out_root, d)
        if os.path.getmtime(path) < cutoff:
            shutil.rmtree(path)
            deleted.append(d)
            print(f"[retention] deleted {d}")
    print(f"[retention] {len(deleted)} deleted, {len(folders) - len(deleted)} kept (policy: {days} days)")
    return deleted


# ---------------------------------------------------------------- commands
def cmd_backup(a):
    run_backup(a.uri, a.out, a.db)
    apply_retention(a.out, a.retention_days)


def cmd_schedule(a):
    def job():
        try:
            run_backup(a.uri, a.out, a.db)
            apply_retention(a.out, a.retention_days)
        except Exception as e:
            print(f"[schedule] job failed: {e}")

    job()  # run once immediately
    if a.every_minutes:
        schedule.every(a.every_minutes).minutes.do(job)
        print(f"[schedule] running every {a.every_minutes} minute(s) (Ctrl+C to stop)")
    else:
        schedule.every().hour.do(job)
        print("[schedule] running every hour (Ctrl+C to stop)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


def cmd_retention(a):
    apply_retention(a.out, a.retention_days)


def cmd_retention_demo(a):
    demo = os.path.join(a.out, "retention_demo")
    shutil.rmtree(demo, ignore_errors=True)
    os.makedirs(demo)
    for age in (10, 8, 6, 3, 0):
        p = os.path.join(demo, f"backup_age_{age}_days")
        os.makedirs(p)
        t = time.time() - age * 86400
        os.utime(p, (t, t))
    print("Before:", sorted(os.listdir(demo)))
    apply_retention(demo, a.retention_days)
    print("After :", sorted(os.listdir(demo)))
    shutil.rmtree(demo, ignore_errors=True)


def cmd_verify(a, n=1000):
    client = MongoClient(a.uri)
    coll = client[LAB_DB]["backup_test"]
    coll.drop()
    now = int(time.time())
    coll.insert_many([{"_id": i, "name": f"doc_{i}", "value": i * 2, "created_at": now, "verified": True}
                      for i in range(n)])
    original = {d["_id"]: d for d in coll.find()}
    print(f"[verify] inserted {coll.count_documents({})} documents")

    dest, _ = run_backup(a.uri, a.out, LAB_DB)

    coll.update_many({}, {"$set": {"verified": False}})
    print(f"[verify] modified data: {coll.count_documents({'verified': False})} docs now have verified=False")

    run_restore(a.uri, dest, ns_include=f"{LAB_DB}.backup_test")

    restored = {d["_id"]: d for d in coll.find()}
    mismatches = 0
    if len(restored) != len(original):
        print(f"ALERT: document count mismatch (expected {len(original)}, got {len(restored)})")
        mismatches += 1
    for _id, doc in original.items():
        if restored.get(_id) != doc:
            mismatches += 1
            print(f"ALERT: document {_id} differs after restore")
    if mismatches == 0:
        print(f"[verify] PASS - all {len(original)} documents identical to the pre-modification state")
    else:
        print(f"[verify] FAIL - {mismatches} mismatches")
    return mismatches == 0


def cmd_benchmark(a):
    client = MongoClient(a.uri)
    rows, payload = [], "x" * 900  # ~1 KB per doc -> 100k docs ~ 100 MB
    for size in (1000, 10000, 100000):
        client.drop_database(LAB_DB)
        coll = client[LAB_DB]["bench"]
        for start in range(0, size, 10000):
            end = min(start + 10000, size)
            coll.insert_many([{"_id": i, "payload": payload, "ts": time.time()} for i in range(start, end)])
        dest, backup_s = run_backup(a.uri, a.out, LAB_DB)
        size_mb = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(dest) for f in fs) / 1e6
        client.drop_database(LAB_DB)                       # simulate data loss
        restore_s = run_restore(a.uri, dest, ns_include=f"{LAB_DB}.bench")
        ok = coll.count_documents({}) == size
        rows.append([f"{size:,}", f"{size_mb:.1f}", f"{backup_s:.2f}", f"{restore_s:.2f}", "OK" if ok else "FAIL"])
    client.drop_database(LAB_DB)

    table = tabulate(rows, headers=["Documents", "Backup size (MB)", "Backup time (s)", "Restore time (s)", "Count check"],
                     tablefmt="github")
    biggest_restore = float(rows[-1][3])
    rto = biggest_restore + a.restart_seconds
    summary = (
        f"\n{table}\n\n"
        f"RPO = backup interval = 1 hour (at worst, 1 hour of data can be lost).\n"
        f"RTO = restore time + application restart time = {biggest_restore:.2f}s + {a.restart_seconds}s "
        f"= ~{rto:.0f}s for 100,000 documents.\n"
    )
    print(summary)
    with open(os.path.join(a.out, "benchmark_results.md"), "w") as f:
        f.write("# Backup / Restore benchmark\n" + summary)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["backup", "schedule", "retention", "retention-demo", "verify", "benchmark"])
    p.add_argument("--uri", default=DEFAULT_URI, help="MongoDB connection URI")
    p.add_argument("--out", default="/data/backups", help="backup output directory")
    p.add_argument("--db", default=None, help="back up only this database (default: all)")
    p.add_argument("--retention-days", type=int, default=7)
    p.add_argument("--every-minutes", type=int, default=0, help="schedule: use minutes instead of hourly (for demos)")
    p.add_argument("--restart-seconds", type=int, default=30, help="assumed application restart time for RTO")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    {"backup": cmd_backup, "schedule": cmd_schedule, "retention": cmd_retention,
     "retention-demo": cmd_retention_demo, "verify": cmd_verify, "benchmark": cmd_benchmark}[a.command](a)


if __name__ == "__main__":
    main()
