"""Lab 9.1 - Measure Write Concern Latency (+ Activity: j:true vs j:false)

Inserts 1,000 small documents under each write concern:
    w:1, w:majority, w:all      (each with j:false and j:true)
and reports total time, average latency per write, P50 and P99.

NOTE ON "w:all": MongoDB has no literal w:"all" option. "All members" is
expressed as w:<number of data-bearing members>. This replica set has 3, so
w:all == w:3.
"""
import math
import os
import statistics
import time

from pymongo import MongoClient, WriteConcern

from common import RS_URI, banner, replica_set_members, healthy_data_members, save_json

DOC_COUNT = int(os.getenv("DOC_COUNT", "1000"))
WARMUP = int(os.getenv("WARMUP", "50"))
WTIMEOUT_MS = int(os.getenv("WTIMEOUT_MS", "15000"))
DB_NAME = "write_concern_lab"


def percentile(sorted_vals, p):
    """Nearest-rank percentile on an already sorted list."""
    k = max(0, math.ceil(p / 100 * len(sorted_vals)) - 1)
    return sorted_vals[k]


def benchmark(client, label, w, j, n=DOC_COUNT, warmup=WARMUP):
    """Insert n docs one at a time with the given write concern; return stats dict."""
    wc = WriteConcern(w=w, j=j, wtimeout=WTIMEOUT_MS)
    db = client[DB_NAME]
    coll_name = "data_" + "".join(ch if ch.isalnum() else "_" for ch in label)

    # NOTE: write concern must be attached to the collection (with_options /
    # get_collection). insert_one() itself does not accept a write_concern kwarg.
    db.drop_collection(coll_name)
    db.create_collection(coll_name)
    col = db.get_collection(coll_name, write_concern=wc)

    for i in range(warmup):                       # warm-up: connections, caches
        col.insert_one({"warmup": True, "i": i})
    col.delete_many({"warmup": True})

    latencies = []
    t_start = time.perf_counter()
    for i in range(n):
        doc = {"seq": i, "label": label, "payload": "x" * 64}
        t0 = time.perf_counter()
        col.insert_one(doc)                       # raises if the write concern is not met
        latencies.append(time.perf_counter() - t0)
    total_s = time.perf_counter() - t_start

    stored = col.count_documents({})
    if stored != n:
        raise RuntimeError(f"{label}: expected {n} documents, found {stored}")

    ms = sorted(x * 1000 for x in latencies)
    return {
        "label": label,
        "w": w,
        "j": j,
        "docs": n,
        "total_s": total_s,
        "avg_ms": total_s / n * 1000,
        "p50_ms": statistics.median(ms),
        "p99_ms": percentile(ms, 99),
        "min_ms": ms[0],
        "max_ms": ms[-1],
        "ops_per_s": n / total_s,
    }


def main():
    banner("Lab 9.1: Write Concern Latency Benchmark")
    client = MongoClient(RS_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")

    members = replica_set_members(client)
    healthy = healthy_data_members(members)
    for m in members:
        print(f"  {m['name']:<14} {m['state']:<10} health={m['health']}")
    n_members = len(members)
    if len(healthy) != n_members or n_members < 3:
        raise SystemExit(
            "[FAIL] Need all 3 members healthy (w:all can only be met when every member is up).\n"
            "       Run:  lab setup   and wait until it prints 'ready'."
        )
    print(f"\n[OK] Connected. {n_members} data-bearing members -> w:all means w:{n_members}.")
    print(f"Inserting {DOC_COUNT:,} documents per configuration (+{WARMUP} warm-up)...\n")

    configs = []
    for wlabel, w in (("w:1", 1), ("w:majority", "majority"), (f"w:all (w:{n_members})", n_members)):
        for j in (False, True):
            configs.append((f"{wlabel}, j:{'true' if j else 'false'}", w, j))

    results = []
    for label, w, j in configs:
        print(f"  running {label:<24} ...", end=" ", flush=True)
        r = benchmark(client, label, w, j)
        results.append(r)
        print(f"done in {r['total_s']:.2f}s  (avg {r['avg_ms']:.2f} ms/write)")

    base = results[0]["avg_ms"]
    line = "=" * 98
    print("\n" + line)
    print(f"  {'Configuration':<24}{'Total (s)':>10}{'Avg (ms)':>10}{'P50 (ms)':>10}{'P99 (ms)':>10}{'ops/s':>10}{'vs w:1,j:false':>16}")
    print(line)
    for r in results:
        r["slowdown_vs_baseline"] = r["avg_ms"] / base
        print(f"  {r['label']:<24}{r['total_s']:>10.2f}{r['avg_ms']:>10.2f}{r['p50_ms']:>10.2f}"
              f"{r['p99_ms']:>10.2f}{r['ops_per_s']:>10.0f}{r['slowdown_vs_baseline']:>15.2f}x")
    print(line)

    print("\n  Activity - does journaling (j:true) add significant latency?")
    for i in range(0, len(results), 2):
        a, b = results[i], results[i + 1]
        pct = (b["avg_ms"] - a["avg_ms"]) / a["avg_ms"] * 100
        wl = a["label"].split(",")[0]
        print(f"    {wl:<16} j:false {a['avg_ms']:.2f} ms -> j:true {b['avg_ms']:.2f} ms  ({pct:+.0f}%)")

    path = save_json("lab_01_results.json", {
        "doc_count": DOC_COUNT, "members": n_members,
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results,
    })
    print(f"\n[OK] Results saved to {path}")
    client.close()
    banner("Lab 9.1 Complete")


if __name__ == "__main__":
    main()
