import csv
import re
from retrieval.hybrid_retriever import HybridRetriever
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore

# ==============================
# CONFIGURACIÓN
# ==============================
DIMENSIONS = [
    "Vision general",
    "Case study",
    "Interoperability",
    "Performance efficiency",
    "Availability",
    "Scalability",
    "Maintainability",
    "Security"
]

TOP_K = 20
OUTPUT_CSV = "literature_review_framework.csv"

# ==============================
# INICIALIZAR RETRIEVER
# ==============================
embedder = OllamaEmbedder()
vector_store = ChromaVectorStore()
retriever = HybridRetriever(embedder, vector_store)

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def normalize_text(text: str) -> str:
    return text.replace("\n", " ").replace(",", " ").strip()

def extract_metrics(snippet: str) -> list:
    """
    Detecta métricas mencionadas en el snippet.
    """
    snippet = snippet.lower()
    metrics_patterns = [
        "throughput", "latency", "transactions per second", "tps",
        "uptime", "availability", "scalability", "response time",
        "maintainability", "security", "integrity", "consistency",
        "accuracy", "precision", "recall", "f1-score"
    ]
    found = [m for m in metrics_patterns if m in snippet]
    return found

def estimate_evidence_strength(snippet: str) -> str:
    """
    Heurística simple:
    - strong: cifras, tablas, resultados concretos
    - medium: descripciones metodológicas
    - weak: solo discusión teórica
    """
    snippet_lower = snippet.lower()
    if re.search(r"\d+(\.\d+)?\s*(%|ms|s|tps|transactions|hours|days)", snippet_lower):
        return "strong"
    elif any(word in snippet_lower for word in ["experiment", "evaluation", "study", "methodology", "results"]):
        return "medium"
    else:
        return "weak"

# ==============================
# RECUPERACIÓN Y EXPORTACIÓN
# ==============================
all_rows = []

for dimension in DIMENSIONS:
    print(f"\n🔹 Procesando dimensión: {dimension}")

    results = retriever.query(query_text=dimension, n_results=TOP_K)

    for rank, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        snippet = normalize_text(result.get("text", ""))

        metrics = extract_metrics(snippet)
        evidence = estimate_evidence_strength(snippet)

        row = {
            "dimension": dimension,
            "rank": rank,
            "doc_id": metadata.get("doc_id", ""),
            "title": metadata.get("title", ""),
            "year": metadata.get("year", 0),
            "section": metadata.get("section", ""),
            "snippet": snippet,
            "metrics": "; ".join(metrics) if metrics else "",
            "evidence_strength": evidence,
            "semantic_score": round(result.get("semantic_score", 0), 4),
            "structural_score": round(result.get("structural_weight", 0), 4),
            "recency_score": round(result.get("recency_weight", 0), 4),
            "diversity_score": round(result.get("diversity_score", 0), 4),
            "final_score": round(result.get("final_score", 0), 4)
        }

        all_rows.append(row)

# ==============================
# GUARDAR CSV
# ==============================
fieldnames = [
    "dimension", "rank", "doc_id", "title", "year", "section", "snippet",
    "metrics", "evidence_strength",
    "semantic_score", "structural_score", "recency_score", "diversity_score", "final_score"
]

with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\n✅ CSV generado con {len(all_rows)} filas: {OUTPUT_CSV}")
