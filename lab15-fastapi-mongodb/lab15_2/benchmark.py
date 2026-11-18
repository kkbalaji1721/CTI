"""
Step 4 - compare query performance of the two isolation strategies.

A  = document-level   : one `tasks` collection, compound index (tenant_id, created_at)
B  = collection-per-tenant : tasks_tenant_<id>, index (created_at)

Scenarios: list a tenant's tasks | create a task | cross-tenant analytics.
Numbers are measured on YOUR machine at YOUR data size - the report states what was measured.
"""
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone

from .common import RESULTS_DIR, TENANTS, get_db, target_name


def _time_ms(fn, repeats: int, warmup: int = 3):
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    return {
        "mean_ms": round(statistics.mean(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(samples[max(0, int(len(samples) * 0.95) - 1)], 3),
        "runs": repeats,
    }


def run(db=None, repeats: int = 50, use_union_with: bool = True) -> dict:
    db = db if db is not None else get_db()
    tenants = sorted(db.tasks.distinct("tenant_id")) or TENANTS
    colls = [target_name(t) for t in tenants]
    for c in colls:
        if db[c].count_documents({}) == 0:
            raise RuntimeError(f"{c} is empty - run the migration first")
    results = {}

    # 1) list a tenant's tasks (newest 50) ------------------------------------------------
    def list_doc():
        for t in tenants:
            list(db.tasks.find({"tenant_id": t}).sort("created_at", -1).limit(50))

    def list_coll():
        for c in colls:
            list(db[c].find().sort("created_at", -1).limit(50))

    results["list_tasks_per_tenant (all 5 tenants per run)"] = {
        "document_level": _time_ms(list_doc, repeats),
        "collection_per_tenant": _time_ms(list_coll, repeats),
    }

    # 2) create a task -----------------------------------------------------------------------
    def make_creator(use_collections: bool):
        inserted = []

        def create():
            for t in tenants:
                doc = {"tenant_id": t, "title": "bench", "status": "open", "priority": "low",
                       "created_at": datetime.now(timezone.utc)}
                coll = db[target_name(t)] if use_collections else db.tasks
                inserted.append((coll.name, coll.insert_one(doc).inserted_id))
        return create, inserted

    create_a, ins_a = make_creator(False)
    create_b, ins_b = make_creator(True)
    res_a = _time_ms(create_a, repeats)
    res_b = _time_ms(create_b, repeats)
    for name, _id in ins_a + ins_b:       # clean up so data stays at 500 docs
        db[name].delete_one({"_id": _id})
    results["create_task (insert 1 per tenant per run)"] = {"document_level": res_a, "collection_per_tenant": res_b}

    # 3) cross-tenant analytics: task count per tenant -------------------------------------------
    def analytics_doc():
        list(db.tasks.aggregate([{"$group": {"_id": "$tenant_id", "count": {"$sum": 1}}}]))

    def analytics_app_side():
        {t: db[c].count_documents({}) for t, c in zip(tenants, colls)}

    analytics = {
        "document_level ($group, 1 pipeline)": _time_ms(analytics_doc, repeats),
        "collection_per_tenant (app-side merge, N queries)": _time_ms(analytics_app_side, repeats),
    }
    if use_union_with:
        def analytics_union():
            pipeline = [{"$unionWith": {"coll": c}} for c in colls[1:]]
            pipeline.append({"$group": {"_id": "$tenant_id", "count": {"$sum": 1}}})
            list(db[colls[0]].aggregate(pipeline))
        try:
            analytics["collection_per_tenant ($unionWith, 1 pipeline)"] = _time_ms(analytics_union, repeats)
        except Exception as exc:  # e.g. MongoDB < 4.4
            analytics["collection_per_tenant ($unionWith, 1 pipeline)"] = {"error": str(exc)[:120]}
    results["cross_tenant_analytics (count per tenant)"] = analytics

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "documents": db.tasks.count_documents({}),
        "tenants": len(tenants),
        "repeats": repeats,
        "results": results,
    }


def _winner(group: dict):
    ok = {k: v["mean_ms"] for k, v in group.items() if "mean_ms" in v}
    if len(ok) < 2:
        return "n/a"
    best = min(ok, key=ok.get)
    worst = max(ok.values())
    gap = (worst - ok[best]) / worst * 100 if worst else 0
    if gap < 10:
        return f"no meaningful difference (<10% gap) at this data size; fastest mean: {best}"
    return f"{best} is faster by {gap:.0f}% (mean)"


def to_markdown(report: dict) -> str:
    lines = [
        "# Lab 15.2 - Query performance comparison",
        "",
        f"Generated: {report['generated_at']}  |  Platform: {report['platform']}",
        f"Data: {report['documents']} documents, {report['tenants']} tenants, {report['repeats']} timed runs per scenario.",
        "",
    ]
    for scenario, group in report["results"].items():
        lines += [f"## {scenario}", "", "| Strategy | mean (ms) | median (ms) | p95 (ms) |", "|---|---:|---:|---:|"]
        for name, r in group.items():
            if "mean_ms" in r:
                lines.append(f"| {name} | {r['mean_ms']} | {r['median_ms']} | {r['p95_ms']} |")
            else:
                lines.append(f"| {name} | n/a ({r.get('error')}) | | |")
        lines += ["", f"**Result:** {_winner(group)}", ""]
    lines += [
        "> Note: with only 500 documents everything fits in memory and in cache, so differences are small and "
        "can vary run to run. The architectural trade-offs (see docs/RECOMMENDATION.md) matter more than these timings.",
    ]
    return "\n".join(lines)


def save(report: dict, directory: str = None) -> tuple:
    directory = directory or RESULTS_DIR
    os.makedirs(directory, exist_ok=True)
    jp, mp = os.path.join(directory, "benchmark_results.json"), os.path.join(directory, "benchmark_results.md")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2)
    with open(mp, "w") as f:
        f.write(to_markdown(report))
    return jp, mp
