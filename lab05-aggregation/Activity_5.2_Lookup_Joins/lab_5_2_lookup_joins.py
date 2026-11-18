"""
Lab 5.2 - Join Data with $lookup
================================
Objective : Use $lookup to perform cross-collection joins and analyse the results.

Steps covered
  1. Create a `products` collection (name, category, base_price) and an `orders`
     collection that REFERENCES products by product_id (nothing is embedded).
  2. $lookup pipeline: order date, product name, quantity and the computed
     total (quantity * base_price).
  3. Products that have NEVER been ordered (left outer join using $lookup,
     followed by a $match on the empty join result).

Run     : python lab_5_2_lookup_joins.py
Needs   : pip install pymongo      and a running MongoDB (default localhost:27017)
          (use a different server with:  set MONGO_URI=mongodb://host:port )
Data    : lab_5_2_data.json  (same folder; holds both collections:
          "products" and "orders")
"""

import os
import sys

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lab5_2_lookup"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_5_2_data.json")


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
    db = client[DB_NAME]
    products, orders = db["products"], db["orders"]

    # ------------------------------------------------------------------
    # STEP 1 - Create both collections (orders reference products by id)
    # ------------------------------------------------------------------
    banner("STEP 1: Create 'products' and 'orders' (referenced, not embedded)")
    products.drop()
    orders.drop()
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json_util.loads(f.read())
    products.insert_many(data["products"])
    orders.insert_many(data["orders"])
    print(f"Database : {DB_NAME}")
    print(f"products : {products.count_documents({})} documents")
    print(f"orders   : {orders.count_documents({})} documents\n")

    print("products  (product_id, name, category, base_price)")
    print("-" * 62)
    for p in products.find({}, {"_id": 0}).sort("product_id", 1):
        print(f"{p['product_id']}  {p['name']:<28} {p['category']:<12} {p['base_price']:>8.2f}")

    print("\norders  (note: only product_id is stored, not the product name/price)")
    print("-" * 62)
    for o in orders.find({}, {"_id": 0}).sort("order_id", 1).limit(5):
        print(f"{o['order_id']}  {o['customer']:<7} {o['product_id']}  qty={o['quantity']}  "
              f"{o['order_date']:%Y-%m-%d}  {o['status']}")
    print("... (18 orders in total)")

    # ------------------------------------------------------------------
    # STEP 2 - $lookup: orders + products -> date, product name, qty, total
    # ------------------------------------------------------------------
    banner("STEP 2: $lookup join - order date, product, quantity, total")
    pipeline_join = [
        {"$sort": {"order_date": 1, "order_id": 1}},
        {"$lookup": {
            "from": "products",              # collection to join with
            "localField": "product_id",      # field in orders
            "foreignField": "product_id",    # field in products
            "as": "product",                 # result array
        }},
        {"$unwind": "$product"},             # 1-element array -> plain sub-document
        {"$project": {
            "_id": 0,
            "order_id": 1,
            "order_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}},
            "product_name": "$product.name",
            "quantity": 1,
            "base_price": "$product.base_price",
            "total": {"$round": [{"$multiply": ["$quantity", "$product.base_price"]}, 2]},
        }},
    ]
    print(f"{'order_id':<9} {'order_date':<10}  {'product_name':<28} {'qty':>3} "
          f"{'base_price':>10} {'total':>9}")
    print("-" * 77)
    grand = 0
    count = 0
    for r in orders.aggregate(pipeline_join):
        grand += r["total"]
        count += 1
        print(f"{r['order_id']:<9} {r['order_date']:<10}  {r['product_name']:<28} "
              f"{r['quantity']:>3} {r['base_price']:>10.2f} {r['total']:>9.2f}")
    print("-" * 77)
    print(f"{count} joined orders, combined value = {grand:,.2f}")

    # ------------------------------------------------------------------
    # STEP 3 - Products that have never been ordered
    #          (left outer join: $lookup + $match on empty array)
    # ------------------------------------------------------------------
    banner("STEP 3: Products that have NEVER been ordered")
    pipeline_never = [
        {"$lookup": {
            "from": "orders",
            "localField": "product_id",
            "foreignField": "product_id",
            "as": "matching_orders",         # [] when the product was never ordered
        }},
        {"$match": {"matching_orders": {"$size": 0}}},   # keep only the empty joins
        {"$project": {"_id": 0, "product_id": 1, "name": 1,
                      "category": 1, "base_price": 1}},
        {"$sort": {"product_id": 1}},
    ]
    never = list(products.aggregate(pipeline_never))
    print(f"{'product_id':<10} {'name':<20} {'category':<12} {'base_price':>10}")
    print("-" * 55)
    for p in never:
        print(f"{p['product_id']:<10} {p['name']:<20} {p['category']:<12} {p['base_price']:>10.2f}")

    # Cross-check against the orders collection itself
    ordered_ids = set(orders.distinct("product_id"))
    all_ids = {p["product_id"] for p in products.find({}, {"product_id": 1})}
    print("\nCross-check:")
    print(f"  products in catalogue      : {len(all_ids)}")
    print(f"  products appearing in orders: {len(ordered_ids)}")
    print(f"  never ordered (difference)  : {len(all_ids - ordered_ids)}"
          f"  -> matches pipeline result: {len(never) == len(all_ids - ordered_ids)}")

    banner("Lab 5.2 complete")
    client.close()


if __name__ == "__main__":
    main()
