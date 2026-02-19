from retrieval.hybrid_retriever import HybridRetriever
from qa.academic_qa_engine import AcademicQAEngine
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore

embedder = OllamaEmbedder()
vector_store = ChromaVectorStore()
retriever = HybridRetriever(embedder, vector_store)

qa_engine = AcademicQAEngine(
    retriever=retriever,
    model_name="llama3.1"
)

response = qa_engine.ask(
    "What are the main enterprise benefits of Hyperledger Fabric?"
)

print(response["answer"])
print(response["sources"])
