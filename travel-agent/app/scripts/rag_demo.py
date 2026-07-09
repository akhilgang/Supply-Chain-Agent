# app/scripts/rag_demo.py
# Demo: query embedding generation + Cosmos DB VectorDistance similarity search.
# Run:  python -m app.scripts.rag_demo
import asyncio
from dotenv import load_dotenv
from app.rag.retriever import retrieve

load_dotenv()


async def main():
    query = "BankGold dining rewards and airport lounge access"
    print("=" * 60)
    print("RAG RETRIEVAL DEMO (Cosmos DB VectorDistance)")
    print("=" * 60)
    results = await retrieve(query, k=4, partition_key="cards")
    print(f"\n📊 Retrieved {len(results)} documents with similarity scores.")


if __name__ == "__main__":
    asyncio.run(main())
