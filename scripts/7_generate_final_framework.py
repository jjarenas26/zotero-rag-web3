import pandas as pd
import requests
import os

# Configuración
INPUT_CSV = "blockchain_business_framework.csv"
FINAL_DOC = "FRAMEWORK_FINAL_BLOCKCHAIN.md"
OLLAMA_MODEL = "llama3.1"

def ask_ollama_to_synthesize(pilar, rules):
    """
    Toma las reglas técnicas en inglés y las sintetiza en un framework ejecutivo en español.
    """
    # Convertimos la lista de reglas en un string numerado
    rules_context = "\n".join([f"- {r}" for r in rules])
    
    # Prompt en INGLÉS para mejor razonamiento técnico del modelo
    prompt = f"""
    [INST] You are a Senior Strategic Technology Consultant. 
    You have extracted the following decision rules from scientific literature regarding the pillar: "{pilar}".
    
    EXTRACTED RULES:
    {rules_context}
    
    TASK:
    1. Analyze these rules and synthesize them into 3 EXECUTIVE DECISION CRITERIA.
    2. Define an "Adoption Threshold" (When to use vs. when to avoid blockchain based on the evidence).
    3. VERY IMPORTANT: Write the final response COMPLETELY IN SPANISH (español) with a professional tone.
    4. Use Markdown format with bold text to highlight key takeaways.
    [/INST]
    """
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL, 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "temperature": 0.3, # Menor temperatura = más fidelidad a los datos
                    "num_ctx": 4096     # Asegurar ventana de contexto suficiente
                }
            },
            timeout=120 # Aumentado para síntesis complejas
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"Error de Ollama (Status {response.status_code})"
    except Exception as e:
        return f"Error en la síntesis: {str(e)}"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"❌ No se encuentra {INPUT_CSV}. Ejecuta el script 5 primero.")
        return

    # Cargar datos
    df = pd.read_csv(INPUT_CSV)
    
    # Limpiar posibles filas donde la regla falló o quedó vacía
    df = df[df['regla_negocio'].notna()]
    df = df[~df['regla_negocio'].str.contains("Error|Connection", na=False)]
    
    print(f"📄 Procesando reglas técnicas para generar el Framework en Español...")

    with open(FINAL_DOC, "w", encoding="utf-8") as f:
        f.write("# Framework de Factibilidad Blockchain\n")
        f.write("## Basado en Evidencia Científica y Revisión Sistemática de Literatura\n\n")
        f.write("---\n\n")

        # Iterar por cada pilar (Pillars en inglés del CSV)
        pilares = df['pilar'].unique()
        
        for pilar in pilares:
            print(f"🧠 Sintetizando pilar técnico: {pilar}...")
            
            # Seleccionamos las reglas con mayor fortaleza de evidencia
            top_rules = df[df['pilar'] == pilar].sort_values(
                by='fortaleza_evidencia', ascending=False
            )['regla_negocio'].head(7).tolist()
            
            if not top_rules:
                continue

            # Llamada a Ollama con prompt en inglés y respuesta en español
            synthesis = ask_ollama_to_synthesize(pilar, top_rules)
            
            f.write(f"## Pilar: {pilar}\n")
            f.write(synthesis)
            f.write("\n\n---\n\n")

    print(f"✅ ¡Framework terminado! Revisa el archivo: {FINAL_DOC}")

if __name__ == "__main__":
    main()