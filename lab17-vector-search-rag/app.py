"""Interactive command-line threat-intelligence RAG demonstration."""

import os

from dotenv import load_dotenv

from database import AtlasDatabase
from rag_pipeline import RAGPipeline


def main() -> None:
    load_dotenv()
    database = None
    uri = os.getenv("MONGODB_ATLAS_URI") or os.getenv("MONGODB_URI")
    if uri:
        database = AtlasDatabase(uri)
        mode = "MongoDB Atlas $vectorSearch"
    else:
        mode = "LOCAL DEMO: exact cosine search; Atlas $vectorSearch is not running"
    pipeline = RAGPipeline(database)
    print(f"Lab 17 RAG — {mode}")
    print(f"Embeddings: {pipeline.embeddings.provider} ({pipeline.embeddings.dimensions} dimensions)")
    print("Ask about the sample threat reports. Enter 'quit' to stop.")
    if not os.getenv("OPENAI_API_KEY"):
        print("Offline mode: ask 'What did I ask you previously?' to test conversation memory.")
    try:
        while True:
            query = input("\nYou: ").strip()
            if query.lower() in {"quit", "exit"}:
                break
            if not query:
                continue
            answer, results = pipeline.chat(query)
            print(f"\nAssistant: {answer}")
            print("Sources: " + ", ".join(sorted({row["source"] for row in results})))
    finally:
        if database:
            database.close()


if __name__ == "__main__":
    main()
