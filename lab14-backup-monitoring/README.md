# Chapter 14 Labs – MongoDB Monitoring, Backup & Restore (Docker)

Everything (MongoDB 7 as a single-node replica set + Python scripts) runs in ONE container.

## 1. Build and test locally
```bash
docker build -t mongodb-lab14 .
mkdir -p output
docker run -it --rm -v "$PWD/output:/app/output" mongodb-lab14
```
The container starts MongoDB, runs the full demo of both labs, then leaves you in a shell.
Evidence (`metrics.log`, `benchmark_results.md`) appears in `./output`.

## 2. Manual commands inside the container
```bash
python3 monitor.py                                   # table every 30 s -> metrics.log
python3 monitor.py --webhook https://hooks.slack.com/services/XXX   # webhook extension
python3 backup_verify.py backup                      # one timestamped mongodump
python3 backup_verify.py schedule                    # hourly (add --every-minutes 1 for demo)
python3 backup_verify.py verify                      # restore verification
python3 backup_verify.py benchmark                   # 1k / 10k / 100k + RPO/RTO
```
To show alerts firing: `python3 monitor.py --iterations 1 --cache-threshold 101 --lag-threshold -1`

## 3. Push to Docker Hub
```bash
docker login
docker tag mongodb-lab14 YOUR_USERNAME/mongodb-lab14:latest
docker push YOUR_USERNAME/mongodb-lab14:latest
```
URL to submit: `https://hub.docker.com/r/YOUR_USERNAME/mongodb-lab14` (make the repo **public**).

## 4. Make the PDF
```bash
docker run --rm -v "$PWD:/out" -w /out mongodb-lab14 python3 /app/make_pdf.py \
  https://hub.docker.com/r/YOUR_USERNAME/mongodb-lab14 --name "Your Name" --out submission.pdf
```
(`entrypoint` starts MongoDB first; that is harmless.) Submit `submission.pdf`.
