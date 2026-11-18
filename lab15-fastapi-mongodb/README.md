# Lab 15 - Multi-Tenant Task API (FastAPI + MongoDB)

Everything for **Lab 15.1** (multi-tenant API, JWT, RBAC, rate limiting) and **Lab 15.2** (isolation-strategy migration)
packed in **one Docker image** (embedded MongoDB + app + scripts). Nothing else needs to be installed to demo it.

| Lab requirement | Where it is |
|---|---|
| 15.1-1 Schema with tenant isolation | `docs/SCHEMA.md`, indexes in `app/db.py` |
| 15.1-2 CRUD with `tenant_id` filter on every query | `app/routes_tasks.py` (`scope_filter`) |
| 15.1 tenant_id from JWT in a FastAPI dependency | `app/deps.py` (`get_current_user`) |
| 15.1-3 Rate limiting, MongoDB counter + TTL index + findAndModify | `app/rate_limit.py` |
| 15.1 Activity: RBAC (admin = all tasks, user = own tasks) | `scope_filter` + `require_admin` |
| 15.2 Seed 5 tenants x 100 tasks | `lab15_2/seed.py` |
| 15.2 Migrate to collection-per-tenant (`$out` and `insert_many`) | `lab15_2/migrate.py` |
| 15.2 Validate counts / no cross-tenant leakage | `lab15_2/migrate.py::validate` |
| 15.2 Performance comparison | `lab15_2/benchmark.py` -> `results/` |
| 15.2 Written recommendation | `docs/RECOMMENDATION.md` |

---

## A. Run it locally first (check everything works)

Install **Docker Desktop** and make sure it is running, then in this folder:

```bash
docker build -t lab15-multitenant .
docker run --rm lab15-multitenant all
```

`all` runs, in order: unit tests -> live Lab 15.1 demo (all checks print PASS/FAIL) -> full Lab 15.2 (seed, migrate,
validate, benchmark). You should see `SUMMARY: 23/23 checks passed` and `VALIDATION: PASSED - no cross-tenant leakage`.

Start the API for a manual / Swagger demo:

```bash
docker run --rm -p 8000:8000 --name lab15 lab15-multitenant
# open http://localhost:8000/docs
```

In a second terminal, while it is running:

```bash
docker exec lab15 python scripts/demo_15_1.py      # Lab 15.1 live demo (23 checks)
docker exec lab15 python -m lab15_2.run_all        # Lab 15.2 end to end
docker exec lab15 cat results/benchmark_results.md # the benchmark table
```

Other commands: `docker run --rm lab15-multitenant test` (unit tests only), `... demo-15-1`, `... lab15-2`, `... bash`.

Alternative with a separate Mongo container: `docker compose up --build`.

## B. Upload to Docker Hub

1. Create a free account at https://hub.docker.com (your username is e.g. `jdoe`).
2. `docker login`
3. Build with your username in the tag and push:
   ```bash
   docker build -t jdoe/lab15-multitenant:latest .
   docker push jdoe/lab15-multitenant:latest
   ```
   *(If your laptop is an Apple-silicon Mac and the grader may use Intel/AMD, push both architectures instead:)*
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64 -t jdoe/lab15-multitenant:latest --push .
   ```
4. Make sure the repository is **Public** (Docker Hub -> your repo -> Settings -> Visibility).
5. **Test the pushed image exactly as the grader will**:
   ```bash
   docker rmi jdoe/lab15-multitenant:latest
   docker run --rm jdoe/lab15-multitenant:latest all
   ```

## C. Make the PDF to submit

```bash
pip install reportlab
python make_submission_pdf.py --dockerhub-user jdoe --name "Your Name" --student-id "Your ID"
```
This creates `Lab15_Submission.pdf` containing the Docker Hub URL (`https://hub.docker.com/r/jdoe/lab15-multitenant`)
and the run commands. Any PDF that contains the Docker URL is fine if you prefer to write your own.

## D. Demo script for the grader (about 3 minutes)

1. `docker run --rm -p 8000:8000 --name lab15 jdoe/lab15-multitenant` -> open `/docs`.
2. `docker exec lab15 python scripts/demo_15_1.py` -> show isolation / RBAC / 429 rate limit all PASS.
3. `docker exec lab15 python -m lab15_2.run_all` -> show 5x100 seed, migration table, validation PASSED, benchmark.
4. Show `docs/SCHEMA.md` and `docs/RECOMMENDATION.md` (`docker exec lab15 cat docs/RECOMMENDATION.md`).

### Manual Swagger walk-through (`/docs`)
`POST /tenants` (create tenant + admin) -> `POST /auth/login` -> copy `access_token` -> **Authorize** -> `POST /users`
(add a normal user) -> log in as that user -> `POST /tasks/`, `GET /tasks/`. Log in as admin to see all tasks.

## E. Questions you may be asked

- **Why is `tenant_id` taken from the JWT and not from a query parameter?** A client-supplied `tenant_id` lets anyone read
  another tenant's data by changing the URL. The JWT is signed, so it cannot be forged.
- **Why 404 instead of 403 for another tenant's task?** So attackers cannot learn which task ids exist.
- **Why a compound index `(tenant_id, created_at)`?** Every query filters on `tenant_id` and lists newest-first, so one index serves both.
- **How does the rate limiter stay correct under concurrency?** One atomic `findAndModify` (`$inc` + upsert) per request - no read-modify-write race. The TTL index deletes old counters.
- **When use collection-per-tenant?** Independent backup/restore, strict regulatory separation, per-tenant tuning, few tenants. See `docs/RECOMMENDATION.md`.

## Notes / limitations
- `POST /tenants` is open self-signup (needed for the demo); in production protect it.
- Set `JWT_SECRET` to a long random value in real deployments (`-e JWT_SECRET=...`).
- Rate limiting is a fixed-window counter (simple; allows a burst at a window boundary).
- Unit tests use an in-memory MongoDB emulator (`mongomock`); the demo/benchmark scripts use the real MongoDB in the image.
