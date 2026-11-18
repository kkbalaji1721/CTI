# Exercise-10 – MongoDB Transactions (Lab 10.1 + Lab 10.2)

Everything runs **inside one Docker image**: MongoDB 7 (single-node replica set `rs0`,
required for transactions) + Python 3 + PyMongo + all lab scripts.

## Files
| File | Purpose |
|---|---|
| `Dockerfile`, `entrypoint.sh`, `start_mongod.sh` | Build the image, start mongod + initiate the replica set |
| `common.py` | `run_transaction()` – session/transaction + **exponential-backoff retry** on `TransientTransactionError` |
| `lab10_1_bank_transfer.py` | **Lab 10.1** + retry activity |
| `lab10_2_inventory.py` | **Lab 10.2** – reservation, 8-thread contention, 1/4/8/16-thread throughput + chart, findAndModify comparison |
| `lab10_3_durability.py`, `durability_demo.sh` | Bonus: journaling / durability (kill -9 crash test) |
| `run_all.sh` | Runs everything, saves logs + chart in `/app/results` |
| `make_submission_pdf.py` | Makes the PDF containing your Docker Hub URL |

## 1. Build and test locally
```bash
docker build -t YOUR_DOCKERHUB_USERNAME/mongodb-lab10:latest .
docker run -d --name lab10 YOUR_DOCKERHUB_USERNAME/mongodb-lab10:latest
docker exec -it lab10 /app/run_all.sh          # runs all labs (about 1-2 minutes)
```
Run one lab at a time:
```bash
docker exec -it lab10 python3 /app/lab10_1_bank_transfer.py
docker exec -it lab10 python3 /app/lab10_2_inventory.py
docker exec -it lab10 /app/durability_demo.sh
docker exec -it lab10 mongosh lab10          # inspect data manually
```
Every check prints `[PASS]` / `[FAIL]`. Expected key results:
* 10.1: successful transfer A=800/B=700; insufficient funds -> balances unchanged; crash after debit+credit -> both rolled back; concurrent transfers all succeed with retries.
* 10.2: 8 threads / stock 5 -> **5 succeed, 3 out_of_stock, stock 0, 5 orders**; throughput table + `throughput.png`; findAndModify leaves stock/orders inconsistent when the order insert fails, the transaction does not.

Copy the chart out (for screenshots): `docker cp lab10:/app/results ./results`

> Apple Silicon (M1/M2/M3) users: build with `docker buildx build --platform linux/amd64 -t USER/mongodb-lab10:latest .`
> so the image also works on the grader's machine.

## 2. Push to Docker Hub
1. Create a free account at https://hub.docker.com
2. `docker login`
3. `docker push YOUR_DOCKERHUB_USERNAME/mongodb-lab10:latest`
4. On hub.docker.com open the repository and make sure it is **Public**.
5. Your URL: `https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/mongodb-lab10`
6. Verify from scratch: `docker rm -f lab10 && docker rmi USER/mongodb-lab10 && docker run -d --name lab10 USER/mongodb-lab10 && docker exec -it lab10 /app/run_all.sh`

## 3. Create the PDF
```bash
pip install reportlab
python make_submission_pdf.py --name "Your Name" \
  --url https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/mongodb-lab10 \
  --image YOUR_DOCKERHUB_USERNAME/mongodb-lab10:latest
```
(or just paste the URL into Word/Google Docs and export as PDF.) Submit `Lab10_Submission.pdf`.

## Concepts (for your demonstration / viva)
* **Atomicity** – all operations in a transaction commit together or none do (abort -> rollback).
* **Snapshot isolation** – a transaction reads a consistent snapshot; if another transaction modified a document you try to write, MongoDB raises **WriteConflict** (code 112) labelled `TransientTransactionError`; the app should retry the whole transaction.
* **Backoff** – wait `0.1 * 2**attempt` s (+ jitter) so retrying threads do not collide again.
* **UnknownTransactionCommitResult** – commit outcome unknown (network); retry only `commitTransaction`.
* **Optimistic concurrency** – the `version` field is checked/bumped in the update filter.
* **Durability / journaling** – WiredTiger journals writes (flush ~100 ms; immediately with `j:true` or `w:"majority"`), so after a crash mongod replays the journal and committed data survives, uncommitted transactions vanish.
* Note: PyMongo has no `WriteConflict` exception class – it arrives as `OperationFailure` (code 112) with the `TransientTransactionError` label, which is why `run_transaction` checks the label.
