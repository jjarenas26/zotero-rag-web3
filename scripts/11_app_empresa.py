import sys
import os
import json
import re
import requests
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

# # --- CONFIGURACIÓN DE RUTAS E IMPORTACIONES ---
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# try:
#     from embedding.ollama_embedder import OllamaEmbedder
#     from vectorstore.chroma_vector_store import ChromaVectorStore
#     from retrieval.hybrid_retriever import HybridRetriever
# except ImportError:
#     st.error("No se encontraron los módulos de RAG. Asegúrate de que las rutas son correctas.")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Blockchain Research Advisor", layout="wide", page_icon="🛡️")

# --- LÓGICA DE BASE DE DATOS ---
def get_all_companies():
    """Obtiene la lista de empresas únicas registradas."""
    conn = sqlite3.connect('consultoria_blockchain.db')
    c = conn.cursor()
    try:
        c.execute("SELECT DISTINCT empresa FROM clientes ORDER BY empresa ASC")
        companies = [row[0] for row in c.fetchall()]
    except:
        companies = []
    finally:
        conn.close()
    return companies

def check_user_access(email, empresa):
    conn = sqlite3.connect('consultoria_blockchain.db')
    c = conn.cursor()
    c.execute("SELECT nombre FROM clientes WHERE email = ? AND empresa = ?", (email, empresa))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_evaluation(email, stats):
    conn = sqlite3.connect('consultoria_blockchain.db')
    c = conn.cursor()
    c.execute("SELECT id FROM clientes WHERE email = ?", (email,))
    user_id = c.fetchone()[0]
    c.execute("INSERT INTO evaluaciones (cliente_id, scores_json, fecha) VALUES (?, ?, ?)",
              (user_id, json.dumps(stats), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- INICIALIZACIÓN DE COMPONENTES RAG ---
@st.cache_resource
# def init_retriever():
#     try:
#         embedder = OllamaEmbedder(model="nomic-embed-text")
#         vector_store = ChromaVectorStore()
#         return HybridRetriever(embedder, vector_store)
#     except:
#         return None

# retriever = init_retriever()

# --- UTILIDADES ---
def load_questions(file_path):
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
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

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'user' not in st.session_state:
    st.session_state.user = None

# --- FLUJO DE INTERFAZ ---
if not st.session_state.auth:
    # --- PANTALLA DE VALIDACIÓN ---
    st.title("🛡️ Consultor Blockchain: Acceso Cliente")
    st.markdown("Identifíquese con sus credenciales corporativas para acceder al Framework.")

    # Obtener empresas de la BD
    lista_empresas = get_all_companies()
    
    with st.form("login_form"):
        email_input = st.text_input("Correo Electrónico")
        #empresa_input = st.text_input("Empresa")
        empresa_sel = st.selectbox("Seleccione su Empresa", lista_empresas)
        if st.form_submit_button("Validar y Entrar"):
            nombre = check_user_access(email_input, empresa_sel)
            if nombre:
                st.session_state.auth = True
                st.session_state.user = {"nombre": nombre, "email": email_input, "empresa": empresa_sel}
                st.rerun()
            else:
                st.error("Acceso denegado. Sus credenciales no están en nuestra lista de clientes.")

else:
    # --- PANTALLA PRINCIPAL ---
    st.sidebar.success(f"Sesión activa: {st.session_state.user['nombre']}")
    if st.sidebar.button("Salir"):
        st.session_state.auth = False
        st.rerun()

    st.title("📋 Cuestionario de Factibilidad Técnica")
    questions = load_questions("assessment_questions.json")

    if not questions:
        st.warning("No se encontró el archivo de preguntas (assessment_questions.json).")
    else:
        with st.form("evaluation_form"):
            user_responses = {}
            cols = st.columns(2)
            for i, q in enumerate(questions):
                with cols[i % 2]:
                    p = q.get('pillar', 'Criterio')
                    user_responses[i] = st.radio(f"**{p}**: {q.get('question_es')}", ["No", "Sí"], key=f"q_{i}")
            
            submitted = st.form_submit_button("Analizar Factibilidad")

        if submitted:
            # Cálculo de resultados
            pillar_scores = {}; pillar_totals = {}
            for i, q in enumerate(questions):
                p = q['pillar']; w = q.get('weight', 10)
                pillar_scores[p] = pillar_scores.get(p, 0)
                pillar_totals[p] = pillar_totals.get(p, 0) + w
                if user_responses[i] == "Sí": pillar_scores[p] += w

            stats = {p: (pillar_scores[p]/pillar_totals[p])*100 for p in pillar_scores}
            
            # Guardar resultados en BD
            save_evaluation(st.session_state.user['email'], stats)

            # Visualización
            st.divider()
            c1, c2 = st.columns([1, 1])
            with c1:
                st.pyplot(draw_radar(stats))
            with c2:
                st.subheader("Puntajes por Dimensión")
                for p, s in stats.items():
                    st.progress(s/100, text=f"{p}: {s:.0f}%")
                avg = sum(stats.values())/len(stats)
                st.metric("Puntaje Global", f"{avg:.1f}%")

            # Referencias Bibliográficas (RAG)
            st.header("📚 Respaldo Bibliográfico Personalizado")
            # for pilar in stats.keys():
            #     with st.expander(f"Evidencia para: {pilar}"):
            #         if retriever:
            #             docs = retriever.search2(query_text=f"blockchain {pilar} architecture requirements", n_results=2)
            #             for d in docs:
            #                 m = d['metadata']
            #                 st.markdown(f"**{m.get('author')} ({m.get('year')})** - *{m.get('title')}*")
            #                 st.caption(f"Referencia: {d['text'][:300]}...")
            #                 st.markdown("---")