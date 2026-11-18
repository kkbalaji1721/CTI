"""Shared helpers for the Lab 9 scripts."""
import json
import os
import time

from pymongo import MongoClient

RS_URI = os.getenv(
    "REPLICA_SET_URI",
    "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0",
)
NODES = [n.strip() for n in os.getenv("MONGO_NODES", "mongo1,mongo2,mongo3").split(",")]
PORT = int(os.getenv("MONGO_PORT", "27017"))
RESULTS_DIR = os.getenv("RESULTS_DIR", "/results")


def banner(text, char="=", width=72):
    print()
    print(char * width)
    print(f"  {text}")
    print(char * width)
    print()


def save_json(name, data):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def load_json(name):
    path = os.path.join(RESULTS_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def direct_client(node, timeout_ms=1500):
    """Client that talks to ONE specific node only (no replica-set discovery)."""
    return MongoClient(
        f"mongodb://{node}:{PORT}/?directConnection=true",
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
        socketTimeoutMS=max(timeout_ms, 2500),
    )


def replica_set_members(client):
    """Return [{name, state, health}] from replSetGetStatus."""
    status = client.admin.command("replSetGetStatus")
    return [
        {"name": m["name"], "state": m["stateStr"], "health": m.get("health", 0)}
        for m in status["members"]
    ]


def healthy_data_members(members):
    return [m for m in members if m["health"] == 1 and m["state"] in ("PRIMARY", "SECONDARY")]


def wait_until(predicate, timeout_s, interval_s=1.0):
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(interval_s)
    return False
