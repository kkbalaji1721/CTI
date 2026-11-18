from app import config

from .conftest import add_user, login, make_tenant


def setup_two_tenants(client):
    make_tenant(client, "acme")
    make_tenant(client, "globex")
    acme_admin = login(client, "acme", "admin")
    globex_admin = login(client, "globex", "admin")
    add_user(client, acme_admin, "alice")
    add_user(client, acme_admin, "bob")
    return acme_admin, globex_admin, login(client, "acme", "alice"), login(client, "acme", "bob")


def test_requires_auth(client):
    assert client.get("/tasks/").status_code == 401
    assert client.get("/tasks/", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_bad_login(client):
    make_tenant(client, "acme")
    r = client.post("/auth/login", json={"tenant_id": "acme", "username": "admin", "password": "wrong-pass"})
    assert r.status_code == 401
    r = client.post("/auth/login", json={"tenant_id": "other", "username": "admin", "password": "password123"})
    assert r.status_code == 401


def test_duplicate_tenant(client):
    make_tenant(client, "acme")
    r = client.post("/tenants", json={"tenant_id": "acme", "name": "x", "admin_username": "admin",
                                      "admin_password": "password123"})
    assert r.status_code == 409


def test_crud_roundtrip(client):
    make_tenant(client, "acme")
    h = login(client, "acme", "admin")
    r = client.post("/tasks/", json={"title": "Write report", "priority": "high"}, headers=h)
    assert r.status_code == 201
    tid = r.json()["id"]
    assert r.json()["status"] == "open" and r.json()["tenant_id"] == "acme"
    assert client.get(f"/tasks/{tid}", headers=h).json()["title"] == "Write report"
    r = client.patch(f"/tasks/{tid}", json={"status": "done"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "done"
    assert client.put(f"/tasks/{tid}", json={"title": "New title"}, headers=h).json()["title"] == "New title"
    assert client.delete(f"/tasks/{tid}", headers=h).status_code == 204
    assert client.get(f"/tasks/{tid}", headers=h).status_code == 404


def test_tenant_isolation(client):
    acme_admin, globex_admin, alice, _ = setup_two_tenants(client)
    tid = client.post("/tasks/", json={"title": "acme secret"}, headers=alice).json()["id"]
    client.post("/tasks/", json={"title": "globex task"}, headers=globex_admin)

    # globex admin (even an ADMIN) can't see/modify/delete acme's task
    assert [t["title"] for t in client.get("/tasks/", headers=globex_admin).json()["items"]] == ["globex task"]
    assert client.get(f"/tasks/{tid}", headers=globex_admin).status_code == 404
    assert client.patch(f"/tasks/{tid}", json={"title": "hacked"}, headers=globex_admin).status_code == 404
    assert client.delete(f"/tasks/{tid}", headers=globex_admin).status_code == 404
    # still intact for acme
    assert client.get(f"/tasks/{tid}", headers=acme_admin).json()["title"] == "acme secret"


def test_tenant_id_query_param_is_ignored(client):
    """The insecure pattern from the sample code (?tenant_id=...) must not work."""
    acme_admin, globex_admin, alice, _ = setup_two_tenants(client)
    client.post("/tasks/", json={"title": "acme secret"}, headers=alice)
    r = client.get("/tasks/?tenant_id=acme", headers=globex_admin)
    assert r.json()["total"] == 0


def test_rbac_user_sees_only_own(client):
    acme_admin, _, alice, bob = setup_two_tenants(client)
    a = client.post("/tasks/", json={"title": "alice task"}, headers=alice).json()["id"]
    b = client.post("/tasks/", json={"title": "bob task"}, headers=bob).json()["id"]

    assert [t["title"] for t in client.get("/tasks/", headers=alice).json()["items"]] == ["alice task"]
    assert [t["title"] for t in client.get("/tasks/", headers=bob).json()["items"]] == ["bob task"]
    assert client.get(f"/tasks/{b}", headers=alice).status_code == 404
    assert client.patch(f"/tasks/{b}", json={"status": "done"}, headers=alice).status_code == 404
    assert client.delete(f"/tasks/{b}", headers=alice).status_code == 404

    # admin manages everything in the tenant
    assert client.get("/tasks/", headers=acme_admin).json()["total"] == 2
    assert client.patch(f"/tasks/{a}", json={"status": "done"}, headers=acme_admin).status_code == 200
    assert client.delete(f"/tasks/{b}", headers=acme_admin).status_code == 204


def test_only_admin_manages_users(client):
    acme_admin, _, alice, _ = setup_two_tenants(client)
    r = client.post("/users", json={"username": "mallory", "password": "password123", "role": "admin"}, headers=alice)
    assert r.status_code == 403
    assert client.get("/users", headers=alice).status_code == 403
    assert len(client.get("/users", headers=acme_admin).json()) == 3


def test_same_username_in_two_tenants(client):
    make_tenant(client, "acme")
    make_tenant(client, "globex")
    add_user(client, login(client, "acme", "admin"), "sam")
    add_user(client, login(client, "globex", "admin"), "sam")  # allowed: unique per tenant
    r = client.post("/users", json={"username": "sam", "password": "password123"}, headers=login(client, "acme", "admin"))
    assert r.status_code == 409


def test_rate_limit(client, monkeypatch):
    make_tenant(client, "acme")
    h = login(client, "acme", "admin")
    monkeypatch.setattr(config, "RATE_LIMIT_MAX", 5)
    codes = [client.get("/tasks/", headers=h).status_code for _ in range(8)]
    # the window could roll over mid-test; at least one 429 must still appear unless that happens
    assert codes[:3] == [200, 200, 200]
    assert 429 in codes
    r = client.get("/tasks/", headers=h)
    if r.status_code == 429:
        assert "retry-after" in r.headers


def test_rate_limit_is_per_user(client, monkeypatch):
    acme_admin, _, alice, bob = setup_two_tenants(client)
    monkeypatch.setattr(config, "RATE_LIMIT_MAX", 3)
    for _ in range(6):
        client.get("/tasks/", headers=alice)
    assert client.get("/tasks/", headers=bob).status_code == 200  # bob unaffected by alice's burst


def test_rate_limit_counter_collection_and_ttl_index(client):
    make_tenant(client, "acme")
    h = login(client, "acme", "admin")
    client.get("/tasks/", headers=h)
    from app.db import get_db
    db = get_db()
    assert db.rate_limits.count_documents({}) >= 1
    assert "ttl_timestamp" in db.rate_limits.index_information()


def test_validation(client):
    make_tenant(client, "acme")
    h = login(client, "acme", "admin")
    assert client.post("/tasks/", json={"title": ""}, headers=h).status_code == 422
    assert client.post("/tasks/", json={"title": "x", "priority": "urgent"}, headers=h).status_code == 422
    assert client.get("/tasks/not-an-objectid", headers=h).status_code == 404
