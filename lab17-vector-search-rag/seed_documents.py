"""Seed the threat-intelligence sample documents and Atlas vector index."""

from dotenv import load_dotenv

from database import AtlasDatabase
from rag_pipeline import RAGPipeline


def main() -> None:
    load_dotenv()
    database = AtlasDatabase()
    try:
        pipeline = RAGPipeline(database)
        print(
            f"Inserted {len(pipeline._chunks)} chunks; created Atlas vectorSearch index "
            f"with {pipeline.embeddings.dimensions} dimensions."
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
