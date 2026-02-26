import os
import json
from typing import List, Dict

import re
import unicodedata

from ingestion.section_splitter import SectionSplitter
from ingestion.academic_chunker import AcademicChunker
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore
from ingestion.pdf_loader import extract_clean_text
from ingestion.academic_extractor import AcademicIntelligenceExtractor



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
        self.intel_extractor = AcademicIntelligenceExtractor()
        self.vector_store = ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=persist_directory
        )

    # ============================================================
    # PUBLIC METHODS
    # ============================================================
    def ingest_paper(self, pdf_path: str, metadata_path: str):
        print(f"🧐 Ingesting: {os.path.basename(pdf_path)}")
        
        try:
            metadata = self._load_metadata(metadata_path)
            metadata = self._prepare_metadata(metadata)
            raw_text = extract_clean_text(pdf_path)
            
            # 1. Segmentación Estructural inicial
            sections = self.section_splitter.split(raw_text)

            final_texts = []
            final_metadatas = []
            final_ids = []

            # 2. Procesamiento Inteligente SECCIÓN POR SECCIÓN
            for section in sections:
                name = section["section"]
                content = section["text"]
                print(f"   🧠 Processingfrom {name}...")

                # A. Refinamiento con Llama 3.1 (Limpia ruidos de PDF y une palabras)
                #clean_text = self.refiner.refine_section(name, content)
                clean_text=content

                # B. Extracción de Inteligencia (Solo secciones clave para optimizar)
                intel_data = {}
                if name.lower() in ["introduction", "methodology", "results", "discussion", "conclusion"]:
                    print(f"   🧠 Extracting intelligence from {name}...")
                    intel_data = self.intel_extractor.extract_intelligence(name, clean_text)

                # C. Chunking de la sección limpia
                # Pasamos la inteligencia detectada para que se adjunte a los chunks
                section_chunks = self.chunker.chunk_single_section(
                    section_name=name, 
                    text=clean_text, 
                    doc_metadata=metadata,
                    intel_data=intel_data # Pasamos TRL, Contradicciones, etc.
                )

                for i, chunk in enumerate(section_chunks):
                    final_texts.append(chunk["text"])
                    final_metadatas.append(self._build_vector_metadata(chunk))
                    final_ids.append(f"{metadata['doc_id']}_{name}_ch{i}")

            # 3. Generación de Embeddings y Guardado
            if final_texts:
                embeddings = self.embedder.embed_batch(final_texts)
                self.vector_store.add_documents(
                    ids=final_ids,
                    texts=final_texts,
                    embeddings=embeddings,
                    metadatas=final_metadatas
                )
                print(f"✅ Ingested {len(final_texts)} intelligent chunks from {metadata.get('doc_id')}")
            
        except Exception as e:
            print(f"❌ Error ingesting {pdf_path}: {str(e)}")
    
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

    def _build_vector_metadata(self, chunk: Dict) -> Dict:
        """
        Construye la metadata enriquecida para ChromaDB.
        """
        structural_weight = self._compute_structural_weight(chunk["section"])
        intel = chunk.get("intel_data", {})

        metadata = {
            "doc_id": chunk.get("doc_id", ""),
            "title": chunk.get("title", ""),
            "authors": chunk.get("authors", ""),
            "year": chunk.get("year", 0),
            "section": chunk.get("section", ""),
            "structural_weight": structural_weight,
            
            # 🚀 METADATA ESTRATÉGICA (Inyectada desde el Extractor)
            "trl": intel.get("trl_analysis", {}).get("level", 0),
            "trl_justification": intel.get("trl_analysis", {}).get("justification", ""),
            "contradictions": "|".join(intel.get("contradictions", [])) if intel.get("contradictions") else "",
            "entities": str(intel.get("entities", []))
        }

        # Blindaje contra None
        for k, v in metadata.items():
            if v is None:
                metadata[k] = "" if k != "year" else 0

        return metadata

    def _clean_academic_text(self, text: str) -> str:
        """
        Limpieza profunda para textos extraídos de PDFs académicos.
        """
        # 1. Normalización Unicode (Arregla ligaduras y caracteres extraños)
        text = unicodedata.normalize("NFKC", text)

        # 2. Unir palabras cortadas por saltos de línea (hyphenation)
        # Ejemplo: "block-\nchain" -> "blockchain"
        text = re.sub(r"(\w+)-\n\s*(\w+)", r"\1\2", text)

        # 3. Eliminar saltos de línea internos pero preservar párrafos
        # Reemplazamos un solo salto de línea por espacio
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # 4. Eliminar ruido común de PDFs (caracteres no imprimibles)
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        # 5. Colapsar espacios múltiples
        text = re.sub(r"\s+", " ", text)

        return text.strip()

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
