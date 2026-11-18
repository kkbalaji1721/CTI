"""MongoDB connection + index definitions."""
import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import OperationFailure

from . import config

log = logging.getLogger("tasktracker.db")
_db = None


def get_db():
    """Lazy singleton so importing the app never needs a live database."""
    global _db
    if _db is None:
        client = MongoClient(config.MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)
        _db = client[config.DB_NAME]
    return _db


def set_db(db) -> None:
    """Used by the tests to inject a mongomock database."""
    global _db
    _db = db


def init_indexes() -> None:
    db = get_db()

    # tenants: one document per tenant
    db.tenants.create_index([("tenant_id", ASCENDING)], unique=True, name="uniq_tenant")

    # users: username is unique *inside* a tenant (two tenants may both have "alice")
    db.users.create_index(
        [("tenant_id", ASCENDING), ("username", ASCENDING)], unique=True, name="uniq_tenant_username"
    )

    # tasks: the compound index from the lab solution (tenant_id, created_at)
    db.tasks.create_index(
        [("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="tenant_created_at"
    )
    # speeds up "my tasks" queries for regular users
    db.tasks.create_index(
        [("tenant_id", ASCENDING), ("owner_id", ASCENDING), ("created_at", DESCENDING)],
        name="tenant_owner_created_at",
    )

    # rate_limits: TTL index on the timestamp field - old counters delete themselves
    ttl = config.RATE_LIMIT_WINDOW * 2
    try:
        db.rate_limits.create_index([("timestamp", ASCENDING)], expireAfterSeconds=ttl, name="ttl_timestamp")
    except OperationFailure:
        # TTL value changed between runs -> drop and recreate
        db.rate_limits.drop_index("ttl_timestamp")
        db.rate_limits.create_index([("timestamp", ASCENDING)], expireAfterSeconds=ttl, name="ttl_timestamp")
    log.info("Indexes ready")
