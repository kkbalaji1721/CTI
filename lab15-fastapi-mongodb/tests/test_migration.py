import mongomock
import pytest

from lab15_2 import migrate, seed
from lab15_2.common import TENANTS, target_name


@pytest.fixture()
def db():
    return mongomock.MongoClient()["mig_test"]


@pytest.mark.parametrize("method", ["out", "insert_many"])
def test_seed_migrate_validate(db, method):
    s = seed.seed(db)
    assert s["total"] == 500
    summary = migrate.migrate(db, method=method)
    assert summary == {t: 100 for t in sorted(TENANTS)}
    report = migrate.validate(db)
    assert report["ok"], report
    assert report["total_target"] == 500


def test_validation_detects_leakage(db):
    seed.seed(db)
    migrate.migrate(db)
    # plant a foreign document in acme's collection -> validation MUST fail
    db[target_name("acme")].insert_one({"tenant_id": "globex", "title": "leak", "created_at": None})
    assert migrate.validate(db)["ok"] is False


def test_validation_detects_missing_docs(db):
    seed.seed(db)
    migrate.migrate(db)
    db[target_name("hooli")].delete_one({})
    assert migrate.validate(db)["ok"] is False


def test_migration_is_rerunnable(db):
    seed.seed(db)
    migrate.migrate(db)
    migrate.migrate(db)  # twice -> no duplicates
    assert migrate.validate(db)["ok"]
