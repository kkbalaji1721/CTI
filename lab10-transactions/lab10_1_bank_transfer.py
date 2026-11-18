#!/usr/bin/env python3
"""
Lab 10.1 - Bank transfer using a multi-document transaction.

 1. accounts collection with 2 accounts (+ version field)
 2. transfer() = session + transaction: debit, credit, history insert
 3. insufficient funds -> rollback (neither balance changes)
 Activity: retry with exponential backoff on TransientTransactionError
"""
import sys
import threading
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from common import (DB_NAME, Checker, RetriesExhausted, Stats, banner,
                    get_client, run_transaction)


class InsufficientFunds(Exception):
    pass


class AccountNotFound(Exception):
    pass


def setup(db):
    db.accounts.drop()
    db.transfers.drop()
    db.create_collection("accounts")
    db.create_collection("transfers")      # collections must exist before a transaction
    db.accounts.create_index("account_id", unique=True)
    db.accounts.insert_many([
        {"account_id": "ACC-A", "owner": "Alice", "balance": 1000, "version": 1},
        {"account_id": "ACC-B", "owner": "Bob",   "balance": 500,  "version": 1},
    ])


def balances(db):
    return {d["account_id"]: d["balance"] for d in db.accounts.find()}


def show(db, title="Current state"):
    print(f"  {title}:")
    for d in db.accounts.find({}, {"_id": 0}).sort("account_id", 1):
        print("   ", d)
    print(f"    transfers history documents: {db.transfers.count_documents({})}")


def transfer(client, src, dst, amount, simulate_failure=False,
             max_retries=5, stats=None, verbose=False):
    """Move `amount` from src to dst atomically."""
    db = client[DB_NAME]

    def body(session):
        source = db.accounts.find_one({"account_id": src}, session=session)
        target = db.accounts.find_one({"account_id": dst}, session=session)
        if source is None or target is None:
            raise AccountNotFound(f"{src} or {dst} does not exist")
        if source["balance"] < amount:                      # explicit balance check
            raise InsufficientFunds(
                f"{src} has {source['balance']}, needs {amount}")

        # guard filter: matches 0 documents if funds are insufficient
        debit = db.accounts.update_one(
            {"account_id": src, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount, "version": 1}},
            session=session)
        if debit.modified_count != 1:
            raise InsufficientFunds(f"debit of {amount} from {src} matched no document")

        db.accounts.update_one(
            {"account_id": dst},
            {"$inc": {"balance": amount, "version": 1}},
            session=session)

        if simulate_failure:                                # crash in the middle
            raise RuntimeError("Simulated crash AFTER debit+credit, BEFORE commit")

        transfer_id = str(uuid.uuid4())
        db.transfers.insert_one({
            "transfer_id": transfer_id, "from": src, "to": dst, "amount": amount,
            "status": "completed", "at": datetime.now(timezone.utc)}, session=session)
        return transfer_id

    return run_transaction(client, body, max_retries=max_retries, stats=stats,
                           verbose=verbose, label=f"{src}->{dst}")


def concurrent_transfers(client, n, amount, max_retries, verbose=False):
    """n simultaneous transfers A->B (all hit the same 2 documents)."""
    stats = Stats()
    barrier = threading.Barrier(n)

    def worker(_):
        barrier.wait()  # release all threads at the same instant
        try:
            transfer(client, "ACC-A", "ACC-B", amount, max_retries=max_retries,
                     stats=stats, verbose=verbose)
            return "success"
        except RetriesExhausted:
            return "failed (write conflict, retries exhausted)"
        except Exception as e:
            return f"failed ({type(e).__name__})"

    with ThreadPoolExecutor(max_workers=n) as pool:
        outcomes = Counter(pool.map(worker, range(n)))
    return outcomes, stats.retries


def main():
    client = get_client()
    db = client[DB_NAME]
    chk = Checker()

    banner("STEP 1 - Create accounts collection and insert two accounts")
    setup(db)
    show(db, "Initial state")

    banner("STEP 2 - Successful transfer: ACC-A -> ACC-B, amount 200")
    tid = transfer(client, "ACC-A", "ACC-B", 200)
    print(f"  committed transfer_id={tid}")
    show(db, "After transfer")
    b = balances(db)
    chk.check(b == {"ACC-A": 800, "ACC-B": 700}, "balances are A=800, B=700")
    chk.check(db.transfers.count_documents({}) == 1, "one history document written")

    banner("STEP 3a - Insufficient funds: transfer 5000 from ACC-A (balance 800)")
    before = balances(db)
    try:
        transfer(client, "ACC-A", "ACC-B", 5000)
        chk.check(False, "transfer should have been rejected")
    except InsufficientFunds as e:
        print(f"  InsufficientFunds raised -> transaction aborted: {e}")
    show(db, "After failed transfer")
    chk.check(balances(db) == before, "NEITHER balance changed (rollback)")
    chk.check(db.transfers.count_documents({}) == 1, "no history document added")

    banner("STEP 3b - Failure AFTER debit and credit (proves atomic rollback)")
    print("  Inside the transaction the debit and credit were already applied;")
    print("  we now raise an error before commit...")
    before = balances(db)
    try:
        transfer(client, "ACC-A", "ACC-B", 100, simulate_failure=True)
    except RuntimeError as e:
        print(f"  RuntimeError: {e}")
    show(db, "After aborted transaction")
    chk.check(balances(db) == before, "debit AND credit were both rolled back")
    chk.check(db.transfers.count_documents({}) == 1, "no history document added")

    banner("ACTIVITY 10.1 - Retry with exponential backoff (TransientTransactionError)")
    n, amount = 10, 10
    print(f"\n  (a) {n} concurrent transfers of {amount} WITHOUT retry (max_retries=0)")
    a0, b0 = balances(db)["ACC-A"], balances(db)["ACC-B"]
    outcomes, retries = concurrent_transfers(client, n, amount, max_retries=0)
    print("  outcomes:", dict(outcomes))
    ok = outcomes["success"]
    bal = balances(db)
    chk.check(bal["ACC-A"] + bal["ACC-B"] == a0 + b0, "money conserved (A+B total unchanged)")
    chk.check(bal["ACC-A"] == a0 - ok * amount, f"only the {ok} successful transfers were applied")

    print(f"\n  (b) {n} concurrent transfers of {amount} WITH retry (sleep 0.1 * 2**attempt)")
    a0, b0 = balances(db)["ACC-A"], balances(db)["ACC-B"]
    outcomes, retries = concurrent_transfers(client, n, amount, max_retries=10, verbose=True)
    print("  outcomes:", dict(outcomes), "| total retries:", retries)
    ok = outcomes["success"]
    bal = balances(db)
    chk.check(ok == n, f"all {n} transfers eventually succeeded thanks to retries")
    chk.check(bal["ACC-A"] == a0 - n * amount and bal["ACC-B"] == b0 + n * amount,
              "final balances are exactly correct")
    show(db, "Final state")

    rc = chk.summary("Lab 10.1 summary")
    client.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
