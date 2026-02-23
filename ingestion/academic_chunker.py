from typing import List, Dict
import re

class AcademicChunker:
    """
    Chunker académico consciente de sección.
    Optimizado para taxonomy extraction mode y Smart Overlap.
    """

    SECTION_SIZES = {
        "Abstract": 350,
        "Introduction": 600,
        "Background": 600,
        "Literature Review": 600,
        "Methodology": 550,
        "Results": 500,
        "Discussion": 550,
        "Conclusion": 450,
        "Future Work": 450,
        "Recommendations": 450
    }

    TAXONOMY_TRIGGERS = [
        "classify", "classified", "classification", "categorized", "taxonomy",
        "types of", "levels of", "dimensions of", "grouped into", "divided into",
        "framework consists", "framework includes", "can be divided into", "can be classified into"
    ]

    def __init__(
        self,
        default_chunk_size: int = 750,
        overlap: int = 60,
        min_chunk_size: int = 300
    ):
        self.default_chunk_size = default_chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _split_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        # Regex mejorada para respetar abreviaturas comunes en academia (e.g., et al., i.e.)
        sentences = re.split(r"(?<!e\.g)(?<!i\.e)(?<!et al)(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _contains_taxonomy_trigger(self, text: str) -> bool:
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in self.TAXONOMY_TRIGGERS)

    def _contains_structured_table(self, text: str) -> bool:
        return text.count("|") >= 2

    def chunk_sections(self, sections: List[Dict], metadata: Dict) -> List[Dict]:
        chunks = []
        chunk_global_id = 0

        for section_data in sections:
            section_name = section_data["section"]
            section_text = section_data["text"]

            if not section_text.strip() or section_name == "References":
                continue

            chunk_size = self.SECTION_SIZES.get(section_name, self.default_chunk_size)
            paragraphs = self._split_paragraphs(section_text)

            current_chunk = ""
            current_tokens = 0
            dynamic_chunk_size = chunk_size

            for paragraph in paragraphs:
                p_tokens = self._estimate_tokens(paragraph)

                # Si el párrafo es más grande que el límite, dividimos en oraciones
                units = self._split_sentences(paragraph) if p_tokens > dynamic_chunk_size else [paragraph]

                for unit in units:
                    taxonomy_detected = self._contains_taxonomy_trigger(unit)
                    dynamic_chunk_size = max(chunk_size, 1000) if taxonomy_detected else chunk_size
                    u_tokens = self._estimate_tokens(unit)

                    if current_tokens + u_tokens <= dynamic_chunk_size:
                        current_chunk += " " + unit
                        current_tokens += u_tokens
                    else:
                        # --- CIERRE DE CHUNK ACTUAL ---
                        if current_tokens >= self.min_chunk_size:
                            chunks.append(
                                self._build_chunk(section_name, current_chunk.strip(), metadata, chunk_global_id)
                            )
                            chunk_global_id += 1

                        # --- LÓGICA DE SMART OVERLAP (SENTENCE-BASED) ---
                        sentences_in_chunk = self._split_sentences(current_chunk)
                        
                        # Intentamos que el overlap sea la última oración completa
                        if len(sentences_in_chunk) >= 1:
                            overlap_text = sentences_in_chunk[-1]
                        else:
                            # Fallback: caracteres si no hay oraciones claras
                            overlap_chars = self.overlap * 4
                            overlap_text = current_chunk[-overlap_chars:]

                        current_chunk = overlap_text + " " + unit
                        current_tokens = self._estimate_tokens(current_chunk)

            # Guardar último fragmento del pilar
            if current_chunk.strip() and current_tokens >= self.min_chunk_size:
                chunks.append(
                    self._build_chunk(section_name, current_chunk.strip(), metadata, chunk_global_id)
                )
                chunk_global_id += 1

        return chunks

    def _build_chunk(self, section_name: str, text: str, metadata: Dict, chunk_id: int) -> Dict:
        has_taxonomy = self._contains_taxonomy_trigger(text)
        has_table = self._contains_structured_table(text)
        
        # Inyección de Contexto Jerárquico para mejorar el RAG
        context_header = f"[Source: {metadata.get('title', 'N/A')} | Section: {section_name}]\n"
        enriched_text = context_header + text

        return {
            "id": f"{metadata['doc_id']}_{chunk_id}",
            "doc_id": metadata["doc_id"],
            "title": metadata.get("title"),
            "authors": metadata.get("authors"),
            "year": int(metadata.get("year", 0)) if metadata.get("year") else None,
            "section": section_name,
            "chunk_id": chunk_id,
            "tokens": self._estimate_tokens(enriched_text),
            "has_taxonomy_pattern": has_taxonomy,
            "has_structured_table": has_table,
            "text": enriched_text
        }