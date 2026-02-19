import os
import json
from typing import List, Dict

from ingestion.section_splitter import SectionSplitter
from ingestion.academic_chunker import AcademicChunker
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore

from pypdf import PdfReader


class AcademicIngestionPipeline:
    """
    Orquestador principal del sistema de investigación estructurada.
    Coordina extracción, chunking, embedding y almacenamiento.
    """

    def __init__(
        self,
        collection_name: str = "academic_research",
        persist_directory: str = "./chroma_db"
    ):
        self.section_splitter = SectionSplitter()
        self.chunker = AcademicChunker()
        self.embedder = OllamaEmbedder()
        self.vector_store = ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=persist_directory
        )

    # ============================================================
    # PUBLIC METHODS
    # ============================================================

    def ingest_paper(self, pdf_path: str, metadata_path: str):
        """
        Ingesta completa de un paper individual.
        """

        metadata = self._load_metadata(metadata_path)
        metadata = self._prepare_metadata(metadata)

        raw_text = self._extract_pdf_text(pdf_path)

        sections = self.section_splitter.split(raw_text)
        chunks = self.chunker.chunk_sections(sections, metadata)

        if not chunks:
            print(f"No chunks generated for {pdf_path}")
            return

        texts = []
        metadatas = []

        for chunk in chunks:
            texts.append(chunk["text"])
            metadatas.append(self._build_vector_metadata(chunk))

        embeddings = self.embedder.embed_batch(texts)

        self.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        print(f"Ingested {len(chunks)} chunks from {metadata.get('doc_id')}")

    def ingest_collection(self, folder_path: str):
        """
        Ingesta automática de una carpeta con PDFs y JSONs emparejados.
        """

        files = os.listdir(folder_path + "/pdfs")
        pdf_files = [f for f in files if f.endswith(".pdf")]

        for pdf_file in pdf_files:
            base_name = os.path.splitext(pdf_file)[0]
            pdf_path = os.path.join(folder_path + "/pdfs", pdf_file)
            json_path = os.path.join(folder_path + "/metadata", f"{base_name}.json")

            if not os.path.exists(json_path):
                print(f"Metadata not found for {pdf_file}, skipping.")
                continue

            self.ingest_paper(pdf_path, json_path)

    # ============================================================
    # INTERNAL METHODS
    # ============================================================

    def _prepare_metadata(self, metadata: dict):
        """
        Limpieza y normalización completa del metadata original.
        Garantiza compatibilidad con Chroma.
        """

        clean = {}

        for k, v in metadata.items():

            # Normalizar listas
            if isinstance(v, list):
                clean[k] = ", ".join([str(x) for x in v])

            # Convertir None
            elif v is None:
                clean[k] = ""

            # Year como int seguro
            elif k == "year":
                try:
                    clean[k] = int(v)
                except:
                    clean[k] = 0

            # Tipos permitidos
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v

            # Cualquier otro tipo
            else:
                clean[k] = str(v)

        # Asegurar campos clave
        if "year" not in clean or clean["year"] == "":
            clean["year"] = 0

        return clean

    def _load_metadata(self, metadata_path: str) -> Dict:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # doc_id obligatorio
        metadata["doc_id"] = metadata.get("zotero_key", "")

        return metadata

    def _extract_pdf_text(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""
            text += "\n"

        return text

    def _build_vector_metadata(self, chunk: Dict) -> Dict:
        """
        Construye metadata limpia para Chroma.
        Solo campos necesarios para filtrado y boost.
        """

        structural_weight = self._compute_structural_weight(chunk["section"])

        metadata = {
            "doc_id": chunk.get("doc_id", ""),
            "title": chunk.get("title", ""),
            "authors": chunk.get("authors", ""),
            "year": chunk.get("year", 0),
            "journal": chunk.get("journal", ""),
            "doi": chunk.get("doi", ""),
            "collection": chunk.get("collection", ""),
            "research_question": chunk.get("research_question", ""),
            "section": chunk.get("section", ""),
            "chunk_id": chunk.get("chunk_id", ""),
            "structural_weight": structural_weight,

            # 🔬 NUEVO: taxonomy mode metadata
            "has_taxonomy_pattern": bool(chunk.get("has_taxonomy_pattern", False)),
            "has_structured_table": bool(chunk.get("has_structured_table", False))
        }

        # 🔒 Blindaje final contra None
        for k, v in metadata.items():
            if v is None:
                metadata[k] = "" if k != "year" else 0

        return metadata

    # ============================================================
    # STRUCTURAL BOOST BASE
    # ============================================================

    def _compute_structural_weight(self, section: str) -> float:
        """
        Peso base para futura estrategia de boost estructural.
        """

        weights = {
            "Abstract": 1.4,
            "Introduction": 1.2,
            "Methodology": 1.3,
            "Results": 1.3,
            "Discussion": 1.2,
            "Conclusion": 1.2,
            "References": 0.8
        }

        return weights.get(section, 1.0)
