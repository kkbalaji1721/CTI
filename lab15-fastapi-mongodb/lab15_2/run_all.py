"""Run the whole Lab 15.2:  python -m lab15_2.run_all   (seed -> migrate -> validate -> benchmark)"""
import argparse
import json
import sys

from . import benchmark, migrate, seed
from .common import MIGRATION_DB, MONGO_URI, RESULTS_DIR, get_db


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lab 15.2 - tenant isolation migration")
    p.add_argument("--method", choices=["out", "insert_many"], default="out", help="migration method")
    p.add_argument("--repeats", type=int, default=50, help="timed runs per benchmark scenario")
    args = p.parse_args(argv)

    db = get_db()
    print(f"MongoDB: {MONGO_URI}   database: {MIGRATION_DB}")

    print("\n=== STEP 1: seed document-level isolation (5 tenants x 100 tasks) ===")
    s = seed.seed(db)
    print(f"seeded {s['total']} documents into 'tasks' ({s['tenants']} tenants x {s['per_tenant']})")

    print(f"\n=== STEP 2: migrate to collection-per-tenant (method: {args.method}) ===")
    summary = migrate.migrate(db, method=args.method)
    for tid, n in summary.items():
        print(f"  tasks -> tasks_tenant_{tid}: {n} documents")

    print("\n=== STEP 3: validate (counts, leakage, ids) ===")
    report = migrate.validate(db)
    migrate.print_validation(report)

    print("\n=== STEP 4: benchmark ===")
    bench = benchmark.run(db, repeats=args.repeats)
    jp, mp = benchmark.save(bench)
    for scenario, group in bench["results"].items():
        print(f"\n{scenario}")
        for name, r in group.items():
            print(f"  {name:<55} " + (f"mean {r['mean_ms']:>8} ms  median {r['median_ms']:>8} ms" if "mean_ms" in r
                                       else f"n/a ({r.get('error')})"))
        print(f"  -> {benchmark._winner(group)}")
    print(f"\nSaved: {jp}\n       {mp}")
    print("Recommendation: docs/RECOMMENDATION.md  (results dir: " + RESULTS_DIR + ")")

    with open(f"{RESULTS_DIR}/validation_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
