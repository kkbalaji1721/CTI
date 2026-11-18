# Chapter 16 NoSQL Lab: MongoDB + Cassandra + Neo4j (Docker)

Contents: **Lab 16.1** (same dataset in 3 DBs), **Activity 16.1** (hybrid architecture), **Lab 16.2** (`FraudQueryService`,
connection pooling, circuit breaker, unit + integration tests, latency measurements).

## Run everything (one command)
```bash
docker compose up --build
```
First start takes 1-2 minutes (Cassandra boots slowly). The `lab` container waits for all databases, runs every task,
prints the results and saves them to `output/lab_output.txt` and `output/latency_report.md`.

Run again later without rebuilding: `docker compose run --rm lab`
Stop and clean up: `docker compose down -v`

## Project layout
| Path | Purpose |
|---|---|
| `lab16_1/mongodb.js`, `cassandra.cql`, `neo4j.cypher` | Schemas + queries as plain scripts |
| `lab16_1/run_lab16_1.py` | Loads data into all 3 DBs, runs the 3 queries in each, times them |
| `lab16_1/COMPARISON.md` | Syntax complexity / performance comparison |
| `lab16_1/activity_16_1_hybrid.py` | Hybrid architecture (Mongo ops, Cassandra audit, Neo4j prerequisites) |
| `lab16_2/fraud_service.py` | `FraudQueryService`, `CircuitBreaker`, connection pooling |
| `lab16_2/seed_data.py` | Fraud dataset loaded into all 3 DBs |
| `lab16_2/tests/test_unit.py` | Unit tests with `unittest.mock` |
| `lab16_2/tests/test_integration.py` | Full fraud-analysis workflow on real DBs |
| `lab16_2/benchmark.py` | Latency measurements -> `output/latency_report.md` |

## Publish to Docker Hub and submit
1. Create a free account at https://hub.docker.com (remember your username).
2. `docker login`
3. Build and push (replace `USER`):
   ```bash
   docker build -t USER/nosql-lab16:latest .
   docker push USER/nosql-lab16:latest
   ```
4. Edit `docker-compose.yml`: replace `YOUR_DOCKERHUB_USERNAME` with `USER`. Paste that compose file into the
   **Overview/description** of your Docker Hub repo (Repository -> Edit description), so the grader can run the full
   demo from your image: `docker compose up`.
5. Create the PDF: `pip install reportlab` then `python make_submission_pdf.py USER "Your Name"` -> `Lab16_Submission.pdf`
   (URL: `https://hub.docker.com/r/USER/nosql-lab16`). Make sure the repository is **public**.
6. Test as the grader would: on a clean folder with only the compose file, run `docker compose up`.

## Run unit tests only (no databases needed)
```bash
docker run --rm USER/nosql-lab16:latest python -m unittest lab16_2.tests.test_unit -v
```
