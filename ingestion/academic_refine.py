import requests

class AcademicRefiner:
    def __init__(self, model="llama3.1", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = f"{base_url}/api/generate"

    # Agregamos 'self' aquí
    def _get_academic_clean_prompt(self, raw_text_chunk: str) -> str:
        return f"""
        [ROLE: EXPERT ACADEMIC COPYEDITOR]
        Your task is to RECONSTRUCT the following raw text extracted from a scientific PDF.
        
        INPUT TEXT:
        {raw_text_chunk}
        
        STRICT RULES:
        1. REPAIR words split by hyphens (e.g., "block- chain" -> "blockchain").
        2. REMOVE all system noise: page numbers, journal headers (Elsevier, MDPI, etc.), DOI links, and editor names (e.g., "Academic Editor: ...").
        3. FIX sentence flow: ensure sentences that were broken by line breaks are joined into a single fluid paragraph.
        4. PRESERVE all technical content, citations (e.g., [12]), and numerical data. 
        5. DO NOT summarize. DO NOT add comments. DO NOT change the vocabulary.
        6. OUTPUT: Return only the cleaned text.
        
        CLEANED ACADEMIC TEXT:
        """

    def refine_section(self, section_name: str, raw_text: str) -> str:
        # 1. Limpieza básica antes de enviar al LLM para ahorrar tokens
        text_to_process = raw_text.strip()
        if not text_to_process:
            return ""

        prompt = self._get_academic_clean_prompt(text_to_process)
        
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": 4096  # Aseguramos suficiente ventana de contexto
                    }
                },
                timeout=60 # Evita que el script se cuelgue si Ollama tarda
            )
            
            if response.status_code == 200:
                # Algunos modelos de Ollama devuelven el texto con etiquetas, limpiamos por si acaso
                cleaned_text = response.json().get("response", "").strip()
                return cleaned_text
            
            print(f"⚠️ Ollama Error: {response.status_code} - {response.text}")
            return raw_text 

        except Exception as e:
            print(f"❌ Connection Error: {str(e)}")
            return raw_text