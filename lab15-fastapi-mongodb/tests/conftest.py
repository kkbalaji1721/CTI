import mongomock
import pytest
from fastapi.testclient import TestClient

from app import config, db as dbmod
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    dbmod.set_db(mongomock.MongoClient(tz_aware=True)["test_tasktracker"])
    dbmod.init_indexes()
    monkeypatch.setattr(config, "RATE_LIMIT_MAX", 1000)  # tests that need a low limit override this
    yield TestClient(app)
    dbmod.set_db(None)


def make_tenant(client, tenant_id, admin="admin", pw="password123"):
    r = client.post("/tenants", json={"tenant_id": tenant_id, "name": tenant_id.title(),
                                      "admin_username": admin, "admin_password": pw})
    assert r.status_code == 201, r.text


def login(client, tenant_id, username, pw="password123"):
    r = client.post("/auth/login", json={"tenant_id": tenant_id, "username": username, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def add_user(client, admin_headers, username, role="user", pw="password123"):
    r = client.post("/users", json={"username": username, "password": pw, "role": role}, headers=admin_headers)
    assert r.status_code == 201, r.text
