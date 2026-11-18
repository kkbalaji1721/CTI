from pymongo import MongoClient
from pprint import pprint


MONGO_URI = "mongodb://localhost:27017/"


def get_client():
    return MongoClient(MONGO_URI)


def get_db(db_name="nosql_labs"):
    client = get_client()
    return client[db_name]


def reset_collection(db, collection_name):

    if collection_name in db.list_collection_names():
        db.drop_collection(collection_name)

    return db[collection_name]


def banner(title):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_json(data):
    pprint(data)