# MongoDB Labs 11 and 12 — Student Project

This project contains practical starter implementations for Labs 11.1, 11.2, 12.1 and 12.2.

## Before starting
- Windows 10/11 with Docker Desktop and Docker Compose v2.
- Python 3.10+ (for the data loader and TLS test).
- Internet access for the first Docker image download.
- At least 6 GB of free RAM is recommended for the sharding lab. Close other heavy apps.
- These compose files are **local teaching/demo environments**, not production deployments.

## Important
1. Start with Lab 11. Do not start every service at once.
2. Save screenshots of your own terminal outputs. Do not submit the illustrative values in the report as if they were measured.
3. Change the example passwords before using the environment. Do not publish real credentials or private keys to Docker Hub.
4. A single-member replica set per shard and a single-member config-server replica set are for a classroom demonstration only.

## Folder guide
- `Lab-11-Sharding`: two-shard cluster and shard-key experiments.
- `Lab-12-Security`: independent authentication/RBAC and TLS exercises.
- `submission/`: final report template.

## Build the custom Docker Hub image first
From the project root folder, replace `YOUR_DOCKERHUB_USERNAME` with your Docker Hub username in all three compose files, then run:

```powershell
docker build -f Dockerfile.mongo -t YOUR_DOCKERHUB_USERNAME/mongodb-lab11-12:1.0 .
docker login
docker push YOUR_DOCKERHUB_USERNAME/mongodb-lab11-12:1.0
```

The compose files use this published custom MongoDB image for the config server, both shards, mongos, the RBAC server and the TLS server. The image is based on the official MongoDB 8.0 image and includes the lab scripts. Do not include generated private certificates or passwords in the image.

## Lab 11 start (PowerShell)
Open PowerShell in `Lab-11-Sharding`:

```powershell
docker compose up -d cfg shard1 shard2
docker compose exec cfg mongosh --port 27019 --eval "rs.initiate({_id:'cfgRS',configsvr:true,members:[{_id:0,host:'cfg:27019'}]})"
docker compose exec shard1 mongosh --port 27018 --eval "rs.initiate({_id:'shard1RS',members:[{_id:0,host:'shard1:27018'}]})"
docker compose exec shard2 mongosh --port 27018 --eval "rs.initiate({_id:'shard2RS',members:[{_id:0,host:'shard2:27018'}]})"
```

Wait about 20–40 seconds for the replica sets to elect their single-member primaries, then start the router:

```powershell
docker compose up -d mongos
docker compose ps
docker compose exec mongos mongosh --port 27017
```

At the mongosh prompt, run:

```javascript
sh.addShard("shard1RS/shard1:27018")
sh.addShard("shard2RS/shard2:27018")
sh.status()
```

If `sh.addShard` reports that a shard is already registered, use `sh.status()` and continue.

### Lab 11.1
Read `Lab-11-Sharding/LAB11_1_DECISION_MATRIX.md`. The decision matrix is the written part of the exercise. `lab11_1_resharding.js` contains an optional resharding demonstration; run it only after the two-shard cluster is healthy.

### Lab 11.2
Still in mongosh, run:

```javascript
load("/scripts/prepare_lab11_2.js")
```

The scripts folder is mounted into the mongos container. Exit mongosh, then from `Lab-11-Sharding` run:

```powershell
py -m pip install -r requirements.txt
py python/insert_data.py
```

Then reconnect to mongos and run:

```javascript
load("/scripts/verify_lab11_2.js")
```

The verification script prints the shard statistics and explain plans. Actual distribution varies by MongoDB version, chunk placement, and balancing. Record your own output. If the output does not show the expected pattern, do not fabricate it; capture the result and investigate with `sh.status()`.

Stop Lab 11 when finished:

```powershell
docker compose down
```

## Lab 12.1 start (PowerShell)
Open PowerShell in `Lab-12-Security`:

```powershell
docker compose up -d mongodb
docker compose ps
```

The first startup creates the root user using the demo credentials in `docker-compose.yml`. Change them before use. Then create the application roles and users:

```powershell
docker compose exec mongodb mongosh -u root -p "ChangeMe_Root_123!" --authenticationDatabase admin --file /scripts/setup_users.js
```

Test the read-only user:

```powershell
docker compose exec mongodb mongosh -u orders_reader -p "ChangeMe_Read_123!" --authenticationDatabase lab12
```

At the prompt:

```javascript
use lab12
db.orders_public.find()
db.orders.insertOne({order_id:"blocked"})
```

The view query should work; the insert should fail with an authorization error.

Test the writer:

```powershell
docker compose exec mongodb mongosh -u orders_writer -p "ChangeMe_Write_123!" --authenticationDatabase lab12
```

At the prompt:

```javascript
use lab12
db.orders.insertOne({order_id:"ORD-TEST",customer_id:"C-TEST",status:"created"})
db.employees.find()
```

The insert should work; the employee query should fail.

Test the HR-limited user:

```powershell
docker compose exec mongodb mongosh -u hr_reader -p "ChangeMe_HR_123!" --authenticationDatabase lab12
```

At the prompt:

```javascript
use lab12
db.employees_public.find()
db.employees.find()
```

The view should omit `salary`; direct access to `employees` should fail.

### Reset Lab 12.1
`docker compose down -v` deletes the database volume. Use this only if you want to start the lab from scratch.

## Lab 12.2 TLS (separate deployment)
Open PowerShell in `Lab-12-Security`. Generate certificates:

```powershell
docker run --rm -v "${PWD}/certificates:/certificates" -v "${PWD}/scripts:/scripts" alpine:3.20 sh /scripts/generate_certs.sh
```

Start the TLS-only MongoDB service:

```powershell
docker compose -f docker-compose.tls.yml up -d
docker compose -f docker-compose.tls.yml ps
```

Install Python dependency and test both connection types:

```powershell
py -m pip install -r requirements.txt
py python/test_tls.py
```

The script expects the plaintext connection to fail and the TLS connection with the CA and client certificate to succeed.

Stop the TLS deployment:

```powershell
docker compose -f docker-compose.tls.yml down
```

## Docker Hub submission
Build and publish only after local tests pass. Replace `YOUR_DOCKERHUB_USERNAME` with your own Docker Hub username:

```powershell
docker build -f Dockerfile.mongo -t YOUR_DOCKERHUB_USERNAME/mongodb-lab11-12:1.0 .
docker login
docker push YOUR_DOCKERHUB_USERNAME/mongodb-lab11-12:1.0
```

The custom image includes the lab scripts and deployment files. Docker Compose launches the multi-container cluster; keep the compose files alongside the image when demonstrating the labs. Do not bake passwords or generated private certificates into the image.

**Important for grading:** If the instructor expects a self-contained image that starts all four labs from one `docker run`, confirm that requirement with them. A multi-service sharded cluster is correctly orchestrated with Docker Compose, not represented by a single MongoDB container.

## Evidence checklist
- [ ] `docker compose ps` showing config server, two shards and mongos.
- [ ] `sh.status()` showing both shards.
- [ ] 10,000 documents inserted into each Lab 11.2 collection.
- [ ] `stats().shards` output for both collections.
- [ ] `explain("executionStats")` output for both range queries.
- [ ] RBAC success and denied-operation screenshots.
- [ ] TLS script showing plaintext failure and TLS ping success.
- [ ] Docker Hub repository page and pushed image tag.
- [ ] Final PDF updated with your real Docker Hub URL and screenshots.
