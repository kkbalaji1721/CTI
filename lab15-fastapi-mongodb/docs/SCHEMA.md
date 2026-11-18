# Lab 15.1 - Task 1: Database schema (document-level tenant isolation)

All tenants share the same collections. Every tenant-owned document carries a `tenant_id`.

```
tenants                         users                               tasks                               rate_limits
-------                         -----                               -----                               -----------
_id                             _id                                 _id                                 _id  "<scope>:<bucket>"
tenant_id  (unique)  <------+   tenant_id  (FK -> tenants)          tenant_id  (FK -> tenants)          scope  "user:<tenant>:<uid>"
name                         +--username                            owner_id   (FK -> users._id)        count  (atomic $inc)
created_at                       password_hash (PBKDF2-SHA256)       title, description                  timestamp  (TTL field)
                                 role  "admin" | "user"              priority  low|medium|high
                                 created_at                          status    open|in_progress|done
                                                                     created_at, updated_at
```

## Indexes

| Collection | Index | Why |
|---|---|---|
| tenants | `{tenant_id: 1}` unique | one tenant per id |
| users | `{tenant_id: 1, username: 1}` unique | usernames unique *per tenant* |
| tasks | `{tenant_id: 1, created_at: -1}` | **compound index from the lab solution** - tenant filter + newest-first listing served by the index |
| tasks | `{tenant_id: 1, owner_id: 1, created_at: -1}` | "my tasks" for regular users (RBAC) |
| rate_limits | `{timestamp: 1}` TTL (`expireAfterSeconds = 2 x window`) | counters delete themselves |

## How isolation is enforced

1. `tenant_id` is read from the **verified JWT** (FastAPI dependency `get_current_user`), never from the request.
2. Every query is built by `scope_filter()` which always starts with `{"tenant_id": <from JWT>}`.
3. Another tenant's task id returns **404**, not 403, so ids cannot be probed.

## RBAC (Activity 15.1)

| Role | Tasks | Users |
|---|---|---|
| admin | all tasks in own tenant | create / list users in own tenant |
| user | only tasks where `owner_id == own id` | no access (403) |

## Rate limiting

Fixed-window counter. One atomic `find_one_and_update` (MongoDB `findAndModify`) with `$inc` + `upsert` per request on
document `_id = "<scope>:<window bucket>"`; if `count > limit` -> HTTP 429 with `Retry-After`. The TTL index on `timestamp` cleans old buckets.
Defaults: 60 req / 60 s per user, 30 login/signup attempts per window per IP (env: `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW_SECONDS`, `LOGIN_RATE_LIMIT_MAX`).
