from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, InsertOne
from bson import ObjectId
import random

URI = "mongodb://localhost:27017"
TOTAL = 10_000
client = MongoClient(URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")
db = client["lab11"]

# Use batches to avoid holding all operations in memory.
hotspot = db["hotspot_data"]
even = db["even_data"]

# Clean only this lab's two collections before re-running.
hotspot.delete_many({})
even.delete_many({})

start = datetime(2025, 1, 1, tzinfo=timezone.utc)
batch_size = 1000

for offset in range(0, TOTAL, batch_size):
    end = min(offset + batch_size, TOTAL)
    hot_docs = []
    even_docs = []
    for i in range(offset, end):
        hot_docs.append({
            "ts": start + timedelta(seconds=i),
            "order_no": i + 1,
            "payload": "timestamp-demo"
        })
        # Random ObjectIds give distinct, non-monotonic customer identifiers.
        even_docs.append({
            "user_id": ObjectId(),
            "order_no": i + 1,
            "payload": "hashed-demo"
        })
    hotspot.insert_many(hot_docs, ordered=False)
    even.insert_many(even_docs, ordered=False)
    print(f"Inserted {end:,}/{TOTAL:,} into each collection")

print("\nFinal counts:")
print("hotspot_data:", hotspot.count_documents({}))
print("even_data:", even.count_documents({}))
print("\nData loading complete. Run scripts/verify_lab11_2.js in mongosh.")
client.close()
