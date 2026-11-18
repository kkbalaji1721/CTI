#!/usr/bin/env python3
"""
Lab 10.2 - Inventory reservation with write-conflict (deadlock-like) handling.

 * inventory{product_id,name,stock,version}  orders{order_id,customer_id,items,status,total}
 * reserve_inventory(): read stock, check, decrement (optimistic version bump),
   insert pending order - all in ONE transaction
 * contention test: 8 concurrent requests, stock 5   (without / with retry)
 * throughput test: 1, 4, 8, 16 threads, transactional vs findAndModify
 * consistency demo: failure after decrement -> transaction rolls back,
   non-transactional approach leaves an inconsistent state
"""
import json
import os
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from common import (DB_NAME, RESULTS_DIR, Checker, RetriesExhausted, Stats,
                    banner, get_client, run_transaction)

PRODUCT = "P-100"
PRICE = 49.99


class OutOfStock(Exception):
    pass


class ProductNotFound(Exception):
    pass


def setup(db, stock):
    db.inventory.drop()
    db.orders.drop()
    db.create_collection("inventory")
    db.create_collection("orders")
    db.inventory.create_index("product_id", unique=True)
    db.orders.create_index("order_id", unique=True)
    db.inventory.insert_one({"product_id": PRODUCT, "name": "Mechanical Keyboard",
                             "stock": stock, "version": 0, "price": PRICE})


def reset_stock(db, stock):
    db.orders.delete_many({})
    db.inventory.update_one({"product_id": PRODUCT}, {"$set": {"stock": stock, "version": 0}})


def _order_doc(order_id, customer_id, qty):
    return {"order_id": order_id, "customer_id": customer_id,
            "items": [{"product_id": PRODUCT, "qty": qty, "price": PRICE}],
            "status": "pending", "total": round(qty * PRICE, 2),
            "created_at": datetime.now(timezone.utc)}


def reserve_inventory(client, product_id, qty, customer_id, order_id=None,
                      max_retries=10, base_delay=0.05, stats=None):
    """Transactional reservation: stock decrement + order insert are atomic."""
    db = client[DB_NAME]
    order_id = order_id or f"ORD-{uuid.uuid4().hex[:10]}"

    def body(session):
        product = db.inventory.find_one({"product_id": product_id}, session=session)
        if product is None:
            raise ProductNotFound(product_id)
        if product["stock"] < qty:
            raise OutOfStock(f"stock={product['stock']} < requested={qty}")
        # optimistic concurrency: only update the version we read, bump it
        res = db.inventory.update_one(
            {"product_id": product_id, "version": product["version"],
             "stock": {"$gte": qty}},
            {"$inc": {"stock": -qty, "version": 1}}, session=session)
        if res.modified_count != 1:
            raise OutOfStock("stock changed / insufficient")
        db.orders.insert_one(_order_doc(order_id, customer_id, qty), session=session)
        return order_id

    return run_transaction(client, body, max_retries=max_retries,
                           base_delay=base_delay, stats=stats, label=customer_id)


def reserve_nontransactional(client, product_id, qty, customer_id, order_id=None):
    """findAndModify approach: fast, but decrement and order insert are NOT atomic."""
    db = client[DB_NAME]
    order_id = order_id or f"ORD-{uuid.uuid4().hex[:10]}"
    prod = db.inventory.find_one_and_update(
        {"product_id": product_id, "stock": {"$gte": qty}},
        {"$inc": {"stock": -qty, "version": 1}},
        return_document=ReturnDocument.AFTER)
    if prod is None:
        raise OutOfStock("insufficient stock")
    db.orders.insert_one(_order_doc(order_id, customer_id, qty))   # can fail AFTER decrement!
    return order_id


def attempt(fn, *a, **k):
    try:
        fn(*a, **k)
        return "success"
    except OutOfStock:
        return "out_of_stock"
    except RetriesExhausted:
        return "write_conflict_exhausted"
    except Exception as e:
        return f"error:{type(e).__name__}"


def contention_test(client, db, requests, stock, max_retries):
    reset_stock(db, stock)
    stats = Stats()
    barrier = threading.Barrier(requests)

    def worker(i):
        barrier.wait()
        return attempt(reserve_inventory, client, PRODUCT, 1, f"CUST-{i}",
                       max_retries=max_retries, stats=stats)

    with ThreadPoolExecutor(max_workers=requests) as pool:
        outcomes = Counter(pool.map(worker, range(requests)))
    final_stock = db.inventory.find_one({"product_id": PRODUCT})["stock"]
    orders = db.orders.count_documents({"status": "pending"})
    return outcomes, stats.retries, final_stock, orders


def throughput_run(client, db, mode, workers, total_requests):
    reset_stock(db, total_requests * 10)       # plenty of stock: measure speed, not stock-outs
    stats = Stats()
    if mode == "transactional":
        fn = lambda i: attempt(reserve_inventory, client, PRODUCT, 1, f"C{i}",
                               max_retries=30, base_delay=0.005, stats=stats)
    else:
        fn = lambda i: attempt(reserve_nontransactional, client, PRODUCT, 1, f"C{i}")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = Counter(pool.map(fn, range(total_requests)))
    elapsed = time.perf_counter() - start
    ok = outcomes["success"]
    return {"mode": mode, "threads": workers, "requests": total_requests, "success": ok,
            "failed": total_requests - ok, "retries": stats.retries,
            "seconds": round(elapsed, 3), "throughput": round(ok / elapsed, 1)}


