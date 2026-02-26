import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# 1. CONFIGURACIÓN DE RUTAS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipelines.academic_ingestion_pipeline import AcademicIngestionPipeline

# Configuraciones iniciales
st.set_page_config(page_title="Technical Evidence Auditor", layout="wide")

# Inicializar el Pipeline
@st.cache_resource
def get_pipeline():
    return AcademicIngestionPipeline()

pipeline = get_pipeline()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Control de Datos")
    st.write("Carga nuevos archivos a la carpeta `data/raw` y presiona el botón para procesarlos.")
    
    if st.button("🚀 Ejecutar Pipeline de Ingesta"):
        with st.status("Procesando documentos...", expanded=True) as status:
            st.write("Escaneando directorio `data/raw`...")
            # Aquí ejecutamos tu lógica actual
            try:
                pipeline.ingest_collection("data/raw")
                status.update(label="✅ Ingesta Completada!", state="complete", expanded=False)
                st.success("Documentos analizados e indexados en ChromaDB.")
            except Exception as e:
                st.error(f"Error en el pipeline: {e}")
                status.update(label="❌ Fallo en la ingesta", state="error")

# --- CUERPO PRINCIPAL ---
st.title("🔍 Auditor de Evidencia Técnica")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.markdown("### 📊 Radar de Factibilidad")
    # (Tu lógica de Plotly aquí...)

with col2:
    st.markdown("### 🛠️ Pipeline de Procesamiento")
    
    # Listar archivos actuales para mostrar transparencia al CIO
    if os.path.exists("data/raw"):
        files = os.listdir("data/raw")
        files = [f for f in files if f.endswith('.pdf')]
        
        st.write(f"**Archivos en repositorio:** {len(files)}")
        
        # Simulación visual de lo que hace tu pipeline internamente
        with st.expander("Ver flujo de transformación por archivo", expanded=True):
            for file in files[:3]: # Mostramos los primeros 3 para no saturar
                st.markdown(f"**📄 {file}**")
                cols = st.columns(3)
                cols[0].write("✅ Layout Columnas")
                cols[1].write("✅ Split Estructural")
                cols[2].write("✨ Refined (Llama)")
                st.divider()
    else:
        st.warning("No se encontró la carpeta `data/raw`.")

# --- SECCIÓN DE CONSULTA (QA) ---
st.divider()
st.markdown("### 🤖 Consulta de Evidencia (Audit Mode)")
# Aquí integrarías tu qa_engine.ask()