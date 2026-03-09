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

# --- FUNCIONES DE INTELIGENCIA ESTRATÉGICA ---

def display_intel_card(m):
    """Muestra la metadata de TRL y contradicciones de forma visual."""
    trl = m.get('trl', 0)
    color = "green" if trl >= 7 else "orange" if trl >= 4 else "red"
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"<h3 style='color:{color};'>TRL {trl}</h3>", unsafe_allow_html=True)
        st.caption(f"_{m.get('trl_justification', 'Sin justificación')}_")
    with col2:
        st.markdown("**⚠️ Contradicciones/Riesgos:**")
        cons = m.get('contradictions', "").split('|')
        for c in cons:
            if c: st.markdown(f"- <span style='font-size:0.85rem;'>{c}</span>", unsafe_allow_html=True)

def get_dynamic_tradeoffs(pilar, phase1_answers, questions_ref):
    """
    Generates strategic dilemmas with a robust JSON repair logic.
    """
    user_requirements = []
    for i, ans in phase1_answers.items():
        q_data = questions_ref[i]
        if ans == "Sí" and q_data.get('pillar') == pilar:
            user_requirements.append(q_data.get('question_es'))

    query = f"technical trade-offs and constraints in {pilar}"
    docs = retriever.search3(query_text=query, n_results=3)
    
    evidence_context = ""
    for d in docs:
        m = d['metadata']
        evidence_context += f"- Paper: {m.get('title')} | Constraints: {m.get('contradictions')}\n"

    # Reforzamos el prompt para pedir que no use comillas internas problemáticas
    prompt = f"""
    [ROLE: SENIOR ARCHITECTURE AUDITOR]
    BUSINESS CONTEXT: {user_requirements}
    EVIDENCE: {evidence_context}

    TASK:
    Generate 2 trade-off questions (Scale 1-5). 
    IMPORTANT: Ensure the JSON is perfectly formatted. Use ONLY single quotes for internal text if needed.
    
    STRICT JSON FORMAT:
    [
      {{
        "question": "Text",
        "low_label": "Text",
        "high_label": "Text",
        "evidence": "Text"
      }}
    ]
    """
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1} # Bajamos la temperatura para más estabilidad
            },
            timeout=120
        )
        
        raw_output = response.json().get("response", "[]")
        
        # --- MOTOR DE REPARACIÓN DE JSON ---
        # 1. Eliminar bloques de código markdown
        clean_json = re.sub(r'```json\s*|```', '', raw_output).strip()
        
        # 2. Extraer solo lo que está entre los primeros [ y últimos ]
        # Esto ignora cualquier texto conversacional que la IA haya puesto fuera del JSON
        start_idx = clean_json.find('[')
        end_idx = clean_json.rfind(']')
        
        if start_idx != -1 and end_idx != -1:
            clean_json = clean_json[start_idx:end_idx + 1]
        
        # 3. Intentar corregir comas faltantes (patrón común: } { -> }, {)
        clean_json = re.sub(r'\}\s*\{', '}, {', clean_json)

        data = json.loads(clean_json)
        return data, docs

    except Exception as e:
        st.error(f"⚠️ Error de formato en la IA: {e}")
        # FALLBACK: Si falla, devolvemos una pregunta genérica para no romper la app
        fallback_q = [{
            "question": f"¿Cómo prioriza la escalabilidad frente a la seguridad en {pilar}?",
            "low_label": "Priorizo Seguridad",
            "high_label": "Priorizo Escalabilidad",
            "evidence": "Trade-off estándar detectado en arquitectura blockchain."
        }]
        return fallback_q, []

def render_strategic_roadmap(user_answers, docs_context, initial_stats):
    """
    Synthesizes the final strategic roadmap by crossing business priorities 
    with scientific maturity (TRL) and technical constraints.
    """
    st.divider()
    st.header("🚀 Hoja de Ruta Estratégica Personalizada")
    
    evidence_str = ""
    for d in docs_context:
        m = d['metadata']
        evidence_str += f"- Paper: {m.get('title')} | TRL: {m.get('trl')} | Constraints: {m.get('contradictions')}\n"

    prompt = f"""
    [ROLE: SENIOR STRATEGIC TECHNOLOGY CONSULTANT]
    TASK: Generate a professional 3-phase Roadmap (Q1-Q2, Q3-Q4, Year 2) for Blockchain adoption.
    
    INPUT DATA:
    - Phase 1 Feasibility Scores: {initial_stats}
    - Phase 2 Strategic Trade-offs (Scale 1-5): {user_answers}
    - Scientific Evidence & TRL: {evidence_str}
    
    STRICT STRATEGIC RULES:
    1. If average TRL < 5: Phase 1 focus on 'Academic Validation'.
    2. Link recommendations to specific constraints in evidence.
    3. Use professional executive Spanish.
    """
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1", "prompt": prompt, "stream": False},
            timeout=180
        )
        roadmap_md = response.json().get("response", "Error al generar el roadmap.")
        
        col_main, col_side = st.columns([3, 1])
        with col_main:
            st.markdown(roadmap_md)
        with col_side:
            st.info("🧬 **Resumen de Auditoría**")
            trls = [float(d['metadata'].get('trl', 0)) for d in docs_context]
            avg_trl = sum(trls) / len(trls) if trls else 0
            st.metric("TRL Promedio", f"Nivel {avg_trl:.1f}")
            st.warning("⚠️ **Riesgos Críticos**")
            for d in docs_context[:2]:
                st.write(f"• {d['metadata'].get('contradictions', '').split('|')[0]}")
    except Exception as e:
        st.error(f"Error en la síntesis: {e}")

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
st.title("🛡️ Blockchain Strategic Advisor")
st.markdown("### Framework de Factibilidad y Adopción Basado en Evidencia")

