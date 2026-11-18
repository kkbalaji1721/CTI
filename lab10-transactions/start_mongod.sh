#!/bin/bash
# Starts mongod as a single-node replica set "rs0" and waits until it is PRIMARY.
# Safe to call again after a crash (used by durability_demo.sh).
mkdir -p /data/db /var/log
mongod --replSet rs0 --bind_ip_all --dbpath /data/db \
       --logpath /var/log/mongod.log --logappend --fork > /dev/null || exit 1

for i in $(seq 1 60); do
  mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' > /dev/null 2>&1 && break
  sleep 1
done

mongosh --quiet --eval '
try { rs.status(); }
catch (e) { rs.initiate({_id:"rs0", members:[{_id:0, host:"localhost:27017"}]}); }
' > /dev/null 2>&1

for i in $(seq 1 60); do
  mongosh --quiet --eval 'db.hello().isWritablePrimary' 2>/dev/null | grep -q true && { echo "[mongod] replica set rs0 PRIMARY ready"; exit 0; }
  sleep 1
done
echo "[mongod] ERROR: replica set did not become PRIMARY"; exit 1
