import requests
import time

class AcademicRefiner:
    def __init__(self, model="llama3.1", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = f"{base_url}/api/generate"

    def _get_academic_clean_prompt(self, raw_text_chunk: str) -> str:
        return f"""
        [ROLE: EXPERT ACADEMIC COPYEDITOR]
        Your task is to RECONSTRUCT the following raw text extracted from a scientific PDF.
        
        INPUT TEXT:
        {raw_text_chunk}
        
        STRICT RULES:
        1. REPAIR words split by hyphens (e.g., "block- chain" -> "blockchain").
        2. REMOVE all system noise: page numbers, journal headers, DOI links, and editor names.
        3. FIX sentence flow: join broken sentences into fluid paragraphs.
        4. PRESERVE all technical content, citations [12], and data.
        5. DO NOT summarize. DO NOT add comments.
        6. OUTPUT: Return only the cleaned text.
        
        CLEANED ACADEMIC TEXT:
        """

    def refine_section(self, section_name: str, raw_text: str, chunk_size: int = 3000) -> str:
        """
        Limpia una sección dividiéndola en partes si es demasiado larga.
        """
        # Si el texto es pequeño, se procesa directamente
        if len(raw_text) <= chunk_size:
            return self._call_ollama(raw_text)

        # Si es largo (como tus 95k palabras), dividimos
        print(f"📦 Section '{section_name}' is large ({len(raw_text)} chars). Splitting...")
        
        # Dividir por párrafos para no cortar oraciones a la mitad
        paragraphs = raw_text.split("\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n"
            else:
                chunks.append(current_chunk)
                current_chunk = p + "\n"
        chunks.append(current_chunk)

        refined_parts = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            print(f"  -> Processing part {i+1}/{len(chunks)} of {section_name}...")
            refined_parts.append(self._call_ollama(chunk))
            # Opcional: pequeño delay para no saturar Ollama
            time.sleep(0.1)

        return "\n".join(refined_parts)

    def process_document_flow(self, raw_text: str, chunk_size: int = 4000):
        # 1. AHORA SÍ: Dividimos por párrafos para no romper ideas
        paragraphs = raw_text.split("\n") 
        
        structured_data = {}
        current_section = "Initial_Meta"
        current_chunk = ""

        for p in paragraphs:
            # Acumulamos párrafos hasta llegar al tamaño del chunk
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n"
            else:
                # Cuando el chunk está lleno, lo procesamos con el LLM
                response = self._process_chunk_with_llm(current_chunk, current_section)
                
                # Actualizamos la sección si el LLM detectó un cambio
                if "SECTION:" in response:
                    parts = response.split("SECTION:", 1)
                    header_line = parts[1].split("\n")[0].strip()
                    current_section = header_line
                    content = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
                else:
                    content = response

                if current_section not in structured_data:
                    structured_data[current_section] = []
                print("procesando {current_section}")
                structured_data[current_section].append(content)
                
                # Reiniciamos el chunk con el párrafo actual
                current_chunk = p + "\n"

        return structured_data
    
    def _process_chunk_with_llm(self, chunk, current_section):
        prompt = f"""
            [TASK: ACADEMIC TEXT RECONSTRUCTION]
            Identify the current section and clean the text.
            
            PREVIOUS SECTION DETECTED: {current_section}
            
            TEXT TO PROCESS:
            {chunk}
            
            STRICT RULES:
            1. If a NEW section header (e.g. Introduction, Methodology) appears, start your response with 'SECTION: [Name]'.
            2. Clean all PDF noise (footers, authors, page numbers, split words).
            3. Return ONLY the cleaned text and the section header if it changed.
            """
        return self._call_ollama2(prompt)

    def _call_ollama2(self, prompt):
        res = requests.post(self.base_url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0} # 0 para máxima fidelidad al texto
        })
        return res.json().get("response", "")

    def _call_ollama(self, text: str) -> str:
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": self._get_academic_clean_prompt(text),
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 4096}
                },
                timeout=90
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            print(f"❌ Error en Ollama: {e}")
        return text # Fallback al original