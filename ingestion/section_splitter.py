import re
from typing import List, Dict


class SectionSplitter:

    def __init__(self):
        self.section_keywords = {
            "abstract": "Abstract",
            "introduction": "Introduction",
            "background": "Background",
            "literature review": "Literature Review",
            "methodology": "Methodology",
            "methods": "Methodology",
            "materials and methods": "Methodology",
            "results": "Results",
            "findings": "Results",
            "discussion": "Discussion",
            "conclusion": "Conclusion",
            "conclusions": "Conclusion",
            "future work": "Future Work",
            "recommendations": "Recommendations",
            "references": "References",
            "bibliography": "References"
        }

    # --------------------------------------------------
    # 🔹 Normalización robusta
    # --------------------------------------------------
    def _normalize(self, line: str) -> str:
        line = line.replace("\xa0", " ")  # espacios raros PDF
        line = line.strip()

        # eliminar numeración tipo:
        # 1.
        # 1.1
        # I.
        # IV-A
        # 2)
        line = re.sub(r"^(\d+(\.\d+)*|[ivxlcdm]+)([\.\-\)]\s*)?", "", line, flags=re.IGNORECASE)

        # eliminar ":" final
        line = line.rstrip(":").strip()

        return line.lower()

    # --------------------------------------------------
    # 🔹 Detección segura de headers
    # --------------------------------------------------
    def _detect_header(self, line: str) -> str | None:
        cleaned = self._normalize(line)

        # líneas demasiado largas no son headers
        if len(cleaned) == 0 or len(cleaned) > 100:
            return None

        # evitar detectar referencias individuales
        if re.search(r"\[\d+\]", line):
            return None

        if re.search(r"\(\d{4}\)", line):
            return None

        # PRIORIDAD absoluta para references
        if cleaned == "references":
            return "References"

        # match exacto primero
        for keyword, canonical in self.section_keywords.items():
            if cleaned == keyword:
                return canonical

        # match flexible (ej: findings & suggestions...)
        for keyword, canonical in self.section_keywords.items():
            if keyword in cleaned:
                # solo permitir flexible si línea es corta
                if len(cleaned.split()) <= 8:
                    return canonical

        return None

    # --------------------------------------------------
    # 🔹 Split principal
    # --------------------------------------------------
    def split(self, text: str) -> List[Dict]:
        lines = text.split("\n")
        sections = []

        current_section = "Unknown"
        buffer = []
        in_references = False

        def flush():
            if buffer:
                sections.append({
                    "section": current_section,
                    "text": "\n".join(buffer).strip()
                })

        for line in lines:

            # 🔒 Si estamos en references → no detectar más headers
            if in_references:
                buffer.append(line)
                continue

            header = self._detect_header(line)

            if header:
                flush()
                current_section = header
                buffer = []

                if header == "References":
                    in_references = True
            else:
                buffer.append(line)

        flush()

        return sections
