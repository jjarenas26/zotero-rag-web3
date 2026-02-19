import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import uuid
import logging


class ChromaVectorStore:
    """
    Vector Store académico basado en ChromaDB.
    Diseñado para investigación estructurada + metadata rica.
    """

    def __init__(
        self,
        collection_name: str = "academic_research",
        persist_directory: str = "./chroma_db"
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    # ==========================================
    # INSERT DOCUMENTS
    # ==========================================

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ):
        """
        Inserta documentos con embeddings y metadata rica.
        """

        if not (len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError("texts, embeddings y metadatas deben tener el mismo tamaño")

        ids = [str(uuid.uuid4()) for _ in texts]
        for i, m in enumerate(metadatas):
            for k, v in m.items():
                if not isinstance(v, (str, int, float, bool)):
                    print("❌ INVALID METADATA")
                    print("Chunk index:", i)
                    print("Key:", k)
                    print("Type:", type(v))
                    print("Value:", v)
                    raise ValueError("Invalid metadata detected")

        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        self.logger.info(f"Inserted {len(texts)} documents into ChromaDB")

    # ==========================================
    # QUERY
    # ==========================================

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where_filter: Dict[str, Any] = None
    ):
        """
        Query semántico con filtros estructurales opcionales.
        """

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )

        return results

    # ==========================================
    # COUNT
    # ==========================================

    def count(self) -> int:
        return self.collection.count()

    # ==========================================
    # DELETE COLLECTION
    # ==========================================

    def delete_collection(self):
        self.client.delete_collection(self.collection_name)
        self.logger.info("Collection deleted")
