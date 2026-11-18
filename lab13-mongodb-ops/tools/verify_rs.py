"""Lab 13.1 step 3: verify all three members are healthy."""
import os, sys
from pymongo import MongoClient

URI = os.getenv("MONGO_URI") or (
    f"mongodb://{os.getenv('MONGO_ADMIN_USER','admin')}:{os.getenv('MONGO_ADMIN_PASSWORD','AdminPass123')}"
    "@prod-mongo-1:27017,prod-mongo-2:27017,prod-mongo-3:27017/?replicaSet=rs0&authSource=admin")

client = MongoClient(URI, serverSelectionTimeoutMS=15000)
status = client.admin.command("replSetGetStatus")
print(f"Replica set: {status['set']}   ok={status['ok']}")
print(f"{'MEMBER':<22}{'STATE':<12}{'HEALTH':<8}")
for m in status["members"]:
    print(f"{m['name']:<22}{m['stateStr']:<12}{m['health']:<8.0f}")
states = sorted(m["stateStr"] for m in status["members"])
healthy = states == ["PRIMARY", "SECONDARY", "SECONDARY"] and all(m["health"] == 1 for m in status["members"])
print("\nRESULT:", "PASS - 1 PRIMARY + 2 SECONDARY, all healthy" if healthy else "FAIL")
sys.exit(0 if healthy else 1)
