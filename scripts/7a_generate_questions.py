import sys
import os
import json
import requests
import re
import random

# Configuración
FRAMEWORK_FILE = "FRAMEWORK_FINAL_BLOCKCHAIN.md"
QUESTIONS_FILE = "assessment_questions.json"
OLLAMA_MODEL = "llama3.1"
PILLARS = ["Technical", "Organizational", "Environmental/Strategic", "Governance/Legal"]
QUESTION = 5

def extract_section(content, pillar):
    pattern = rf"(?i)##.*?(?:Pilar|Pillar)?\s*?:?\s*?{re.escape(pillar)}.*?\n(.*?)(?=\n##|\n---|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else None

def generate_questions_pro():
    if not os.path.exists(FRAMEWORK_FILE):
        print(f"❌ Error: No existe {FRAMEWORK_FILE}")
        return

    with open(FRAMEWORK_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    final_questions = []

    for pillar in PILLARS:
        print(f"📖 Analizando pilar: {pillar}...")
        section_content = extract_section(full_content, pillar)
        
        if not section_content:
            continue

        # Memoria temporal para evitar repeticiones en el mismo pilar
        topics_covered = []

        for i in range(1, QUESTION+1):
            print(f"   -> Redactando pregunta {i}/{QUESTION} para {pillar}...")
            
            # Prompt mejorado con instrucción de NO REPETICIÓN
            avoid_instruction = f"Avoid these topics already covered: {', '.join(topics_covered)}" if topics_covered else ""
            
            prompt = f"""
            [INST] 
            ROLE: Senior Blockchain Research Analyst.
            TASK: Generate ONE (1) unique "Yes/No" diagnostic question in SPANISH for the pillar: {pillar}.
            
            CONTEXT:
            {section_content}
            
            INSTRUCTIONS:
            - The question must evaluate a NEW technical or strategic requirement.
            - {avoid_instruction}
            - Ensure the question is professionally phrased in Spanish.
            - Assign "is_critical": true ONLY if the context describes it as a mandatory requirement.
            
            JSON FORMAT (OBJECT ONLY):
            {{
              "pillar": "{pillar}",
              "question_es": "...",
              "topic_keyword": "one_word_topic",
              "is_critical": false
            }}
            [/INST]
            """

            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
                    timeout=90
                )
                
                q_data = json.loads(response.json().get("response", "{}"))
                
                if isinstance(q_data, dict) and "question_es" in q_data:
                    # --- ALGORITMO DE BALANCEO DE PESOS ---
                    # Si es crítico: 15. Si no: Alternamos entre 8 y 12 para dar dinamismo al Radar.
                    if q_data.get("is_critical") is True:
                        q_data["weight"] = 15
                    else:
                        q_data["weight"] = random.choice([8, 10, 12])
                    
                    # Guardar el tema para no repetirlo en la siguiente iteración del pilar
                    topics_covered.append(q_data.get("topic_keyword", "general"))
                    
                    # Limpiar campos extra antes de guardar
                    q_data.pop("topic_keyword", None)
                    q_data["pillar"] = pillar
                    final_questions.append(q_data)
                
            except Exception as e:
                print(f"   ❌ Error en {pillar} Q{i}: {str(e)}")

    # Guardado Final
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_questions, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Proceso terminado. {len(final_questions)} preguntas balanceadas y diversas generadas.")

if __name__ == "__main__":
    generate_questions_pro()