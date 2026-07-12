from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureTextEmbedding

load_dotenv()

# Lazy initialization of Cosmos client
_client = None
_container = None

def get_cosmos_client():
    global _client, _container
    if _client is None:
        try:
            _client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
            print("✅ Using Cosmos DB connection key")
            _container = _client.get_database_client(os.environ["COSMOS_DB"]).get_container_client(os.environ["COSMOS_CONTAINER"])
        except Exception as e:
            print(f"❌ Cosmos DB connection failed: {e}")
            _client = None
            _container = None
    return _client, _container

# Initialize Semantic Kernel for embeddings
def create_embedding_kernel():
    kernel = Kernel()
    try:
        kernel.add_service(
            AzureTextEmbedding(
                deployment_name=os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"],
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_KEY"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"]
            )
        )
    except Exception as e:
        print(f"❌ Failed to create embedding kernel: {e}")
        # Return None to trigger fallback
        return None
    return kernel

async def embed_texts(texts):
    """Generate embeddings using Semantic Kernel"""
    try:
        kernel = create_embedding_kernel()
        if kernel is None:
            raise Exception("Failed to create embedding kernel")
        
        embedding_service = kernel.get_service(type=AzureTextEmbedding)
        embeddings = []
        for text in texts:
            # generate_embeddings expects a list and returns a 2D array (n, dim);
            # take the first (and only) row so each embedding is a flat vector.
            result = await embedding_service.generate_embeddings([text])
            vector = result[0]
            if hasattr(vector, 'tolist'):
                embeddings.append(vector.tolist())
            else:
                embeddings.append(list(vector))
        return embeddings
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        raise Exception(f"Failed to generate embeddings: {e}")

async def retrieve(query: str, k: int = 5, partition_key: str = None):
    """Retrieve relevant documents using vector similarity search"""
    try:
        client, container = get_cosmos_client()
        if client is None or container is None:
            raise Exception("Cosmos DB not available")

        # Generate embedding for the query
        print(f"\n🔎 RAG retrieval for query: {query!r}")
        query_embedding = await embed_texts([query])
        query_vector = query_embedding[0] if query_embedding else []
        print(f"   ✅ Query embedding generated ({len(query_vector)} dimensions)")

        if not query_vector or not isinstance(query_vector, list):
            raise ValueError(f"Invalid embedding format: {type(query_vector)}")

        if len(query_vector) == 0:
            raise ValueError("Empty embedding vector")

        query_vector = [float(x) if not isinstance(x, (list, tuple)) else float(x[0]) for x in query_vector]

        if partition_key:
            sql = """
            SELECT TOP @k c.id, c.text, c.pk,
                   VectorDistance(c.embedding, @queryVector, false) as distance
            FROM c
            WHERE IS_DEFINED(c.embedding) AND IS_ARRAY(c.embedding) AND c.pk = @pk
            ORDER BY VectorDistance(c.embedding, @queryVector, false)
            """
            params = [
                {"name": "@k", "value": k},
                {"name": "@queryVector", "value": query_vector},
                {"name": "@pk", "value": partition_key}
            ]
        else:
            sql = """
            SELECT TOP @k c.id, c.text, c.pk,
                   VectorDistance(c.embedding, @queryVector, false) as distance
            FROM c
            WHERE IS_DEFINED(c.embedding) AND IS_ARRAY(c.embedding)
            ORDER BY VectorDistance(c.embedding, @queryVector, false)
            """
            params = [
                {"name": "@k", "value": k},
                {"name": "@queryVector", "value": query_vector}
            ]

        # Execute the vector similarity search against Cosmos DB
        raw_results = list(container.query_items(
            query=sql,
            parameters=params,
            enable_cross_partition_query=True
        ))

        # Normalize results: convert VectorDistance to a similarity score
        results = []
        print(f"   ✅ VectorDistance query executed against Cosmos DB — {len(raw_results)} result(s):")
        for item in raw_results:
            distance = item.get("distance", 1.0)
            score = 1.0 - float(distance)  # cosine distance -> similarity
            content = item.get("text", "")
            print(f"   • id={item.get('id')} | VectorDistance={distance:.4f} | similarity={score:.4f}")
            print(f"       content: {content[:90]}")
            results.append({
                "id": item.get("id"),
                "content": content,
                "pk": item.get("pk"),
                "distance": distance,
                "score": score,
                "metadata": {"id": item.get("id"), "pk": item.get("pk")}
            })

        return results
    except Exception as e:
        print(f"❌ RAG retrieval failed: {e}")
        return []
