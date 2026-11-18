import os
_client = None
def db():
    """MongoDB handle. USE_MOCK=1 -> in-memory mongomock seeded with sample data (no server needed)."""
    global _client
    name = os.getenv("MONGO_DB", "cti")
    if _client is None:
        if os.getenv("USE_MOCK") == "1":
            import mongomock
            from .seed import seed
            _client = mongomock.MongoClient(); seed(_client[name])
            from .merge import import_kev, load_fragments, merge_fragments
            import_kev(_client[name]); load_fragments(_client[name]); merge_fragments(_client[name])
        else:
            from pymongo import MongoClient
            _client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    return _client[name]
