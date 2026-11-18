"""
Live demo for Lab 15.1 - talks to the RUNNING API over HTTP and prints PASS/FAIL for every requirement.
Usage:  python scripts/demo_15_1.py [base_url]        (default http://localhost:8000)
"""
import random
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PW = "Passw0rd!123"
results = []


def check(name: str, cond: bool, detail: str = ""):
    results.append(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def login(c, tenant, user):
    r = c.post("/auth/login", json={"tenant_id": tenant, "username": user, "password": PW})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main():
    sfx = random.randint(1000, 9999)
    t1, t2 = f"acme_{sfx}", f"globex_{sfx}"
    with httpx.Client(base_url=BASE, timeout=15) as c:
        print(f"API: {BASE}  health: {c.get('/health').json()}\n")

        print("1. Create two tenants (each gets an admin)")
        for t in (t1, t2):
            r = c.post("/tenants", json={"tenant_id": t, "name": t, "admin_username": "admin", "admin_password": PW})
            check(f"tenant {t} created", r.status_code == 201, str(r.status_code))
        a1, a2 = login(c, t1, "admin"), login(c, t2, "admin")

        print("\n2. Admin creates regular users in tenant 1")
        for u in ("alice", "bob"):
            r = c.post("/users", json={"username": u, "password": PW, "role": "user"}, headers=a1)
            check(f"user {u} created in {t1}", r.status_code == 201)
        alice, bob = login(c, t1, "alice"), login(c, t1, "bob")

        print("\n3. CRUD")
        r = c.post("/tasks/", json={"title": "Alice's task", "priority": "high"}, headers=alice)
        check("create task", r.status_code == 201)
        alice_task = r.json()["id"]
        r = c.post("/tasks/", json={"title": "Bob's task"}, headers=bob)
        bob_task = r.json()["id"]
        check("read task", c.get(f"/tasks/{alice_task}", headers=alice).json()["title"] == "Alice's task")
        check("update task", c.patch(f"/tasks/{alice_task}", json={"status": "in_progress"}, headers=alice).json()["status"] == "in_progress")
        r = c.post("/tasks/", json={"title": "to delete"}, headers=alice)
        check("delete task", c.delete(f"/tasks/{r.json()['id']}", headers=alice).status_code == 204)

        print("\n4. Tenant isolation (tenant_id comes from the JWT, filtered on every query)")
        c.post("/tasks/", json={"title": "Globex task"}, headers=a2)
        check("globex admin sees only globex tasks", [t["title"] for t in c.get("/tasks/", headers=a2).json()["items"]] == ["Globex task"])
        check("globex ADMIN cannot read acme task by id", c.get(f"/tasks/{alice_task}", headers=a2).status_code == 404)
        check("globex ADMIN cannot delete acme task", c.delete(f"/tasks/{alice_task}", headers=a2).status_code == 404)
        check("?tenant_id=<other> query param is ignored", c.get(f"/tasks/?tenant_id={t1}", headers=a2).json()["total"] == 1)

        print("\n5. RBAC (Activity 15.1): admin manages all, users only their own")
        check("alice sees only her own task", [t["title"] for t in c.get("/tasks/", headers=alice).json()["items"]] == ["Alice's task"])
        check("alice cannot read bob's task", c.get(f"/tasks/{bob_task}", headers=alice).status_code == 404)
        check("alice cannot update bob's task", c.patch(f"/tasks/{bob_task}", json={"status": "done"}, headers=alice).status_code == 404)
        check("alice cannot create users (403)", c.post("/users", json={"username": "eve", "password": PW}, headers=alice).status_code == 403)
        check("admin sees all tenant tasks", c.get("/tasks/", headers=a1).json()["total"] == 2)
        check("admin can update bob's task", c.patch(f"/tasks/{bob_task}", json={"status": "done"}, headers=a1).status_code == 200)
        check("admin can delete bob's task", c.delete(f"/tasks/{bob_task}", headers=a1).status_code == 204)
        check("no token -> 401", c.get("/tasks/").status_code == 401)

        print("\n6. Rate limiting (MongoDB counter + TTL index)")
        c.post("/users", json={"username": "ratetest", "password": PW}, headers=a1)
        rt = login(c, t1, "ratetest")
        first = c.get("/tasks/", headers=rt)
        limit = int(first.headers["X-RateLimit-Limit"])
        print(f"  limit = {limit} requests / window; sending {limit + 5} more requests ...")
        codes = [c.get("/tasks/", headers=rt) for _ in range(limit + 5)]
        n429 = sum(1 for r in codes if r.status_code == 429)
        check("requests over the limit get 429", n429 >= 1, f"{n429} x 429")
        if n429:
            r429 = next(r for r in codes if r.status_code == 429)
            check("429 carries Retry-After header", "retry-after" in r429.headers, f"Retry-After={r429.headers.get('retry-after')}s")
        check("other users are unaffected by the burst", c.get("/tasks/", headers=bob).status_code == 200)

    print(f"\nSUMMARY: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
