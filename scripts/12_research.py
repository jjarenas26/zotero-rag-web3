from retrieval.hybrid_retriever import HybridRetriever
from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import textwrap

def analizar_dimension_completa(resultados_lista, w1=0.4, w2=0.3, w3=0.3):
    if not resultados_lista:
        return 0.0, 0.0
    scores_individuales = []
    for res in resultados_lista:
        trl_norm = float(res['metadata'].get('trl', 1)) / 9.0
        recency = float(res['breakdown'].get('recency', 0.5))
        semantic = float(res['breakdown'].get('semantic', 0.5))
        f_i = (w1 * trl_norm + w2 * recency + w3 * semantic) * 10
        scores_individuales.append(f_i)
    promedio = np.mean(scores_individuales)
    desviacion = np.std(scores_individuales)
    return round(promedio, 2), round(desviacion, 2)

def wrap_text(text, width=50):
    if not text: return "N/A"
    return "\n".join(textwrap.wrap(str(text), width=width))

def generar_investigacion_final(retriever, queries):
    filas_scores = []
    scores_globales = []
    evidencia_detallada = [] # Para el CSV
    
    for dimension, query in queries.items():
        resultados_k = retriever.search2(query, n_results=5)
        
        if resultados_k:
            avg, std = analizar_dimension_completa(resultados_k)
            scores_globales.append(avg)
            nivel_incertidumbre = "Bajo" if std < 1.0 else "Medio" if std < 2.0 else "Alto"
            
            # 1. Datos para el Reporte Ejecutivo (PDF)
            filas_scores.append({
                "Dimensión": dimension,
                "F-Score (Avg)": avg,
                "Desviación (σ)": std,
                "Incertidumbre": nivel_incertidumbre,
                "TRL Pred.": int(np.median([float(r['metadata'].get('trl', 0)) for r in resultados_k])),
                "Doc Principal": resultados_k[0]['metadata'].get('doc_id', 'N/A')
            })
            
            # 2. Datos para la Matriz de Evidencia (CSV)
            for res in resultados_k:
                meta = res['metadata']
                evidencia_detallada.append({
                    "Pilar_TOE": dimension,
                    "Doc_ID": meta.get("doc_id"),
                    "Año": meta.get("year"),
                    "TRL": meta.get("trl"),
                    "F_Score_Individual": round((0.4*(float(meta.get("trl",1))/9) + 0.3*res['breakdown']['recency'] + 0.3*res['breakdown']['semantic'])*10, 2),
                    "Justificacion_TRL_Gap": meta.get("trl_justification"),
                    "Riesgo_Contradiccion": meta.get("contradictions"),
                    "Evidencia_Texto": res['text'],
                    "URL_Ref": meta.get("url", "N/A")
                })

    # Crear DataFrames
    df_scores = pd.DataFrame(filas_scores)
    df_csv = pd.DataFrame(evidencia_detallada)
    f_final = round(np.mean(scores_globales), 2)

    # --- EXPORTAR A CSV (Matriz Completa de Evidencia) ---
    csv_filename = 'Matriz_Evidencia_Blockchain_Completa.csv'
    df_csv.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✅ CSV generado con éxito: {csv_filename}")

    # --- EXPORTAR A PDF (Reporte Ejecutivo) ---
    with PdfPages('Reporte_Ejecutivo_Factibilidad.pdf') as pdf:
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.axis('off')
        plt.title(f"RESUMEN EJECUTIVO: FACTIBILIDAD TOE\nScore Global: {f_final}/10", 
                  fontsize=16, fontweight='bold', pad=30)
        
        # En el PDF solo dejamos los scores para que sea limpio
        tabla = ax.table(cellText=df_scores.values, colLabels=df_scores.columns, 
                         cellLoc='center', loc='center', colColours=["#2c3e50"]*6)
        
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(12)
        tabla.scale(1.1, 4)
        
        for (row, col), cell in tabla.get_celld().items():
            if row == 0:
                cell.get_text().set_color('white')
                cell.get_text().set_weight('bold')
            if row > 0 and col == 3:
                val = df_scores.iloc[row-1, col]
                if val == "Alto": cell.set_facecolor("#fab1a0")
                if val == "Bajo": cell.set_facecolor("#55efc4")
        
        pdf.savefig(bbox_inches='tight')
        plt.close()
        print(f"✅ PDF ejecutivo generado: Reporte_Ejecutivo_Factibilidad.pdf")

if __name__ == "__main__":
    embedder = OllamaEmbedder()
    vector_store = ChromaVectorStore()
    retriever = HybridRetriever(embedder, vector_store)
    evidencia_total = []
    query_prueba_1 = (
        "Performance benchmarks of permissioned blockchain frameworks (Hyperledger, Corda, Quorum) for high-volume banking transactions: scalability, latency, and throughput constraints"
        #"Límites de rendimiento, TPS y latencia en protocolos blockchain "
        #"permisionados para procesamiento de transacciones bancarias masivas"
    )
    query_prueba_2 = (
        "Organizational readiness and cost-benefit analysis of blockchain adoption in incumbent banks: ROI, human talent acquisition, and top management support challenges"
        # "Mecanismos de privacidad en ledgers distribuidos, protocolos de "
        # "Zero-Knowledge Proofs (ZKP) y cumplimiento del secreto bancario "
        # "en infraestructuras financieras digitales"
    )

    query_prueba_3 = (
        "Competitive pressure and industry standards for blockchain interoperability in financial services: ISO 20022 compliance and the influence of fintech ecosystems on bank adoption"
        # "Interoperabilidad de middleware blockchain con sistemas Core Bancario "
        # "legacy, latencia de sincronización de bases de datos externas y "
        # "estándares de mensajería financiera (ISO 20022)"
    )
    query_prueba_4 = (
        "Regulatory compliance and legal frameworks for distributed ledgers in banking: data sovereignty, KYC/AML automation, and conflict resolution policies in smart contracts"
    )

    queries_investigacion = {
        "Technical": query_prueba_1,
        "Organizational": query_prueba_2,
        "Environmental": query_prueba_3,
        "Governance": query_prueba_4
    }

    generar_investigacion_final(retriever, queries_investigacion)