def plot(rows, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("  (matplotlib not available, skipping plot):", e)
        return False
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for mode, marker in (("transactional", "o"), ("findAndModify", "s")):
        pts = sorted((r["threads"], r["throughput"]) for r in rows if r["mode"] == mode)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=marker, label=mode)
        for x, y in pts:
            ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center")
    ax.set_xlabel("Concurrent threads")
    ax.set_ylabel("Successful reservations / second")
    ax.set_title("Lab 10.2 - Throughput vs concurrency (single hot document)")
    ax.set_xticks([1, 4, 8, 16])
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return True


def main():
    client = get_client()
    db = client[DB_NAME]
    chk = Checker()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    banner("STEP 1 - Schema + insert product with stock = 5")
    setup(db, 5)
    print("  inventory:", db.inventory.find_one({}, {"_id": 0}))

    banner("STEP 2 - Single reservation (sanity check)")
    oid = reserve_inventory(client, PRODUCT, 1, "CUST-SANITY")
    inv = db.inventory.find_one({"product_id": PRODUCT})
    print(f"  order {oid} created; stock={inv['stock']} version={inv['version']}")
    chk.check(inv["stock"] == 4 and db.orders.count_documents({}) == 1,
              "stock decremented and order inserted together")

    banner("STEP 3 - Contention: 8 simultaneous requests, only 5 units, NO retry")
    out, retries, stock, orders = contention_test(client, db, 8, 5, max_retries=0)
    print("  outcomes:", dict(out))
    print(f"  final stock={stock}, pending orders={orders}")
    print("  -> several threads fail with WriteConflict because only one transaction")
    print("     can modify the hot document at a time.")
    chk.check(5 - stock == orders, "consistency: units sold == orders created (even with failures)")

    banner("STEP 4 - Same test WITH retry/backoff (max 10 retries)")
    out, retries, stock, orders = contention_test(client, db, 8, 5, max_retries=10)
    print("  outcomes:", dict(out), "| retries performed:", retries)
    print(f"  final stock={stock}, pending orders={orders}")
    chk.check(out["success"] == 5, "exactly 5 reservations succeeded")
    chk.check(out["out_of_stock"] == 3, "remaining 3 correctly failed: stock reached zero")
    chk.check(stock == 0 and orders == 5, "stock=0 and exactly 5 orders (no overselling)")

    banner("STEP 5 - Throughput vs concurrency (1, 4, 8, 16 threads)")
    rows = []
    total = 200
    print(f"  {'mode':<14}{'threads':>8}{'ok':>6}{'fail':>6}{'retries':>9}{'sec':>8}{'ops/s':>9}")
    for mode in ("transactional", "findAndModify"):
        for workers in (1, 4, 8, 16):
            r = throughput_run(client, db, mode, workers, total)
            rows.append(r)
            print(f"  {r['mode']:<14}{r['threads']:>8}{r['success']:>6}{r['failed']:>6}"
                  f"{r['retries']:>9}{r['seconds']:>8}{r['throughput']:>9}")
    with open(os.path.join(RESULTS_DIR, "throughput.json"), "w") as f:
        json.dump(rows, f, indent=2)
    png = os.path.join(RESULTS_DIR, "throughput.png")
    if plot(rows, png):
        print(f"  chart saved to {png}")
    print("  Note: all threads fight for ONE document, so transactional throughput is")
    print("  limited by write conflicts/retries; findAndModify is a single atomic op.")

    banner("STEP 6 - Consistency: failure AFTER stock decrement")
    setup(db, 10)
    db.orders.insert_one(_order_doc("ORD-DUP", "SOMEONE", 1))   # next insert of this id will fail
    db.inventory.update_one({"product_id": PRODUCT}, {"$inc": {"stock": -1}})  # 9 left, 1 order
    s0, o0 = 9, 1
    print("  Start: stock=9, orders=1.  The next order insert will fail (duplicate order_id).")

    print("\n  (a) transactional reserve_inventory")
    try:
        reserve_inventory(client, PRODUCT, 1, "CUST-T", order_id="ORD-DUP")
    except DuplicateKeyError:
        print("  order insert failed -> whole transaction rolled back")
    s = db.inventory.find_one({"product_id": PRODUCT})["stock"]
    o = db.orders.count_documents({})
    print(f"  stock={s}, orders={o}")
    chk.check(s == s0 and o == o0, "transactional: stock restored, state consistent")

    print("\n  (b) non-transactional findAndModify")
    try:
        reserve_nontransactional(client, PRODUCT, 1, "CUST-N", order_id="ORD-DUP")
    except DuplicateKeyError:
        print("  order insert failed, but stock was ALREADY decremented!")
    s = db.inventory.find_one({"product_id": PRODUCT})["stock"]
    o = db.orders.count_documents({})
    print(f"  stock={s}, orders={o}")
    chk.check(s == s0 - 1 and o == o0,
              "non-transactional: stock lost 1 unit with NO order -> INCONSISTENT (expected demo)")

    rc = chk.summary("Lab 10.2 summary")
    client.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
