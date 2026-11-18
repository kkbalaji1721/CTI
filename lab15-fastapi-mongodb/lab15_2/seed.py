"""Step 1 - seed document-level isolation: ONE `tasks` collection, tenant_id on every document."""
import random
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING

from .common import TASKS_PER_TENANT, TENANTS, get_db


def seed(db=None, tenants=TENANTS, per_tenant=TASKS_PER_TENANT, seed_value=42) -> dict:
    db = db if db is not None else get_db()
    rng = random.Random(seed_value)  # deterministic -> same data every run

    # start clean: drop tasks and any tenant collections from a previous run
    db.drop_collection("tasks")
    for name in db.list_collection_names():
        if name.startswith("tasks_tenant_"):
            db.drop_collection(name)

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    docs = []
    for tid in tenants:
        for n in range(1, per_tenant + 1):
            docs.append(
                {
                    "tenant_id": tid,
                    "title": f"{tid} task {n}",
                    "status": rng.choice(["open", "in_progress", "done"]),
                    "priority": rng.choice(["low", "medium", "high"]),
                    "created_at": base + timedelta(minutes=rng.randint(0, 60 * 24 * 90)),
                }
            )
    db.tasks.insert_many(docs)
    db.tasks.create_index([("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="tenant_created_at")

    return {"tenants": len(tenants), "per_tenant": per_tenant, "total": db.tasks.count_documents({})}
