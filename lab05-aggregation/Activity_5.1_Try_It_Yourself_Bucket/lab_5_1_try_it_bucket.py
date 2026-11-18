"""
Lab 5.1 - Try it yourself: categorise orders with $bucket
=========================================================
Task : Add a $bucket stage that categorises orders by TOTAL ORDER VALUE
       (quantity * unit_price) into
           small  : under $50
           medium : $50 - $200   (both ends included)
           large  : over $200

How the boundaries work
  $bucket uses [lower, upper) ranges: lower bound INCLUSIVE, upper EXCLUSIVE.
      [0, 50)        -> small   (so exactly $50.00 is NOT small)
      [50, 200.01)   -> medium  (so exactly $50.00 and exactly $200.00 are medium)
      [200.01, 1e5)  -> large   (anything above $200.00)
  Order values are rounded to cents, so 200.01 is the next possible value
  above $200.00. The data deliberately contains an order of exactly $50.00
  and exactly $200.00 to prove the edges are handled correctly.

Run     : python lab_5_1_try_it_bucket.py
Needs   : pip install pymongo      and a running MongoDB (default localhost:27017)
Data    : lab_5_1_try_it_orders.json  (same folder)
"""

import os
import sys

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lab5_1_bucket"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_5_1_try_it_orders.json")

ORDER_TOTAL = {"$round": [{"$multiply": ["$quantity", "$unit_price"]}, 2]}

# bucket lower boundary  ->  (label, human readable range)
LABELS = {0: ("SMALL", "under $50"),
          50: ("MEDIUM", "$50 - $200"),
          200.01: ("LARGE", "over $200")}


def banner(text):
    print("\n" + "=" * 70)
    print("  " + text)
    print("=" * 70)


def connect():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        sys.exit(f"[ERROR] Cannot reach MongoDB at {MONGO_URI}. "
                 "Start mongod (or set MONGO_URI) and run again.")
    print(f"[OK] Connected to MongoDB {client.server_info()['version']} at {MONGO_URI}")
    return client


def main():
    client = connect()
    orders = client[DB_NAME]["orders"]

    banner("Load data")
    orders.drop()
    with open(DATA_FILE, encoding="utf-8") as f:
        orders.insert_many(json_util.loads(f.read())["orders"])
    print(f"Inserted {orders.count_documents({})} orders into {DB_NAME}.orders")

    # ------------------------------------------------------------------
    # $bucket pipeline
    # ------------------------------------------------------------------
    banner("Orders bucketed by total order value")
    pipeline = [
        {"$addFields": {"order_total": ORDER_TOTAL}},
        {"$bucket": {
            "groupBy": "$order_total",
            "boundaries": [0, 50, 200.01, 100000],
            "default": "out_of_range",                  # catches anything outside the ranges
            "output": {
                "orders": {"$sum": 1},
                "revenue": {"$sum": "$order_total"},
                "avg_value": {"$avg": "$order_total"},
                "min_value": {"$min": "$order_total"},
                "max_value": {"$max": "$order_total"},
                "order_ids": {"$push": "$order_id"},
            },
        }},
        {"$project": {"_id": 1, "orders": 1, "order_ids": 1,
                      "revenue": {"$round": ["$revenue", 2]},
                      "avg_value": {"$round": ["$avg_value", 2]},
                      "min_value": 1, "max_value": 1}},
    ]

    print(f"{'Category':<8} {'Range':<11} {'Orders':>6} {'Revenue':>10} "
          f"{'Avg':>8} {'Min':>8} {'Max':>8}")
    print("-" * 66)
    results = list(orders.aggregate(pipeline))
    bucketed = 0
    for row in results:
        label, rng = LABELS.get(row["_id"], ("OTHER", "n/a"))
        bucketed += row["orders"]
        print(f"{label:<8} {rng:<11} {row['orders']:>6} {row['revenue']:>10,.2f} "
              f"{row['avg_value']:>8,.2f} {row['min_value']:>8,.2f} {row['max_value']:>8,.2f}")
    print("-" * 66)
    print(f"Orders bucketed: {bucketed} of {orders.count_documents({})}")

    banner("Which orders fell in each bucket?")
    for row in results:
        label, rng = LABELS.get(row["_id"], ("OTHER", "n/a"))
        ids = ", ".join(sorted(row["order_ids"]))
        print(f"{label} ({rng}) - {row['orders']} orders")
        # wrap the id list at ~66 chars
        line = "   "
        for oid in ids.split(", "):
            if len(line) + len(oid) + 2 > 68:
                print(line.rstrip())
                line = "   "
            line += oid + ", "
        print(line.rstrip(", "))

    banner("Edge-case check ($50.00 and $200.00 must both be MEDIUM)")
    # Look the order up, then see which $bucket result actually contains it.
    for edge in (50.0, 200.0):
        o = next(orders.aggregate([
            {"$addFields": {"order_total": ORDER_TOTAL}},
            {"$match": {"order_total": edge}},
            {"$limit": 1},
        ]))
        bucket = next(r for r in results if o["order_id"] in r["order_ids"])
        label, _ = LABELS[bucket["_id"]]
        print(f"{o['order_id']}  order_total = {o['order_total']:>7.2f}  -> {label}")

    banner("Try-it-yourself (bucket) complete")
    client.close()


if __name__ == "__main__":
    main()
