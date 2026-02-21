import sys
import os
import json
import re
import requests
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# 1. CONFIGURACIÓN DE RUTAS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from embedding.ollama_embedder import OllamaEmbedder
from vectorstore.chroma_vector_store import ChromaVectorStore
from retrieval.hybrid_retriever import HybridRetriever

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Blockchain Research Advisor", layout="wide", page_icon="📚")

# --- INICIALIZACIÓN DE COMPONENTES ---
@st.cache_resource
def init_retriever():
    try:
        embedder = OllamaEmbedder(model="nomic-embed-text")
        vector_store = ChromaVectorStore()
        return HybridRetriever(embedder, vector_store)
    except Exception as e:
        st.error(f"Error de inicialización: {e}")
        return None

retriever = init_retriever()

# --- FUNCIONES DE UTILIDAD ---
def load_questions(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = f.read().strip()
    match = re.search(r'\[.*\]', raw_data, re.DOTALL)
    if match: raw_data = match.group()
    try:
        data = json.loads(raw_data)
        return data.get("questions", data) if isinstance(data, dict) else data
    except: return None

def draw_radar(stats):
    categories = list(stats.keys())
    values = list(stats.values())
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]; angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color='#1f77b4', alpha=0.3)
    ax.plot(angles, values, color='#1f77b4', linewidth=2, marker='o')
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), categories)
    ax.set_ylim(0, 100)
    return fig

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Consultor Blockchain Basado en Evidencia")
st.markdown("### Framework de Factibilidad con Respaldo Bibliográfico de Zotero")

questions = load_questions("assessment_questions.json")

if not questions:
    st.warning("⚠️ Cuestionario no detectado. Ejecuta el script 7a primero.")
else:
    with st.form("evaluation_form"):
        st.subheader("📋 Evaluación de Criterios Científicos")
        user_responses = {}
        cols = st.columns(2)
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                with cols[i % 2]:
                    pillar = q.get('pillar', 'General')
                    user_responses[i] = st.radio(f"**{pillar}**: {q.get('question_es')}", ["No", "Sí"], key=f"q_{i}")
        submitted = st.form_submit_button("Analizar y Generar Referencias")

    if submitted:
        # Cálculo de puntajes
        pillar_scores = {}; pillar_totals = {}
        for i, q in enumerate(questions):
            if not isinstance(q, dict): continue
            p = q['pillar']; w = q.get('weight', 10)
            pillar_scores[p] = pillar_scores.get(p, 0)
            pillar_totals[p] = pillar_totals.get(p, 0) + w
            if user_responses[i] == "Sí": pillar_scores[p] += w

        stats = {p: (pillar_scores[p]/pillar_totals[p])*100 for p in pillar_scores}
        
        # Resultados Visuales
        st.divider()
        col_r, col_metrics = st.columns([1, 1]) # Corregido: col_metrics definido aquí
        with col_r: 
            st.pyplot(draw_radar(stats))
        with col_metrics: # Corregido: col_metrics usado aquí
            st.subheader("Resultados por Dimensión")
            for p, s in stats.items(): 
                st.progress(s/100, text=f"{p}: {s:.0f}%")
            
            avg_score = sum(stats.values()) / len(stats) if stats else 0
            st.metric("Puntaje Global de Factibilidad", f"{avg_score:.1f}%")

        # --- SECCIÓN DE EVIDENCIA CON CITAS FORMALES ---
        st.header("📚 Evidencia Científica de Respaldo")
        
        for pilar in stats.keys():
            with st.expander(f"📖 Referencias Bibliográficas para: {pilar}"):
                if retriever:
                    docs = retriever.search2(query_text=f"critical requirements for blockchain {pilar}", n_results=2)
                    for d in docs:
                        m = d['metadata']
                        st.markdown(f"**Cita:** {m.get('author', 'N.N.')} ({m.get('year', 's.f.')}). *{m.get('title')}*.")
                        st.info(f"“...{d['text'][:550]}...”")
                        st.caption(f"Ubicación en PDF: {m.get('section', 'Desconocida')}")
                        st.markdown("---")

# --- AGENTE DE CHAT CON CITAS DINÁMICAS ---
st.divider()
st.header("💬 Agente de Refinamiento Bibliográfico")
if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Pregunta sobre un paper específico o criterio técnico..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.spinner("Consultando biblioteca de Zotero..."):
        if retriever:
            context_docs = retriever.search2(query_text=prompt, n_results=3)
            context = ""
            for d in context_docs:
                m = d['metadata']
                context += f"\n[DOCUMENTO: {m.get('title')} | AUTOR: {m.get('author')} | AÑO: {m.get('year')}]\nCONTENIDO: {d['text']}\n"
            
            sys_prompt = f"""Eres un Asistente de Investigación Senior. 
            Responde en ESPAÑOL. Debes citar explícitamente el autor y año de los documentos proporcionados en tu respuesta.
            Contexto científico:\n{context}"""
            
            try:
                res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3.1", "prompt": f"{sys_prompt}\n\nPregunta: {prompt}", "stream": False},
                    timeout=90
                )
                answer = res.json().get("response", "Error en generación.")
            except: answer = "Error de conexión con Ollama."
            
            with st.chat_message("assistant"): st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})