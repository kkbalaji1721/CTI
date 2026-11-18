#!/bin/bash
# Initiates the replica set and creates users. Runs in the network namespace of
# mongo-rs0-1, so connections are "localhost" and MongoDB's localhost exception
# allows rs.initiate() + creating the first user on an auth-enabled server.
set -uo pipefail
export MONGO_ADMIN_USER="${MONGO_ADMIN_USER:-admin}"
export MONGO_ADMIN_PASSWORD="${MONGO_ADMIN_PASSWORD:-AdminPass123}"
export EXPORTER_USER="${EXPORTER_USER:-exporter}"
export EXPORTER_PASSWORD="${EXPORTER_PASSWORD:-ExporterPass123}"

# Idempotent: already initialised and admin exists?
if mongosh --quiet -u "$MONGO_ADMIN_USER" -p "$MONGO_ADMIN_PASSWORD" --authenticationDatabase admin \
     --eval "rs.status().ok" 2>/dev/null | grep -q '^1$'; then
  echo "[rs-init] Replica set already initialised - nothing to do."; exit 0
fi

echo "[rs-init] Initiating replica set rs0 ..."
mongosh --quiet --eval '
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "prod-mongo-1:27017", priority: 2 },
    { _id: 1, host: "prod-mongo-2:27017", priority: 1 },
    { _id: 2, host: "prod-mongo-3:27017", priority: 1 }
  ]
})' || { echo "[rs-init] rs.initiate failed"; exit 1; }

echo "[rs-init] Waiting for this node to become PRIMARY ..."
for i in $(seq 1 60); do
  mongosh --quiet --eval 'db.hello().isWritablePrimary' 2>/dev/null | grep -q true && break
  sleep 2
done

echo "[rs-init] Creating admin user ..."
mongosh --quiet --eval '
db.getSiblingDB("admin").createUser({
  user: process.env.MONGO_ADMIN_USER, pwd: process.env.MONGO_ADMIN_PASSWORD,
  roles: [{ role: "root", db: "admin" }]
})' || { echo "[rs-init] createUser failed"; exit 1; }

echo "[rs-init] Creating monitoring user for the Prometheus exporter ..."
mongosh --quiet -u "$MONGO_ADMIN_USER" -p "$MONGO_ADMIN_PASSWORD" --authenticationDatabase admin --eval '
db.getSiblingDB("admin").createUser({
  user: process.env.EXPORTER_USER, pwd: process.env.EXPORTER_PASSWORD,
  roles: [{ role: "clusterMonitor", db: "admin" }, { role: "read", db: "local" }]
})' || { echo "[rs-init] exporter user failed"; exit 1; }

echo "[rs-init] Done. Members:"
mongosh --quiet -u "$MONGO_ADMIN_USER" -p "$MONGO_ADMIN_PASSWORD" --authenticationDatabase admin \
  --eval 'rs.status().members.forEach(m => print(m.name, m.stateStr))'
