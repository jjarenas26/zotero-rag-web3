import requests
from typing import List, Dict, Any
import logging
import time


class OllamaEmbedder:
    """
    Wrapper profesional para generar embeddings usando Ollama.
    Diseñado para integrarse con pipelines académicos + ChromaDB.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        batch_size: int = 16
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = batch_size

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    # ===============================
    # PUBLIC API
    # ===============================

    def embed_text(self, text: str) -> List[float]:
        """
        Genera embedding para un solo texto.
        """
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            },
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama embedding error: {response.status_code} - {response.text}"
            )

        return response.json()["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings en batch (con manejo interno de sub-batches).
        """
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            self.logger.info(f"Embedding batch {i} - {i + len(batch)}")

            batch_embeddings = []
            for text in batch:
                emb = self.embed_text(text)
                batch_embeddings.append(emb)

            all_embeddings.extend(batch_embeddings)

            # pequeña pausa para no saturar Ollama
            time.sleep(0.2)

        return all_embeddings

    # ===============================
    # HEALTH CHECK
    # ===============================

    def health_check(self) -> bool:
        """
        Verifica que Ollama esté activo.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
