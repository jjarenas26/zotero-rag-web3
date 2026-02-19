import requests
from typing import List, Dict


class AcademicQAEngine:
    """
    Motor de QA académico basado en:
    - HybridRetriever
    - Ollama LLM
    """

    def __init__(
        self,
        retriever,
        model_name: str = "llama3",
        base_url: str = "http://localhost:11434"
    ):
        self.retriever = retriever
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    # =====================================================
    # PUBLIC METHOD
    # =====================================================

    def ask(self, question: str, top_k: int = 10) -> Dict:

        # 1️⃣ Retrieval híbrido
        retrieved = self.retriever.query(
            query_text=question,
            n_results=top_k
        )

        # 2️⃣ Seleccionar mejores chunks finales
        selected_chunks = retrieved[:6]

        # 3️⃣ Construir contexto
        context = self._build_context(selected_chunks)

        # 4️⃣ Construir prompt
        prompt = self._build_prompt(question, context)

        # 5️⃣ Llamar a Ollama
        answer = self._generate(prompt)

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "doc_id": c["metadata"]["doc_id"],
                    "section": c["metadata"]["section"],
                    "score": c["final_score"]
                }
                for c in selected_chunks
            ]
        }

    # =====================================================
    # INTERNAL METHODS
    # =====================================================

    def _build_context(self, chunks: List[Dict]) -> str:

        context_blocks = []

        for c in chunks:
            metadata = c["metadata"]

            block = f"""
SOURCE: {metadata['doc_id']}
TITLE: {metadata.get('title')}
SECTION: {metadata.get('section')}
YEAR: {metadata.get('year')}

CONTENT:
{c['text']}
"""
            context_blocks.append(block.strip())

        return "\n\n---\n\n".join(context_blocks)

    def _build_prompt(self, question: str, context: str) -> str:

        return f"""
You are a strict academic research assistant.

You MUST follow these rules:

1. Use ONLY the provided context.
2. If the context does not contain enough evidence, respond:
   "Insufficient evidence in the indexed papers."
3. Every claim MUST include a citation in this format:
   [doc_id - section]
4. Do NOT invent information.
5. Do NOT use prior knowledge.

Write in formal academic tone.

----------------------------
QUESTION:
{question}
----------------------------

CONTEXT:
{context}

----------------------------
ACADEMIC ANSWER:
"""

    def _generate(self, prompt: str) -> str:

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": 600
                }
            }
        )

        if response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()["response"]
