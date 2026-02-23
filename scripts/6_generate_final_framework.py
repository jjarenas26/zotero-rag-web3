import pandas as pd
import requests
import os

# Configuración
INPUT_CSV = "blockchain_business_framework.csv"
FINAL_DOC = "FRAMEWORK_FINAL_BLOCKCHAIN.md"
OLLAMA_MODEL = "llama3.1"

def ask_ollama_to_synthesize(pilar, data_rows):
    """
    Sintetiza las reglas y asocia títulos reales de la literatura.
    """
    # Creamos un contexto que incluya la regla y la fuente (título)
    context_items = []
    for _, row in data_rows.iterrows():
        context_items.append(f"Source: {row['titulo']} | Rule: {row['regla_negocio']}")
    
    rules_context = "\n".join(context_items)
    
    prompt = f"""
    [INST] You are a Senior Strategic Technology Consultant. 
    Analyze these rules derived from specific scientific papers for the pillar: "{pilar}".
    
    DATA SOURCE AND RULES:
    {rules_context}
    
    TASK:
    1. Synthesize these into 3 EXECUTIVE DECISION CRITERIA in Spanish.
    2. Define an "Adoption Threshold" (When to use vs. when to avoid) in Spanish.
    3. Define a final "Conclusion" in Spanish.
    4. Provide a "Scientific References" section listing the unique titles of the papers used.
    
    STRICT FORMATTING RULES:
    - Language: Spanish (español).
    - Tone: Professional/Executive.
    - References: Use the actual titles provided in the 'Source' part of the context.
    - Output: Only return the Markdown content. No conversational filler.
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
                    "temperature": 0.2, # Más bajo para evitar invenciones
                    "num_ctx": 8192     # Aumentado para manejar más texto
                }
            },
            timeout=180
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"Error de Ollama (Status {response.status_code})"
    except Exception as e:
        return f"Error en la síntesis: {str(e)}"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"❌ No se encuentra {INPUT_CSV}.")
        return

    df = pd.read_csv(INPUT_CSV)
    df = df[df['regla_negocio'].notna()]
    
    print(f"📄 Generando Framework con Referencias Reales...")

    with open(FINAL_DOC, "w", encoding="utf-8") as f:
        f.write("# Framework de Factibilidad Blockchain\n")
        f.write("## Basado en Evidencia Científica y Revisión Sistemática de Literatura\n\n")

        pilares = df['pilar'].unique()
        
        for pilar in pilares:
            print(f"🧠 Procesando pilar: {pilar}...")
            
            # Tomamos las filas con mayor fortaleza
            top_data = df[df['pilar'] == pilar].sort_values(
                by='fortaleza_evidencia', ascending=False
            ).head(6) # 6 reglas es ideal para no saturar el prompt
            
            if top_data.empty:
                continue

            synthesis = ask_ollama_to_synthesize(pilar, top_data)
            
            f.write(f"## Pilar: {pilar}\n")
            f.write(synthesis)
            f.write("\n\n---\n\n")

    print(f"✅ ¡Framework terminado! Revisa: {FINAL_DOC}")

if __name__ == "__main__":
    main()