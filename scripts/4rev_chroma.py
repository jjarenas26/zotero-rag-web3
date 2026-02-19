from vectorstore.chroma_vector_store import ChromaVectorStore

vs = ChromaVectorStore(
    collection_name="academic_research",
    persist_directory="./chroma_db"
)

print("Total documentos indexados:", vs.collection.count())