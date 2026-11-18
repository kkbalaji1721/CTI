#!/bin/bash
# Lab 13.2 helper: create keyfile Secret, apply manifests, initiate the replica set.
set -euo pipefail
cd "$(dirname "$0")"
[ -f keyfile ] || openssl rand -base64 756 > keyfile
kubectl create secret generic mongo-keyfile --from-file=keyfile=./keyfile --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f mongo-headless-svc.yaml -f mongo-statefulset.yaml
echo "Waiting for pods..."; kubectl rollout status statefulset/mongo --timeout=300s
kubectl exec mongo-0 -- mongosh --quiet --eval '
rs.initiate({_id:"rs0", members:[
 {_id:0, host:"mongo-0.mongo-headless-svc:27017"},
 {_id:1, host:"mongo-1.mongo-headless-svc:27017"},
 {_id:2, host:"mongo-2.mongo-headless-svc:27017"}]})'
sleep 15
kubectl exec mongo-0 -- mongosh --quiet --eval '
db.getSiblingDB("admin").createUser({user:"admin",pwd:"AdminPass123",roles:["root"]})'
kubectl exec mongo-0 -- mongosh --quiet -u admin -p AdminPass123 --authenticationDatabase admin \
  --eval 'rs.status().members.forEach(m=>print(m.name,m.stateStr))'
