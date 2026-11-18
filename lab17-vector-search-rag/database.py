"""MongoDB Atlas persistence and Atlas Vector Search helpers."""

import os
from typing import Any

from pymongo import MongoClient


class AtlasDatabase:
    def __init__(self, uri: str | None = None, database_name: str | None = None) -> None:
        self.uri = uri or os.getenv("MONGODB_ATLAS_URI") or os.getenv("MONGODB_URI")
        if not self.uri:
            raise ValueError("Set MONGODB_ATLAS_URI to connect to MongoDB Atlas.")
        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=7000)
        self.client.admin.command("ping")
        self.db = self.client[database_name or os.getenv("MONGODB_DATABASE", "lab17")]

    def ingest_chunks(self, chunks: list[dict[str, Any]], dimensions: int) -> None:
        collection = self.db["rag_documents"]
        for chunk in chunks:
            collection.replace_one(
                {"_id": f"{chunk['source']}:{chunk['chunk_index']}"},
                {**chunk, "_id": f"{chunk['source']}:{chunk['chunk_index']}"},
                upsert=True,
            )
        definition = {
            "fields": [
                {"type": "vector", "path": "embedding", "numDimensions": dimensions, "similarity": "cosine"}
            ]
        }
        existing = next(
            (row for row in collection.list_search_indexes() if row.get("name") == "rag_vector_index"),
            None,
        )
        if existing:
            indexed_fields = existing.get("latestDefinition", existing.get("definition", {})).get("fields", [])
            vector_field = next((field for field in indexed_fields if field.get("path") == "embedding"), {})
            if vector_field.get("numDimensions") != dimensions:
                collection.update_search_index("rag_vector_index", definition)
        else:
            collection.create_search_index(
                {"name": "rag_vector_index", "type": "vectorSearch", "definition": definition}
            )

    def vector_search(self, vector: list[float], limit: int = 3) -> list[dict[str, Any]]:
        return list(
            self.db["rag_documents"].aggregate(
                [
                    {
                        "$vectorSearch": {
                            "index": "rag_vector_index",
                            "path": "embedding",
                            "queryVector": vector,
                            "numCandidates": max(30, limit * 10),
                            "limit": limit,
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "text": 1,
                            "source": 1,
                            "chunk_index": 1,
                            "score": {"$meta": "vectorSearchScore"},
                        }
                    },
                ]
            )
        )

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        self.db["conversations"].update_one(
            {"_id": conversation_id},
            {"$push": {"messages": {"$each": [{"role": role, "content": content}], "$slice": -100}}},
            upsert=True,
        )

    def recent_messages(self, conversation_id: str, limit: int = 5) -> list[dict[str, str]]:
        document = self.db["conversations"].find_one({"_id": conversation_id}, {"messages": 1})
        return (document or {}).get("messages", [])[-limit:]

    def close(self) -> None:
        self.client.close()
