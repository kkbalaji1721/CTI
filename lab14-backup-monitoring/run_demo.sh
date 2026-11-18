#!/bin/bash
# Runs every task of Lab 14.1 and 14.2 and saves evidence in /app/output
cd /app
echo; echo "################ LAB 14.1 - MONITORING (3 samples, 5 s apart for demo) ################"
python3 monitor.py --interval 5 --iterations 3 --log /app/output/metrics.log
echo; echo "---- Alert demo: thresholds set so that WARNINGs fire (cache>101%, lag>-1s) ----"
python3 monitor.py --iterations 1 --log /app/output/metrics.log --cache-threshold 101 --lag-threshold -1 | grep -E "WARNING|webhook"

echo; echo "################ LAB 14.2 - BACKUP / RESTORE ################"
echo "---- 1. Single timestamped backup + retention ----"
python3 backup_verify.py backup --db admin
echo "---- 2. 7-day retention policy proof ----"
python3 backup_verify.py retention-demo
echo "---- 3. Insert -> backup -> modify -> restore -> verify ----"
python3 backup_verify.py verify
echo "---- 4. Benchmark 1k / 10k / 100k documents + RPO/RTO ----"
python3 backup_verify.py benchmark
cp /data/backups/benchmark_results.md /app/output/ 2>/dev/null
echo; echo "Done. Evidence files are in /app/output (metrics.log, benchmark_results.md)."
echo "Hourly scheduler:  python3 backup_verify.py schedule"
echo "Live monitor:      python3 monitor.py   (every 30 s)"
