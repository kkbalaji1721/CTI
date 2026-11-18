import os
from pymongo import MongoClient


def get_db(db_name="nosql_labs"):
    """Connect to local MongoDB and return the database object."""
    host = os.getenv("MONGO_HOST", "localhost")
    port = int(os.getenv("MONGO_PORT", "27017"))
    client = MongoClient(host, port, serverSelectionTimeoutMS=5000)
    return client[db_name]


def reset_collection(db_name, collection_name):
    """Drop and recreate the target collection."""
    db = get_db(db_name)
    if collection_name in db.list_collection_names():
        db[collection_name].drop()
    return db[collection_name]


def banner(title):
    """Print a simple section banner."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
