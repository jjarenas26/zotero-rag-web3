import csv
import requests
import json
import sys
import os

# 1. PATH SETUP
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retrieval.hybrid_retriever import HybridRetriever
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore

# CONFIGURATION
TOP_K = 10
OUTPUT_CSV = "blockchain_business_framework.csv"
OLLAMA_MODEL = "llama3.1"

# Fixed Pillars based on Technology Adoption Framework (TOE)
ADOPTION_PILLARS = {
    "Technical": "Focus on scalability, security, interoperability, and technical complexity.",
    "Organizational": "Focus on cost, ROI, top management support, and internal resources.",
    "Environmental/Strategic": "Focus on market pressure, industry standards, and competitive advantage.",
    "Governance/Legal": "Focus on regulatory compliance, legal frameworks, and consensus policies."
}

# Initialize Components
embedder = OllamaEmbedder(model="nomic-embed-text")
vector_store = ChromaVectorStore()
retriever = HybridRetriever(embedder, vector_store)

def generate_optimized_queries(pillar_name, description):
    """
    Uses the library context to generate the best technical queries 
    for each fixed adoption pillar.
    """
    print(f"🧠 Generating optimized research queries for: {pillar_name}...")
    
    # Get a small sample of the library to understand the terminology used by the authors
    sample = retriever.search2(query_text=f"Blockchain {pillar_name} {description}", n_results=5)
    context = "\n".join([d['text'][:500] for d in sample])
    
    prompt = f"""
    [INST] 
    As a Research Expert, your goal is to extract the best search terms for the '{pillar_name}' pillar.
    PILLAR DESCRIPTION: {description}
    LIBRARY CONTEXT: {context}
    
    TASK: Based on the terminology found in the library, generate a single, highly technical 
    search query (in English) to find the most relevant scientific evidence for this pillar.
    
    OUTPUT: Return ONLY the string of the query. No preamble.
    [/INST]
    """
    
    try:
        response = requests.post("http://localhost:11434/api/generate", 
                                 json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        return response.json().get("response", "").strip().strip('"')
    except:
        return f"Blockchain {pillar_name} adoption factors"

def generate_business_rule(pillar, snippet):
    """Generates a strategic rule based on scientific evidence."""
    prompt = f"""
    [INST] 
    ROLE: Senior Blockchain Consultant.
    CONTEXT: "{snippet}"
    TASK: Create a strategic BUSINESS RULE for a feasibility framework regarding the '{pillar}' dimension.
    FORMAT: "IF [business condition] THEN [blockchain recommendation] BECAUSE [scientific evidence]"
    CONSTRAINT: Professional tone, max 30 words, answer in English.
    [/INST]
    """
    try:
        res = requests.post("http://localhost:11434/api/generate", 
                            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        return res.json().get("response", "").strip()
    except:
        return "Generation Error"

# ==============================
# MAIN EXECUTION
# ==============================

all_rows = []

for pillar, description in ADOPTION_PILLARS.items():
    # Phase 1: Dynamic Query Generation
    optimized_query = generate_optimized_queries(pillar, description)
    print(f"✅ Optimized Query: {optimized_query}")
    
    # Phase 2: Evidence Retrieval
    print(f"🔍 Investigating: {pillar}...")
    results = retriever.search2(query_text=optimized_query, n_results=TOP_K)

    for rank, result in enumerate(results, 1):
        metadata = result["metadata"]
        text_content = result["text"].replace("\n", " ").strip()
        
        print(f"   -> Generating business rule for evidence #{rank}...")
        biz_rule = generate_business_rule(pillar, text_content)
        
        all_rows.append({
            "pilar": pillar,
            "rank": rank,
            "titulo": metadata.get("title", "N/A"),
            "regla_negocio": biz_rule,
            "fortaleza_evidencia": 3 if metadata.get("section") in ["Results", "Findings", "Conclusion"] else 1
        })

# Save to CSV
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["pilar", "rank", "titulo", "regla_negocio", "fortaleza_evidencia"])
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\n✅ Framework processed with optimized queries! File: {OUTPUT_CSV}")