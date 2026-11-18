"""
Step 2 + 3 - migrate to collection-per-tenant, then VALIDATE.

Two migration methods (both from the lab solution):
  out          -> db.tasks.aggregate([{$match: {tenant_id: tid}}, {$out: 'tasks_tenant_<tid>'}])
  insert_many  -> Python loop: find + insert_many in batches
"""
from pymongo import DESCENDING

from .common import get_db, target_name


def migrate(db=None, method: str = "out", batch_size: int = 500) -> dict:
    if method not in ("out", "insert_many"):
        raise ValueError("method must be 'out' or 'insert_many'")
    db = db if db is not None else get_db()
    summary = {}
    for tid in sorted(db.tasks.distinct("tenant_id")):
        target = target_name(tid)
        db.drop_collection(target)  # makes the migration re-runnable
        if method == "out":
            db.tasks.aggregate([{"$match": {"tenant_id": tid}}, {"$out": target}])
        else:
            batch = []
            for doc in db.tasks.find({"tenant_id": tid}):
                batch.append(doc)
                if len(batch) >= batch_size:
                    db[target].insert_many(batch)
                    batch = []
            if batch:
                db[target].insert_many(batch)
        # $out / insert_many do not copy indexes -> add the per-tenant index (created_at only!)
        db[target].create_index([("created_at", DESCENDING)], name="created_at")
        summary[tid] = db[target].count_documents({})
    return summary


def validate(db=None) -> dict:
    """Checks counts, tenant purity (no cross-tenant leakage) and exact id equality."""
    db = db if db is not None else get_db()
    checks, all_ok = [], True
    tenants = sorted(db.tasks.distinct("tenant_id"))
    seen_ids, total_target = set(), 0

    for tid in tenants:
        coll = db[target_name(tid)]
        src_count = db.tasks.count_documents({"tenant_id": tid})
        dst_count = coll.count_documents({})
        foreign = coll.count_documents({"tenant_id": {"$ne": tid}})          # leakage in
        src_ids = {d["_id"] for d in db.tasks.find({"tenant_id": tid}, {"_id": 1})}
        dst_ids = {d["_id"] for d in coll.find({}, {"_id": 1})}
        overlap = len(seen_ids & dst_ids)                                    # same doc in 2 collections
        seen_ids |= dst_ids
        total_target += dst_count

        ok = src_count == dst_count and foreign == 0 and src_ids == dst_ids and overlap == 0
        all_ok &= ok
        checks.append({"tenant": tid, "source_count": src_count, "target_count": dst_count,
                       "foreign_docs": foreign, "ids_match": src_ids == dst_ids, "overlap": overlap, "ok": ok})

    total_ok = total_target == db.tasks.count_documents({})
    all_ok &= total_ok
    return {"ok": all_ok, "total_source": db.tasks.count_documents({}), "total_target": total_target,
            "total_matches": total_ok, "tenants": checks}


def print_validation(report: dict) -> None:
    print(f"\n{'tenant':<10} {'source':>7} {'target':>7} {'foreign':>8} {'ids match':>10} {'overlap':>8}  result")
    print("-" * 64)
    for c in report["tenants"]:
        print(f"{c['tenant']:<10} {c['source_count']:>7} {c['target_count']:>7} {c['foreign_docs']:>8} "
              f"{str(c['ids_match']):>10} {c['overlap']:>8}  {'PASS' if c['ok'] else 'FAIL'}")
    print("-" * 64)
    print(f"TOTAL source={report['total_source']} target={report['total_target']}  ->  "
          f"{'PASS' if report['total_matches'] else 'FAIL'}")
    print(f"\nVALIDATION: {'PASSED - no cross-tenant leakage' if report['ok'] else 'FAILED'}")
