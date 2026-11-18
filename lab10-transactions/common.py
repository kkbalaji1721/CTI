"""Shared helpers for Lab 10 (transactions, retries, checks)."""
import os
import random
import threading
import time

from pymongo import MongoClient, WriteConcern
from pymongo.read_concern import ReadConcern
from pymongo.errors import PyMongoError

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0")
DB_NAME = os.environ.get("LAB_DB", "lab10")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/app/results")


def get_client(max_pool=100):
    """Connect to the replica set (transactions REQUIRE a replica set)."""
    client = MongoClient(MONGO_URI, maxPoolSize=max_pool, serverSelectionTimeoutMS=15000)
    hello = client.admin.command("hello")
    if not hello.get("setName"):
        raise SystemExit("ERROR: MongoDB is not running as a replica set - transactions need one.")
    return client


def banner(text):
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


class Checker:
    """Tiny assertion helper that prints PASS/FAIL instead of crashing."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, cond, msg):
        if cond:
            self.passed += 1
            print(f"  [PASS] {msg}")
        else:
            self.failed += 1
            print(f"  [FAIL] {msg}")
        return cond

    def summary(self, title):
        print(f"\n{title}: {self.passed} passed, {self.failed} failed")
        return 1 if self.failed else 0


class Stats:
    """Thread-safe retry counter."""

    def __init__(self):
        self._lock = threading.Lock()
        self.retries = 0

    def add_retry(self):
        with self._lock:
            self.retries += 1


class RetriesExhausted(Exception):
    """Raised when a transaction keeps failing with TransientTransactionError."""

    def __init__(self, attempts, last_error):
        super().__init__(f"gave up after {attempts} attempt(s): {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def _safe_abort(session):
    try:
        session.abort_transaction()
    except Exception:
        pass


def run_transaction(client, body, max_retries=5, base_delay=0.1, max_delay=1.0,
                    stats=None, verbose=False, label="txn"):
    """
    Run body(session) inside a multi-document transaction.

    * TransientTransactionError (e.g. WriteConflict, code 112) -> abort, sleep
      base_delay * 2**attempt (+ jitter) and retry the WHOLE transaction.
    * UnknownTransactionCommitResult -> retry only the commit.
    * Any other exception (InsufficientFunds, OutOfStock, DuplicateKey...) ->
      transaction is aborted (rolled back) and the exception is re-raised.
    """
    attempt = 0
    while True:
        last_error = None
        with client.start_session() as session:
            session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
            )
            try:
                result = body(session)
            except PyMongoError as exc:
                _safe_abort(session)
                if exc.has_error_label("TransientTransactionError"):
                    last_error = exc
                else:
                    raise
            except BaseException:
                _safe_abort(session)  # rollback on ANY application error
                raise
            else:
                commit_tries = 0
                while True:
                    try:
                        session.commit_transaction()
                        return result
                    except PyMongoError as exc:
                        if exc.has_error_label("UnknownTransactionCommitResult") and commit_tries < 3:
                            commit_tries += 1
                            continue
                        if exc.has_error_label("TransientTransactionError"):
                            last_error = exc
                            break
                        raise

        # ---- only reached for transient errors ----
        if attempt >= max_retries:
            raise RetriesExhausted(attempt + 1, last_error)
        delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, base_delay / 2)
        if stats is not None:
            stats.add_retry()
        if verbose:
            reason = getattr(last_error, "details", None) or last_error
            code = reason.get("codeName") if isinstance(reason, dict) else type(last_error).__name__
            print(f"    [retry] {label}: TransientTransactionError ({code}) "
                  f"attempt {attempt + 1} -> sleeping {delay:.3f}s")
        time.sleep(delay)
        attempt += 1
