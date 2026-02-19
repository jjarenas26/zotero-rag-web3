import numpy as np
from datetime import datetime
from typing import List, Dict, Any
import math


class HybridRetriever:

    def __init__(
        self,
        embedder,
        vector_store,
        semantic_weight: float = 0.45,
        structural_weight: float = 0.25,
        recency_weight: float = 0.15,
        diversity_weight: float = 0.15,
        taxonomy_bonus_weight: float = 0.08,
        table_bonus_weight: float = 0.05
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.recency_weight = recency_weight
        self.diversity_weight = diversity_weight

        self.taxonomy_bonus_weight = taxonomy_bonus_weight
        self.table_bonus_weight = table_bonus_weight

    # --------------------------------------------------
    # Recency scoring (equilibrado, no dominante)
    # --------------------------------------------------
    def _compute_recency_score(self, year: int) -> float:
        if not year:
            return 0.5

        current_year = datetime.now().year
        age = current_year - year

        if age <= 1:
            return 1.0
        elif age <= 3:
            return 0.85
        elif age <= 5:
            return 0.7
        elif age <= 8:
            return 0.55
        else:
            return 0.4

    # --------------------------------------------------
    # Structural scoring basado en sección
    # --------------------------------------------------
    def _compute_structural_score(self, section: str) -> float:

        priority_sections = {
            "Methodology": 1.0,
            "Results": 0.9,
            "Discussion": 0.85,
            "Literature Review": 0.8,
            "Introduction": 0.7,
            "Conclusion": 0.75
        }

        return priority_sections.get(section, 0.6)

    # --------------------------------------------------
    # Diversidad simple (penaliza exceso del mismo doc)
    # --------------------------------------------------
    def _compute_diversity_scores(self, results):

        doc_counts = {}
        diversity_scores = []

        for r in results:
            doc_id = r["doc_id"]
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

            if doc_counts[doc_id] == 1:
                diversity_scores.append(1.0)
            elif doc_counts[doc_id] == 2:
                diversity_scores.append(0.8)
            else:
                diversity_scores.append(0.6)

        return diversity_scores

    # --------------------------------------------------
    # Main retrieval
    # --------------------------------------------------
    def search(self, query_embedding, top_k=10):
        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k * 3
        )

        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0]

        results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            semantic_score = 1 / (1 + distance)
            structural_score = metadata.get("structural_weight", 1.0)
            recency_score = metadata.get("recency_score", 1.0)
            taxonomy_bonus = metadata.get("taxonomy_bonus", 0)
            table_bonus = metadata.get("table_bonus", 0)

            results.append({
                "doc_id": metadata.get("doc_id"),
                "title": metadata.get("title"),
                "section": metadata.get("section"),
                "year": metadata.get("year"),
                "semantic_score": semantic_score,
                "structural_score": structural_score,
                "recency_score": recency_score,
                "taxonomy_bonus": taxonomy_bonus,
                "table_bonus": table_bonus,
                "text": doc
            })

        # calcular diversidad y final_score como antes
        diversity_scores = self._compute_diversity_scores(results)
        for i, r in enumerate(results):
            r["diversity_score"] = diversity_scores[i]
            r["final_score"] = (
                self.semantic_weight * r["semantic_score"] +
                self.structural_weight * r["structural_score"] +
                self.recency_weight * r["recency_score"] +
                self.diversity_weight * r["diversity_score"] +
                r["taxonomy_bonus"] +
                r["table_bonus"]
            )

        # ordenar
        ranked = sorted(results, key=lambda x: x["final_score"], reverse=True)
        return ranked[:top_k]

        

    def query(
        self,
        query_text: str,
        n_results: int = 15,
        where_filter: Dict[str, Any] = None,
        recency_bias: bool = True
    ) -> List[Dict]:
        """
        Método principal de retrieval.
        Devuelve lista de chunks rankeados por final_score.
        """
        # 1️⃣ Generar embedding del query
        query_embedding = self.embedder.embed_text(query_text)

        # 2️⃣ Query semántico en Chroma
        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where_filter=where_filter
        )

        # Chroma devuelve listas anidadas
        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0]

        ranked_results = []

        for doc, metadata, distance in zip(documents, metadatas, distances):
            semantic_score = 1 / (1 + distance)
            structural_weight = metadata.get("structural_weight", 1.0)
            recency_weight = metadata.get("recency_score", 1.0)  # si lo tienes

            final_score = (
                0.7 * semantic_score +
                0.2 * structural_weight +
                0.1 * recency_weight
            )

            ranked_results.append({
                "text": doc,
                "metadata": metadata,
                "semantic_score": semantic_score,
                "structural_weight": structural_weight,
                "recency_weight": recency_weight,
                "final_score": final_score
            })

        # Ordenar por final_score
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked_results
