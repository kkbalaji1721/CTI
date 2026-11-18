"""
MongoDB Connection Utilities
23CSE528: NoSQL DBs using MongoDB
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


# MongoDB connection URL
MONGO_URI = "mongodb://localhost:27017"


def get_db(db_name="nosql_labs"):
    """
    Connect to MongoDB and return the requested database.
    """

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

        # Check whether MongoDB is running
        client.admin.command("ping")

        print("[OK] Connected to MongoDB")

        return client[db_name]

    except ConnectionFailure as e:
        print("[ERROR] Could not connect to MongoDB.")
        print("Make sure MongoDB is running.")
        print(f"Details: {e}")
        raise


def reset_collection(db_name, collection_name):
    """
    Delete an existing collection and create a fresh one.
    """

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    try:
        # Check MongoDB connection
        client.admin.command("ping")

        db = client[db_name]

        # Delete existing collection if it exists
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
            print(f"[OK] Reset collection: {collection_name}")

        # Return the newly created collection
        return db[collection_name]

    except ConnectionFailure as e:
        print("[ERROR] Could not connect to MongoDB.")
        print("Make sure MongoDB is running.")
        print(f"Details: {e}")
        raise


def banner(message):
    """
    Print a formatted banner message.
    """

    line = "=" * 70

    print()
    print(line)
    print(message)
    print(line)
    print()
import json


def print_json(data):
    """
    Print Python data in readable JSON format.
    """
    print(json.dumps(data, indent=2, default=str))