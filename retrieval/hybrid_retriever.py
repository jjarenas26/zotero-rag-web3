import numpy as np
from datetime import datetime
from typing import List, Dict, Any

class HybridRetriever:
    """
    Motor de búsqueda híbrida que combina:
    1. Similitud Semántica (Vectores)
    2. Importancia Estructural (Secciones de los papers)
    3. Recencia (Actualidad de la investigación)
    4. Diversidad (Evitar sesgo de un solo autor)
    """

    def __init__(
        self,
        embedder,
        vector_store,
        semantic_weight: float = 0.50,    # Peso de la relevancia del texto
        structural_weight: float = 0.20,  # Peso de la jerarquía académica (Results > Abstract)
        recency_weight: float = 0.15,     # Peso de la actualidad del paper
        diversity_weight: float = 0.15    # Peso para variar fuentes bibliográficas
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.recency_weight = recency_weight
        self.diversity_weight = diversity_weight

    # --------------------------------------------------
    # Cálculo de Recencia No-Lineal (Prioridad a lo último)
    # --------------------------------------------------
    def _compute_recency_score(self, year: int) -> float:
        if not year or year == 0:
            return 0.5 # Default para papers sin año detectado

        current_year = datetime.now().year
        age = current_year - year

        if age <= 1: return 1.0     # 2025-2026 (Estado del arte)
        elif age <= 3: return 0.85  # 2023-2024
        elif age <= 5: return 0.65  # 2021-2022
        elif age <= 8: return 0.45  # 2018-2020
        else: return 0.30           # < 2018 (Contexto histórico)

    # --------------------------------------------------
    # Método Principal de Búsqueda (Híbrido)
    # --------------------------------------------------
    def search2(self, query_text: str, n_results: int = 10, where_filter: dict = None) -> List[Dict]:
        """
        Realiza una búsqueda semántica y aplica el re-ranking basado en 
        metadatos académicos.
        """
        # 1. Generar embedding de la consulta
        query_embedding = self.embedder.embed_text(query_text)

        # 2. Query inicial a Chroma (pedimos más para filtrar después)
        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results * 2,
            where_filter=where_filter
        )

        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0]

        scored_results = []
        doc_counts = {} # Registro para diversidad

        for doc, metadata, distance in zip(documents, metadatas, distances):
            # A. Score Semántico (Invertimos la distancia para que menor sea mejor)
            semantic_score = 1 / (1 + distance)
            
            # B. Score Estructural (Priorizamos secciones clave)
            # Recuperamos el structural_weight calculado en la ingesta
            structural_score = metadata.get("structural_weight", 0.6)
            
            # Bonus por patrones de Taxonomía o Tablas detectados por el Chunker
            if metadata.get("has_taxonomy_pattern"):
                structural_score += 0.15
            if metadata.get("has_structured_table"):
                structural_score += 0.10
            
            # C. Score de Recencia
            year = metadata.get("year", 0)
            recency_score = self._compute_recency_score(year)

            # D. Score de Diversidad (Penalizamos si traemos demasiados chunks del mismo paper)
            doc_id = metadata.get("doc_id", "unknown")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            
            if doc_counts[doc_id] == 1:
                diversity_score = 1.0
            elif doc_counts[doc_id] == 2:
                diversity_score = 0.7
            else:
                diversity_score = 0.4 # Penalización fuerte al tercer chunk del mismo doc

            # --- CÁLCULO DEL FINAL SCORE PONDERADO ---
            final_score = (
                self.semantic_weight * semantic_score +
                self.structural_weight * min(structural_score, 1.5) +
                self.recency_weight * recency_score +
                self.diversity_weight * diversity_score
            )

            scored_results.append({
                "text": doc,
                "metadata": metadata,
                "final_score": final_score,
                "breakdown": {
                    "semantic": round(semantic_score, 3),
                    "structural": round(structural_score, 3),
                    "recency": round(recency_score, 3),
                    "diversity": round(diversity_score, 3)
                }
            })

        # 3. Ordenar por el score final y recortar al Top K deseado
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_results[:n_results]

    def embed_query(self, text: str):
        """Helper para obtener el embedding de una consulta"""
        return self.embedder.embed_text(text)