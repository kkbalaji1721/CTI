"""
Lab 5.1 - Build a Sales Analytics Pipeline
==========================================
Objective : Construct aggregation pipelines for a sales analytics system.

Steps covered
  1. Create an `orders` collection (customer, product, quantity, unit_price,
     order_date, status) and insert 26 orders (6 customers, 8 products).
  2. Monthly revenue  (group by month, sum quantity * unit_price), sorted by month.
  3. Top 3 customers by total spending, with the list of products they bought.
  4. Average order value per status category.

Run     : python lab_5_1_sales_analytics.py
Needs   : pip install pymongo      and a running MongoDB (default localhost:27017)
          (use a different server with:  set MONGO_URI=mongodb://host:port )
Data    : lab_5_1_orders.json  (same folder; the documents inserted by this script)
"""

import os
import sys

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "lab5_1_sales"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_5_1_orders.json")

# Reusable expression: order value = quantity * unit_price (rounded to cents
# so floating-point noise such as 29.970000000000002 never shows up).
ORDER_TOTAL = {"$round": [{"$multiply": ["$quantity", "$unit_price"]}, 2]}


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

    # ------------------------------------------------------------------
    # STEP 1 - Create the collection and insert the orders
    # ------------------------------------------------------------------
    banner("STEP 1: Create 'orders' collection and insert data")
    orders.drop()                                    # start clean on every run
    with open(DATA_FILE, encoding="utf-8") as f:
        docs = json_util.loads(f.read())["orders"]   # {"$date": ...} -> datetime
    orders.insert_many(docs)

    print(f"Database   : {DB_NAME}")
    print(f"Collection : orders")
    print(f"Inserted   : {orders.count_documents({})} orders")
    print(f"Customers  : {len(orders.distinct('customer'))}   "
          f"Products: {len(orders.distinct('product'))}\n")
    print(f"{'order_id':<9} {'customer':<7} {'product':<28} {'qty':>3} "
          f"{'price':>7} {'order_date':<10} status")
    print("-" * 78)
    for o in orders.find({}, {"_id": 0}).sort("order_id", 1):
        print(f"{o['order_id']:<9} {o['customer']:<7} {o['product']:<28} {o['quantity']:>3} "
              f"{o['unit_price']:>7.2f} {o['order_date']:%Y-%m-%d} {o['status']}")

    # ------------------------------------------------------------------
    # STEP 2 - Monthly revenue
    # ------------------------------------------------------------------
    banner("STEP 2: Monthly revenue (sum of quantity * unit_price)")
    pipeline_monthly = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$order_date"}},
            "revenue": {"$sum": {"$multiply": ["$quantity", "$unit_price"]}},
            "orders": {"$sum": 1},
        }},
        {"$project": {"_id": 0, "month": "$_id", "orders": 1,
                      "revenue": {"$round": ["$revenue", 2]}}},
        {"$sort": {"month": 1}},
    ]
    print(f"{'Month':<9} {'Orders':>6} {'Revenue':>12}")
    print("-" * 29)
    grand_total = 0
    for row in orders.aggregate(pipeline_monthly):
        grand_total += row["revenue"]
        print(f"{row['month']:<9} {row['orders']:>6} {row['revenue']:>12,.2f}")
    print("-" * 29)
    print(f"{'TOTAL':<9} {orders.count_documents({}):>6} {grand_total:>12,.2f}")

    # ------------------------------------------------------------------
    # STEP 3 - Top 3 customers by total spending (+ products they bought)
    # ------------------------------------------------------------------
    banner("STEP 3: Top 3 customers by total spending")
    pipeline_top3 = [
        {"$addFields": {"order_total": ORDER_TOTAL}},
        {"$group": {
            "_id": "$customer",
            "total_spent": {"$sum": "$order_total"},
            "orders": {"$sum": 1},
            "products": {"$addToSet": "$product"},      # unique products bought
        }},
        {"$sort": {"total_spent": -1, "_id": 1}},       # highest spender first
        {"$limit": 3},
        {"$project": {"_id": 0, "customer": "$_id", "orders": 1, "products": 1,
                      "total_spent": {"$round": ["$total_spent", 2]}}},
    ]
    for rank, row in enumerate(orders.aggregate(pipeline_top3), start=1):
        print(f"#{rank}  {row['customer']:<7} total spent = {row['total_spent']:>8,.2f}"
              f"   ({row['orders']} orders)")
        for p in sorted(row["products"]):
            print(f"      - {p}")

    # ------------------------------------------------------------------
    # STEP 4 - Average order value per status
    # ------------------------------------------------------------------
    banner("STEP 4: Average order value per status")
    pipeline_status = [
        {"$addFields": {"order_total": ORDER_TOTAL}},
        {"$group": {
            "_id": "$status",
            "avg_order_value": {"$avg": "$order_total"},
            "orders": {"$sum": 1},
            "total_value": {"$sum": "$order_total"},
        }},
        {"$project": {"_id": 0, "status": "$_id", "orders": 1,
                      "avg_order_value": {"$round": ["$avg_order_value", 2]},
                      "total_value": {"$round": ["$total_value", 2]}}},
        {"$sort": {"avg_order_value": -1}},
    ]
    print(f"{'Status':<11} {'Orders':>6} {'Total value':>13} {'Avg order value':>16}")
    print("-" * 49)
    for row in orders.aggregate(pipeline_status):
        print(f"{row['status']:<11} {row['orders']:>6} {row['total_value']:>13,.2f} "
              f"{row['avg_order_value']:>16,.2f}")

    banner("Lab 5.1 complete")
    client.close()


if __name__ == "__main__":
    main()
