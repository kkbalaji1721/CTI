"""Shared helpers for Lab 15.2."""
import os

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
# separate database so the migration lab never touches the API's data
MIGRATION_DB = os.getenv("MIGRATION_DB", "tasktracker_migration")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")

TENANTS = ["acme", "globex", "initech", "umbrella", "hooli"]   # 5 tenants
TASKS_PER_TENANT = 100                                         # x 100 tasks = 500 documents


def target_name(tenant_id: str) -> str:
    """Collection name used by the collection-per-tenant strategy."""
    return f"tasks_tenant_{tenant_id}"


def get_db(client=None):
    client = client or MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client[MIGRATION_DB]
