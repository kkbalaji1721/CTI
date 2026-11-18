#!/bin/bash
cd /app
python3 lab10_3_durability.py inspect
python3 lab10_3_durability.py write
echo; echo ">>> Simulating a crash: kill -9 mongod (no clean shutdown)"
pkill -9 mongod
sleep 3
echo ">>> Restarting mongod (WiredTiger replays the journal)"
/app/start_mongod.sh
python3 lab10_3_durability.py verify
