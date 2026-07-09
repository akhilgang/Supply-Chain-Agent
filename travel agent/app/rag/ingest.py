import os
import asyncio
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureTextEmbedding

load_dotenv()

# Initialize Cosmos client
client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
print("✅ Using Cosmos DB connection key for ingestion")
db = client.create_database_if_not_exists(id=os.environ["COSMOS_DB"])
container = db.create_container_if_not_exists(
    id=os.environ["COSMOS_CONTAINER"],
    partition_key=PartitionKey(path=os.environ["COSMOS_PARTITION_KEY"]),
    indexing_policy={"vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}]}
)

# Initialize Semantic Kernel for embeddings
def create_embedding_kernel():
    kernel = Kernel()
    kernel.add_service(
        AzureTextEmbedding(
            deployment_name=os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"]
        )
    )
    return kernel

def embed_texts(texts):
    """
    Generate embeddings using Semantic Kernel.

    TODO: Implement embedding generation
    - Create kernel with create_embedding_kernel()
    - Get embedding service from kernel using get_service()
    - Loop through texts and call generate_embeddings() for each
    - Convert results to list format for JSON serialization
    """
    kernel = create_embedding_kernel()
    embedding_service = kernel.get_service(type=AzureTextEmbedding)

    embeddings = []
    for text in texts:
        # generate_embeddings is async; run it to completion in this sync context
        result = asyncio.run(embedding_service.generate_embeddings([text]))
        vector = result[0]
        if hasattr(vector, "tolist"):
            embeddings.append(vector.tolist())
        else:
            embeddings.append(list(vector))
    return embeddings

def upsert_snippet(doc_id, text, pk="cards"):
    """
    Upsert a document with its embedding into Cosmos DB.

    TODO: Implement document ingestion
    - Generate embedding using embed_texts()
    - Create document dict with id, pk, text, and embedding fields
    - Use container.upsert_item() to store in Cosmos DB
    """
    try:
        embedding = embed_texts([text])[0]
        document = {
            "id": doc_id,
            "pk": pk,
            "text": text,
            "embedding": embedding
        }
        container.upsert_item(document)
        print(f"✅ {doc_id} upserted with Semantic Kernel embeddings.")
    except Exception as e:
        print(f"❌ Failed to upsert {doc_id}: {e}")

if __name__ == "__main__":
    upsert_snippet("bankgold-1", "BankGold: 4x points on dining worldwide; no FX fees.")
    upsert_snippet("lounge-1", "Lounge access in CDG Terminal 2 with BankGold Premium.")
    upsert_snippet("bankgold-2", "BankGold Premium: Priority boarding, lounge access, concierge service.")
    upsert_snippet("dining-1", "4x points on dining worldwide with BankGold card.")
    print("✅ All snippets upserted with Semantic Kernel embeddings.")
