import csv
import requests
import json
from retrieval.hybrid_retriever import HybridRetriever
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore

# ==============================
# CONFIGURACIÓN (English Queries)
# ==============================
FRAMEWORK_PILLARS = {
    "Technical Feasibility": "Technical limitations, transactions per second (TPS), latency, hardware requirements, and network scalability.",
    "Governance & Privacy": "Permissioned vs public blockchain, consensus mechanisms, GDPR compliance, and data privacy frameworks.",
    "Economic Viability": "Implementation costs, operational expenditure (OPEX), ROI, and cost-benefit analysis vs legacy systems.",
    "Strategic Alignment": "Trust models, disintermediation, transparency requirements, and business process re-engineering."
}

TOP_K = 10
OUTPUT_CSV = "blockchain_business_framework.csv"
OLLAMA_MODEL = "llama3.1" # Asegúrate de que este modelo esté descargado

# Inicializar componentes
embedder = OllamaEmbedder()
vector_store = ChromaVectorStore()
retriever = HybridRetriever(embedder, vector_store)

def generate_business_rule(dimension, snippet):
    """
    Llamada a Ollama con manejo de errores y validación de respuesta.
    """
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""
    [INST] You are a Senior Blockchain Architect. Based on this scientific finding:
    "{snippet}"
    
    Create a strategic BUSINESS RULE for a feasibility framework regarding {dimension}.
    Format: "IF [business condition] THEN [blockchain recommendation] BECAUSE [scientific evidence]"
    Constraint: Professional tone, max 30 words, answer in English. [/INST]
    """
    
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(url, json=payload, timeout=45)
        
        if response.status_code == 200:
            result = response.json().get("response", "").strip()
            # Si Ollama devuelve vacío, devolvemos un placeholder para saber que falló la generación
            return result if result else "Ollama returned an empty response"
        else:
            return f"Error: Ollama status {response.status_code}"
            
    except Exception as e:
        return f"Connection Error: {str(e)}"

def estimate_evidence_strength(metadata):
    """Evalúa la fuerza basado en la metadata técnica del chunk."""
    score = 1
    if metadata.get("section") in ["Results", "Findings", "Conclusion"]:
        score += 2
    if metadata.get("has_taxonomy_pattern"):
        score += 2
    if metadata.get("has_structured_table"):
        score += 1
    return score

# ==============================
# EJECUCIÓN PRINCIPAL
# ==============================
print(f"🚀 Iniciando extracción de reglas con modelo: {OLLAMA_MODEL}")

# 1. Verificar si Ollama está activo antes de empezar
try:
    requests.get("http://localhost:11434/api/tags")
except:
    print("❌ ERROR: Ollama no está corriendo. Abre la aplicación y vuelve a intentarlo.")
    exit()

all_rows = []

for dimension, query in FRAMEWORK_PILLARS.items():
    print(f"🔍 Searching for evidence: {dimension}...")
    # Usamos el método search que corregimos antes para usar los pesos híbridos
    results = retriever.search2(query, n_results=TOP_K)

    for rank, result in enumerate(results, 1):
        metadata = result["metadata"]
        text_content = result["text"].replace("\n", " ").strip()
        
        # Generar la regla de negocio
        print(f"   -> Generating rule for result #{rank}...")
        biz_rule = generate_business_rule(dimension, text_content)
        
        row = {
            "pilar": dimension,
            "rank": rank,
            "titulo": metadata.get("title", "N/A"),
            "seccion": metadata.get("section", "N/A"),
            "regla_negocio": biz_rule,
            "fortaleza_evidencia": estimate_evidence_strength(metadata),
            "final_score": round(result.get("final_score", 0), 4)
        }
        all_rows.append(row)

# Guardar CSV
fieldnames = ["pilar", "rank", "titulo", "seccion", "regla_negocio", "fortaleza_evidencia", "final_score"]
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"✅ Proceso completado. Revisa el archivo: {OUTPUT_CSV}")