# Manejo de estados
if "phase2_unlocked" not in st.session_state: st.session_state.phase2_unlocked = False
if "stats" not in st.session_state: st.session_state.stats = {}

questions = load_questions("assessment_questions.json")

if not questions:
    st.warning("⚠️ Cuestionario no detectado.")
else:
    with st.form("evaluation_form"):
        st.subheader("📋 Fase 1: Evaluación de Factibilidad")
        user_responses = {}
        cols = st.columns(2)
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                with cols[i % 2]:
                    pillar = q.get('pillar', 'General')
                    user_responses[i] = st.radio(f"**{pillar}**: {q.get('question_es')}", ["No", "Sí"], key=f"q_{i}")
        submitted = st.form_submit_button("Calcular Factibilidad")

    if submitted:
        # NUEVO: Guardamos las respuestas Sí/No para usarlas como contexto
        st.session_state.phase1_answers = user_responses 
        # También guardamos la definición de las preguntas para saber qué significa cada "Sí"
        st.session_state.questions_ref = questions
        pillar_scores = {}; pillar_totals = {}
        for i, q in enumerate(questions):
            p = q['pillar']; w = q.get('weight', 10)
            pillar_scores[p] = pillar_scores.get(p, 0)
            pillar_totals[p] = pillar_totals.get(p, 0) + w
            if user_responses[i] == "Sí": pillar_scores[p] += w

        st.session_state.stats = {p: (pillar_scores[p]/pillar_totals[p])*100 for p in pillar_scores}
        avg_score = sum(st.session_state.stats.values()) / len(st.session_state.stats)
        
        st.divider()
        col_r, col_metrics = st.columns([1, 1])
        with col_r: st.pyplot(draw_radar(st.session_state.stats))
        with col_metrics:
            st.subheader("Puntaje Global")
            st.metric("Factibilidad", f"{avg_score:.1f}%")
            if avg_score >= 80:
                st.success("🎯 ¡Umbral superado! Fase de Estrategia desbloqueada.")
                st.session_state.phase2_unlocked = True
            else:
                st.error("⚠️ Factibilidad insuficiente para un Roadmap seguro.")

        # --- SECCIÓN DE EVIDENCIA CON METADATA ---
        st.header("📚 Inteligencia Bibliográfica (Zotero)")
        for pilar in st.session_state.stats.keys():
            with st.expander(f"📖 Evidencia para {pilar}"):
                docs = retriever.search3(query_text=f"blockchain {pilar} requirements", n_results=2)
                for d in docs:
                    m = d['metadata']
                    st.markdown(f"**{m.get('title')}** ({m.get('author')}, {m.get('year')})")
                    display_intel_card(m)
                    st.info(f"“...{d['text'][:400]}...”")
                    st.markdown("---")

# --- DENTRO DEL BLOQUE FASE 2 ---
if st.session_state.phase2_unlocked:
    st.divider()
    st.header("🎯 Fase 2: Análisis de Compromisos (Trade-offs)")
    
    # Para no regenerar preguntas cada vez que Streamlit refresca, las guardamos en session_state
    if "current_tradeoffs" not in st.session_state:
        crit_p = sorted(st.session_state.stats, key=st.session_state.stats.get)[:2]
        all_qs = []
        all_docs = []
        for p in crit_p:
            qs, docs = get_dynamic_tradeoffs(
                p, 
                st.session_state.phase1_answers, # <--- MEMORIA DE RESPUESTAS
                st.session_state.questions_ref   # <--- MEMORIA DE DEFINICIONES
            )
            if isinstance(qs, list):
                all_qs.extend(qs)
            if isinstance(docs, list):
                all_docs.extend(docs)
        st.session_state.current_tradeoffs = all_qs
        st.session_state.current_docs = all_docs

    # --- RENDERIZADO CON VALIDACIÓN ---
    with st.form("tradeoff_form"):
        user_strategy_responses = {}
        
        # Validamos que tengamos una lista antes de iterar
        if st.session_state.current_tradeoffs:
            for i, q in enumerate(st.session_state.current_tradeoffs):
                # DOBLE CHEQUEO: Si por alguna razón q es un string, lo saltamos para evitar el crash
                if not isinstance(q, dict):
                    continue
                
                st.markdown(f"**{q.get('question', 'Pregunta no disponible')}**")
                st.caption(f"🔬 *Evidencia:* {q.get('evidence', 'No hay evidencia disponible')}")
                
                user_strategy_responses[i] = st.select_slider(
                    "Tu posición:", 
                    options=[1, 2, 3, 4, 5], 
                    help=f"1: {q.get('low_label', 'Mínimo')} | 5: {q.get('high_label', 'Máximo')}",
                    key=f"slider_{i}"
                )
        else:
            st.warning("No se pudieron generar preguntas de trade-off basadas en la literatura.")
        
        generate_roadmap = st.form_submit_button("🚀 Generar Roadmap Estratégico Final")
    if generate_roadmap:
        st.balloons()
        # AQUÍ ES DONDE SUCEDE LA MAGIA
        render_strategic_roadmap(
            user_strategy_responses, 
            st.session_state.current_docs, 
            st.session_state.stats
        )


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
            context_docs = retriever.search3(query_text=prompt, n_results=3)
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