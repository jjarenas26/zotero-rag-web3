from retrieval.backup.hybrid_retriever import HybridRetriever
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore


EVALUATION_QUERIES = [
    "blockchain interoperability mechanisms",
    "consensus algorithm performance comparison",
    "smart contract security vulnerabilities",
    "zero knowledge proof scalability limitations",
    "decentralized governance models in blockchain"
]

TOP_K = 5


embedder = OllamaEmbedder()
vector_store = ChromaVectorStore()
retriever = HybridRetriever(embedder, vector_store)


def evaluate_query(query, k=5):
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    #results = retriever.query(query_text=query, n_results=k)
    # Primero generar embedding
    query_embedding = retriever.embedder.embed_text(query)

    # Usar search, que devuelve final_score completo
    results = retriever.search(query_embedding=query_embedding, top_k=k)

    for i, result in enumerate(results):
        print(f"\nRank #{i+1}")
        print("-" * 40)

        #metadata = result["metadata"]
        text = result["text"]

        print("Title:", result["title"])
        print("Section:", result["section"])
        print("Year:", result["year"])

        print("Semantic Score:", round(result["semantic_score"], 4))
        
        print("Structural Score:", round(result["structural_score"], 4))
        print("Recency Score:", round(result["recency_score"], 4))
        print("Diversity Score:", round(result["diversity_score"], 4))

        print("Final Score:", round(result["final_score"], 4))

        print("\nSnippet:")
        print(text[:500])
        print("\n")


if __name__ == "__main__":
    for query in EVALUATION_QUERIES:
        evaluate_query(query, TOP_K)
