import requests
import json
import os

# Configuración
FRAMEWORK_FILE = "FINAL_FRAMEWORK.md"
QUESTIONS_FILE = "assessment_questions.json"
OLLAMA_MODEL = "llama3.1"

def generate_questions_from_framework():
    if not os.path.exists(FRAMEWORK_FILE):
        print("❌ No se encuentra el archivo del framework.")
        return

    with open(FRAMEWORK_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Prompt en inglés para precisión técnica, pidiendo salida en JSON
    prompt = f"""
    [INST] You are a Senior Consultant. Based on the following Blockchain Feasibility Framework synthesized from scientific papers:
    
    {content}
    
    TASK:
    Generate a list of 8-10 specific "Yes/No" questions to evaluate a business project.
    Each question must be linked to one of the pillars (Technical, Governance, Economic, Strategic).
    Return ONLY a JSON list with this structure:
    [
      {{"pillar": "Pillar Name", "question_es": "Pregunta en español", "weight": 10, "is_critical": true/false}}
    ]
    [/INST]
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120
        )
        questions = response.json().get("response")
        
        # Guardar las preguntas en un JSON
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            f.write(questions)
        
        print(f"✅ Cuestionario generado dinámicamente en {QUESTIONS_FILE}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_questions_from_framework()