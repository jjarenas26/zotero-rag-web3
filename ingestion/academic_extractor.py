import requests
import json

class AcademicIntelligenceExtractor:
    def __init__(self, model="llama3.1", base_url="http://localhost:11434"):
        self.model = model
        self.url = f"{base_url}/api/generate"

    def _get_specialized_prompt(self, section_name: str, text: str) -> str:
        section_lower = section_name.lower()
        
        # Guía de referencia TRL inyectada para precisión del modelo
        trl_reference_scale = """
        TRL REFERENCE SCALE:
        - TRL 1-3: Basic principles, paper-based research, mathematical models.
        - TRL 4-5: Component validation in laboratory or simulated environment.
        - TRL 6-7: Prototype demonstration in a relevant or operational environment (Pilots/MVPs).
        - TRL 8-9: Actual system completed, qualified, and proven in mission operations.
        """

        # Configuración del enfoque según la sección
        if "introduction" in section_lower:
            task_focus = "Identify ENTITIES and the PROBLEM STATEMENT. What technologies are being introduced?"
        elif "methodology" in section_lower:
            task_focus = f"Determine the TRL level using the provided scale. Analyze if the testing was in a lab or real environment.\n{trl_reference_scale}"
        elif "results" in section_lower:
            task_focus = "Extract raw TECHNICAL FINDINGS and specific PERFORMANCE CHALLENGES (latency, throughput, etc.)."
        elif "discussion" in section_lower:
            task_focus = "Identify COMPARISONS with other tech and TRADE-OFFS (pros/cons compared to state-of-the-art)."
        elif "conclusion" in section_lower:
            task_focus = "Identify STRATEGIC CHALLENGES and FUTURE WORK. What are the 'unsolved' parts?"
        else:
            task_focus = "General strategic synthesis of the section."

        return f"""
        [ROLE: SENIOR STRATEGIC TECHNOLOGY AUDITOR]
        SECTION CONTEXT: {section_name}
        TASK: {task_focus}
        
        INPUT TEXT:
        {text}
        
        STRICT JSON OUTPUT FORMAT:
        {{
            "entities": [
                {{"name": "EntityName", "type": "Protocol/Platform/Algorithm", "relation": "Role in this paper"}}
            ],
            "trl_analysis": {{
                "level": 1-9,
                "justification": "Short evidence-based sentence in English explaining the assigned TRL."
            }},
            "contradictions": [
                "List specific limitations, technical debates, or trade-offs found in the text"
            ]
        }}
        
        STRICT RULES:
        1. Return ONLY the JSON object.
        2. Assign TRL ONLY if the text provides evidence; otherwise, default to null or 0.
        3. Language: Prompt and Output MUST be in English for maximum precision.
        4. No conversational filler.
        """

    def extract_intelligence(self, section_name: str, clean_text: str) -> dict:
        if not clean_text or len(clean_text) < 150:
            return {}

        prompt = self._get_specialized_prompt(section_name, clean_text)
        
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1} # Temperatura baja para evitar creatividad
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return json.loads(response.json().get("response", "{}"))
            return {}
            
        except Exception as e:
            print(f"❌ Error extracting intel from {section_name}: {e}")
            return {}