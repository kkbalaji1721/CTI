# Lab 13 – MongoDB Replica Set: Docker Compose, Kubernetes, Terraform

| Lab | What | Files |
|---|---|---|
| 13.1 | 3-node replica set, keyFile auth, PyMongo failover test | `docker-compose.yml`, `Dockerfile.mongo`, `scripts/`, `tools/` |
| 13.1 Activity | Prometheus exporter sidecar on node 1 (+ Prometheus UI) | `mongodb-exporter` + `prometheus` services, `prometheus/prometheus.yml` |
| 13.2 | Kubernetes StatefulSet (headless Service, PVCs, keyfile InitContainer) | `k8s/` |
| Atlas | Free-tier cluster with Terraform | `terraform/main.tf` |

## 1. Run the demo (what the grader will see)

```bash
cp .env.example .env            # put your Docker Hub username in DOCKERHUB_USER
docker compose pull             # pulls YOUR images from Docker Hub (or: docker compose build)
docker compose up -d
docker compose logs rs-init     # shows "[rs-init] Done." and the 3 members
docker compose ps               # 3 mongo nodes "healthy"
```

Verify the three members (Lab step 3):
```bash
docker compose run --rm tools python tools/verify_rs.py
```
Expected: `RESULT: PASS - 1 PRIMARY + 2 SECONDARY, all healthy`

Failover with PyMongo (Lab step 4) – writes continuously, steps the primary down after 8 s:
```bash
docker compose run --rm tools python tools/failover_test.py --duration 40 --stepdown-after 8
```
Watch for `>>> rs.stepDown()`, `primary is now ...` changing to another node, a short pause, then writes OK again.
Also try the "hard" version: in a 2nd terminal run `docker stop prod-mongo-1` during the test, then `docker start prod-mongo-1`.

Manual mongosh (the lab's wording):
```bash
docker exec -it prod-mongo-1 mongosh -u admin -p AdminPass123 --authenticationDatabase admin --eval "rs.status().members.map(m=>[m.name,m.stateStr])"
```

**Activity 13.1 – monitoring:** open http://localhost:9216/metrics (exporter), then http://localhost:9090/targets
(Prometheus, target should be UP) and query `mongodb_up` or `mongodb_ss_connections`.

Stop everything: `docker compose down` (add `-v` to delete data/keyfile).

## 2. Publish to Docker Hub (submission)

```bash
docker login
export DOCKERHUB_USER=<your-username>      # Windows PowerShell: $env:DOCKERHUB_USER="<your-username>"
docker compose build
docker compose push                         # pushes <user>/lab13-mongo:1.0 and <user>/lab13-tools:1.0
```
Your URLs: `https://hub.docker.com/r/<user>/lab13-mongo` and `https://hub.docker.com/r/<user>/lab13-tools`
(repositories must be **Public** so the grader can pull). Then make the PDF:
```bash
pip install reportlab
python make_submission_pdf.py --user <your-username> --name "Your Name" --roll "Your ID"
```

## 3. Lab 13.2 – Kubernetes
Needs a cluster (Docker Desktop → Settings → Kubernetes → Enable, or minikube/kind).
```bash
cd k8s && ./deploy-and-init.sh            # creates Secret, applies manifests, rs.initiate, creates admin
kubectl get pods -w                       # mongo-0, mongo-1, mongo-2 Running
kubectl delete pod mongo-2                # Kubernetes recreates it
kubectl exec mongo-0 -- mongosh -u admin -p AdminPass123 --authenticationDatabase admin --eval "rs.status().members.map(m=>[m.name,m.stateStr])"
kubectl get pvc                           # data-mongo-0/1/2 survive pod deletion
```
Manual equivalent of the script, per the lab text: `kubectl apply -f .` (after creating the Secret
`kubectl create secret generic mongo-keyfile --from-file=keyfile=./keyfile`), then `kubectl exec -it mongo-0 -- mongosh`
and run `rs.initiate({...})`.

**Deviation from the lab text (on purpose):** the text says the InitContainer *generates* a keyfile on mongo-0 and copies it
to a shared emptyDir. An emptyDir is per-pod, so each pod would end up with a different key and could not authenticate to
the others. The correct pattern is: one keyfile stored in a Secret, and the InitContainer copies it to an emptyDir with
owner `mongodb` and mode `400` (Secret mounts cannot be chown'ed, and mongod rejects loose permissions).

## 4. Terraform (Atlas M0)
```bash
export MONGODB_ATLAS_PUBLIC_KEY=... MONGODB_ATLAS_PRIVATE_KEY=...
cd terraform && terraform init
terraform apply -var atlas_org_id=<org-id> -var atlas_user_password='<strong-password>'
terraform output -raw cluster_uri
```
Fixes versus the chapter reference `main.tf`: M0 needs `provider_name = "TENANT"` + `backing_provider_name = "AWS"`;
removed arguments invalid for M0 (`serverless`, `cloud_backup`, `auto_scaling_disk_gb_enabled`); added the empty
`provider` block; `ip_access_list` → `project_ip_access_list`; output URI no longer duplicates `mongodb+srv://`.

## 5. Docker Compose vs Kubernetes
| | Docker Compose | Kubernetes StatefulSet |
|---|---|---|
| Self-healing | `restart: unless-stopped` restarts a crashed container on the same host | Controller recreates pods, reschedules on other nodes |
| Network identity | Container names / service DNS | Stable per-pod DNS via headless Service |
| Storage | Named volumes | PVC per pod via volumeClaimTemplates, follows the pod |
| Scaling | Edit file, add services by hand | `kubectl scale statefulset mongo --replicas=5` (then `rs.add`) |
| Complexity | One file, runs on a laptop | Several manifests, cluster needed – much more to learn/operate |
| Replica-set init | Automated by `rs-init` one-shot job | Manual step (or Job/operator) |

## Notes
* Passwords in `.env.example` are lab defaults – change them for anything real.
* `0.0.0.0/0` in the Terraform IP list is for training only.
* Connecting PyMongo from your *host* to this replica set fails server discovery, because members advertise
  container hostnames. That is why the demo runs PyMongo inside the compose network (`tools` service).
