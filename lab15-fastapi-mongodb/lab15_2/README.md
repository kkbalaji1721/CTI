# Lab 15.2 – Multi-tenant Migration

Seeds 5 tenants × 100 tasks, migrates to collection-per-tenant (`$out` and `insert_many`), validates counts / no cross-tenant leakage, and benchmarks both designs.

`seed.py` · `migrate.py` · `benchmark.py` · `run_all.py` · `common.py`

**Run (inside the Docker setup of Lab 15):** `docker exec lab15 python -m lab15_2.run_all`
