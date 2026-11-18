# Lab 09 - Write Concern Latency & Network Partition (MongoDB + Docker)

Everything runs inside Docker. You only need **Docker Desktop** and a free **Docker Hub** account.

## Contents
| File | Purpose |
|---|---|
| `Dockerfile` | Builds the lab image you publish to Docker Hub |
| `docker-compose.yml` | 3-node MongoDB replica set (mongo1/2/3, all data-bearing) + the `lab` runner |
| `src/lab_01_write_concern_latency.py` | **Lab 9.1** + the j:true / j:false activity |
| `src/lab_02_simulate_partition.py` | **Lab 9.2** |
| `src/setup_replicaset.py` | Initiates replica set `rs0` |
| `src/make_report.py` | Builds the submission PDF from the *real* results |

---
## Part A - Build and publish the image (once)

Replace `YOURUSER` with your Docker Hub username everywhere.

```bash
cd lab09
docker login
docker build --build-arg IMAGE_NAME=YOURUSER/nosql-lab09:latest -t YOURUSER/nosql-lab09:latest .
```

## Part B - Test it exactly the way the grader will
```bash
mkdir demo && cd demo
docker run --rm YOURUSER/nosql-lab09:latest print-compose > docker-compose.yml
docker compose up -d mongo1 mongo2 mongo3
docker compose run --rm lab setup       # wait for: Replica set rs0 is ready
docker compose run --rm lab lab01       # ~1-3 minutes
docker compose run --rm lab lab02       # ~2-4 minutes, do not interrupt
```
Results appear in `demo/results/` (`lab_01_results.json`, `lab_02_results.json`, `lab_02_timeline.txt`).
*(Optional: put your `Write-Concern-TradeOffs.jpg` in `demo/results/` before the report step and it is added to the PDF.)*

## Part C - Make the PDF (contains your Docker URL)
```bash
docker compose run --rm lab report --docker-url https://hub.docker.com/r/YOURUSER/nosql-lab09 --name "Your Name" --student-id "Your ID"
```
Your PDF is `demo/results/Lab09_Report.pdf`. Open it and check it.

## Part D - Publish and verify
```bash
docker push YOURUSER/nosql-lab09:latest
```
Make sure the repository is **Public** on hub.docker.com (Repository -> Settings). Then verify from a clean state:
```bash
docker rmi YOURUSER/nosql-lab09:latest
docker compose down -v
docker pull YOURUSER/nosql-lab09:latest
```
Submit the PDF.

## Clean up
`docker compose down -v`

---
## Troubleshooting
* **Lab 9.2 says container not found** - run `docker compose up -d mongo1 mongo2 mongo3` then `lab setup` first.
* **Lab 9.2 stopped halfway** - the script re-connects the containers itself; if in doubt run `docker network connect --alias mongo2 lab09_net mongo2` (same for mongo3), or simply `docker compose down -v` and start again.
* **Numbers look odd** - close heavy apps and re-run `lab01`; single runs are noisy.
* **Port/name already in use** - `docker compose down -v` and retry.
* Windows: use PowerShell or WSL; the commands are identical. Docker Desktop must be in "Linux containers" mode.

## Corrections vs. the reference repo / lab text (worth knowing for viva)
1. `insert_one(doc, write_concern=...)` (used in the reference script) is not valid PyMongo; the write concern is set on the collection (`get_collection(name, write_concern=WriteConcern(...))`).
2. MongoDB has no `w:"all"`; "all members" = `w:<member count>` (here `w:3`).
3. The lab text assumes 3 data-bearing members; the Chapter 8 compose uses an arbiter, which cannot acknowledge writes and would make `w:3` impossible. This package uses 3 data-bearing members.
4. A partitioned secondary does not "disappear" from `rs.status()`; it is listed as not reachable/healthy (health 0).
5. A `w:majority` write that times out is *still applied on the primary*; it is just not majority-safe and can be rolled back after failover.
