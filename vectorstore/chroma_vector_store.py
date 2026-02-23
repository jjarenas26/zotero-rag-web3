import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
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
    # INSERT / UPDATE DOCUMENTS
    # ==========================================

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None  # ✨ Ahora acepta IDs externos
    ):
        """
        Inserta o actualiza documentos con embeddings y metadata rica.
        """

        if not (len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError("texts, embeddings y metadatas deben tener el mismo tamaño")

        # ✨ Si no se pasan IDs, generamos UUIDs. Si se pasan, los usamos.
        final_ids = ids if ids is not None else [str(uuid.uuid4()) for _ in texts]

        # Validación de tipos de metadata para evitar errores en Chroma
        for i, m in enumerate(metadatas):
            for k, v in m.items():
                if not isinstance(v, (str, int, float, bool)) and v is not None:
                    self.logger.error(f"❌ INVALID METADATA at index {i} | Key: {k} | Type: {type(v)}")
                    raise ValueError(f"ChromaDB only supports str, int, float, bool. Got {type(v)} for key '{k}'")

        # ✨ Usamos UPSERT en lugar de ADD para permitir actualizaciones por ID
        self.collection.upsert(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=final_ids
        )

        self.logger.info(f"Successfully upserted {len(texts)} documents into '{self.collection_name}'")

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

    def count(self) -> int:
        return self.collection.count()

    def delete_collection(self):
        self.client.delete_collection(self.collection_name)
        self.logger.info(f"Collection '{self.collection_name}' deleted")