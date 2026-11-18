"""
Lab 5.2 - Try it yourself: $lookup with a pipeline sub-expression
=================================================================
Task : Use $lookup with `let` + `pipeline` (MongoDB 3.6+) so the joined
       documents are FILTERED ON THE FOREIGN SIDE before they are returned.

Plain $lookup (localField/foreignField) returns EVERY matching foreign
document. With a sub-pipeline you can $match / $project inside the
foreign collection first, so unwanted documents never come back.

    "let":      {"pid": "$product_id"}            # variables from the OUTER doc
    "pipeline": [{"$match": {"$expr": {"$eq": ["$product_id", "$$pid"]}}}, ...]
                                                  # $$pid = the outer variable

Demo A : products -> orders, joining ONLY completed orders
         (compared with a plain $lookup that returns every order)
Demo B : orders -> products, joining ONLY premium electronics
         (category = "Electronics" AND base_price >= 100)

Run     : python lab_5_2_try_it_lookup_subpipeline.py
Needs   : pip install pymongo      and a running MongoDB (default localhost:27017)
Data    : lab_5_2_try_it_data.json  (same folder; "products" and "orders")
"""

import os
import sys

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lab5_2_subpipeline"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_5_2_try_it_data.json")


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

    banner("Load data")
    products.drop()
    orders.drop()
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json_util.loads(f.read())
    products.insert_many(data["products"])
    orders.insert_many(data["orders"])
    print(f"products: {products.count_documents({})} docs, orders: {orders.count_documents({})} docs")

    # ------------------------------------------------------------------
    # DEMO A - foreign-side filter: only COMPLETED orders are joined
    # ------------------------------------------------------------------
    banner("DEMO A: products + COMPLETED orders only (sub-pipeline filter)")
    pipeline_a = [
        # 1) plain $lookup -> brings back ALL orders of the product (for comparison)
        {"$lookup": {
            "from": "orders",
            "localField": "product_id",
            "foreignField": "product_id",
            "as": "all_orders",
        }},
        # 2) $lookup with let + pipeline -> filter happens INSIDE the orders collection
        {"$lookup": {
            "from": "orders",
            "let": {"pid": "$product_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$product_id", "$$pid"]},        # the join condition
                    {"$eq": ["$status", "completed"]},        # the extra foreign filter
                ]}}},
                {"$project": {"_id": 0, "order_id": 1, "quantity": 1}},
            ],
            "as": "completed_orders",
        }},
        {"$project": {
            "_id": 0, "product_id": 1, "name": 1,
            "all_orders": {"$size": "$all_orders"},
            "completed_orders": {"$size": "$completed_orders"},
            "completed_units": {"$sum": "$completed_orders.quantity"},
            "completed_ids": "$completed_orders.order_id",
        }},
        {"$sort": {"product_id": 1}},
    ]
    print(f"{'product_id':<10} {'name':<28} {'all':>3} {'completed':>9} {'units':>5}")
    print("-" * 60)
    for r in products.aggregate(pipeline_a):
        print(f"{r['product_id']:<10} {r['name']:<28} {r['all_orders']:>3} "
              f"{r['completed_orders']:>9} {r['completed_units']:>5}")
    print("\n'all' = plain $lookup (every order); 'completed' = $lookup with sub-pipeline.")
    print("Webcam HD has 2 orders but both were cancelled, so 0 completed are joined.")

    # ------------------------------------------------------------------
    # DEMO B - foreign-side filter on the PRODUCT: premium electronics only
    # ------------------------------------------------------------------
    banner("DEMO B: orders joined ONLY to premium electronics (>= 100)")
    pipeline_b = [
        {"$lookup": {
            "from": "products",
            "let": {"pid": "$product_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$product_id", "$$pid"]},
                    {"$eq": ["$category", "Electronics"]},
                    {"$gte": ["$base_price", 100]},
                ]}}},
            ],
            "as": "premium_product",         # [] for every non-premium order
        }},
        {"$match": {"premium_product": {"$ne": []}}},   # drop orders with no premium match
        {"$unwind": "$premium_product"},
        {"$project": {
            "_id": 0, "order_id": 1,
            "order_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}},
            "product": "$premium_product.name",
            "category": "$premium_product.category",
            "quantity": 1,
            "line_total": {"$round": [{"$multiply": ["$quantity", "$premium_product.base_price"]}, 2]},
        }},
        {"$sort": {"order_date": 1, "order_id": 1}},
    ]
    print(f"{'order_id':<9} {'order_date':<10}  {'product':<28} {'category':<11} "
          f"{'qty':>3} {'total':>8}")
    print("-" * 76)
    n = 0
    for r in orders.aggregate(pipeline_b):
        n += 1
        print(f"{r['order_id']:<9} {r['order_date']:<10}  {r['product']:<28} {r['category']:<11} "
              f"{r['quantity']:>3} {r['line_total']:>8.2f}")
    print("-" * 76)
    print(f"{n} of {orders.count_documents({})} orders matched a premium electronics product.")

    banner("Try-it-yourself ($lookup sub-pipeline) complete")
    client.close()


if __name__ == "__main__":
    main()
