#!/bin/bash
# Starts a single-node replica set (so replSetGetStatus works) inside the container
set -e
mkdir -p /data/db /data/logs
mongod --replSet rs0 --bind_ip_all --dbpath /data/db --logpath /data/logs/mongod.log --fork >/dev/null
until mongosh --quiet --eval 'db.adminCommand("ping").ok' >/dev/null 2>&1; do sleep 1; done
mongosh --quiet --eval 'try { rs.status() } catch (e) { rs.initiate({_id:"rs0", members:[{_id:0, host:"localhost:27017"}]}) }' >/dev/null
until mongosh --quiet --eval 'db.hello().isWritablePrimary' 2>/dev/null | grep -q true; do sleep 1; done
echo ">>> MongoDB (replica set rs0) is up and PRIMARY"
exec "$@"
