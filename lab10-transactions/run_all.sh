#!/bin/bash
# Runs every Lab 10 task and saves logs in /app/results
cd /app
mkdir -p /app/results
python3 lab10_1_bank_transfer.py  2>&1 | tee /app/results/lab10_1_output.log
python3 lab10_2_inventory.py      2>&1 | tee /app/results/lab10_2_output.log
./durability_demo.sh              2>&1 | tee /app/results/lab10_3_output.log
echo; echo "All done. Logs and chart are in /app/results"
