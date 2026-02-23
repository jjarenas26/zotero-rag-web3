import re
import unicodedata
from typing import List, Dict

class SectionSplitter:
    def __init__(self):
        self.section_keywords = {
            "abstract": "Abstract",
            "introduction": "Introduction",
            "literature review": "Literature Review",
            "literature review": "Review of the Literature",
            "methodology": "Methodology",
            "results": "Results",
            "discussion": "Discussion",
            "conclusion": "Conclusion",
            "references": "References"
        }

    def _clean_academic_text(self, text: str) -> str:
        """
        Limpia el texto de una sección antes de guardarlo.
        """
        # 1. Normalización Unicode
        text = unicodedata.normalize("NFKC", text)

        # 2. Unir palabras cortadas (hyphenation)
        text = re.sub(r"(\w+)-\n\s*(\w+)", r"\1\2", text)

        # 3. Convertir saltos de línea simples en espacios (preserva el flujo)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # 4. Eliminar caracteres no imprimibles
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        # 5. Colapsar espacios múltiples
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _is_garbage_line(self, line: str) -> bool:
        l = line.strip()
        patterns = [
            r"^\d+\s+[A-Z].*?\bet al\b", 
            r"Procedia Computer Science",
            r"ScienceDirect",
            r"Available online",
            r"^\d+$",
            r"©\s*20\d{2}"
        ]
        return any(re.search(p, l, re.IGNORECASE) for p in patterns)

    def _detect_header(self, line: str) -> str | None:
        raw = line.strip()
        clean_line = re.sub(r"^(\d+\.?\d*|[ivxlcdm]+)\.?\s*", "", raw, flags=re.I).lower()
        for kw, canonical in self.section_keywords.items():
            if clean_line == kw:
                return canonical
        return None

    def split(self, text: str) -> List[Dict]:
        lines = text.split("\n")
        sections_map = {}
        current_section = "Unknown"
        
        for line in lines:
            if self._is_garbage_line(line):
                continue

            header = self._detect_header(line)
            if header:
                current_section = header
                if current_section not in sections_map:
                    sections_map[current_section] = []
                continue
            
            if current_section not in sections_map:
                sections_map[current_section] = []
            
            if line.strip():
                sections_map[current_section].append(line)

        final_sections = []
        for name, content_list in sections_map.items():
            raw_text = "\n".join(content_list)
            # ✨ APLICAMOS LA LIMPIEZA AQUÍ
            clean_text = self._clean_academic_text(raw_text)
            
            if name != "Unknown" and len(clean_text) > 30:
                final_sections.append({
                    "section": name,
                    "text": clean_text
                })
        
        return final_sections