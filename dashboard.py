import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN APP ---
st.set_page_config(page_title="Monitor Latam", page_icon="🚲", layout="centered")

# --- SEGURIDAD ---
ADMIN_PASSWORD = "1234" # Cambia esto por tu clave preferida

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    [data-testid="stMetricValue"] { color: #00FFAA; font-size: 2.5rem; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Login simple
user_pass = st.sidebar.text_input("Ingresa la clave", type="password")

if user_pass != ADMIN_PASSWORD:
    st.title("🔐 Acceso Privado")
    st.warning("Introduce la contraseña en el menú lateral para ver las ofertas.")
    st.stop()

# --- PANEL DE DATOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
LOG_FILE = os.path.join(BASE_DIR, 'bot_log.txt')

st.title("🚲 Monitor Marketplace")
st.write("Estado: 🟢 Operando con Proxies Residenciales")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ofertas ORDER BY fecha_deteccion DESC", conn)
    conn.close()

    c1, c2 = st.columns(2)
    c1.metric("Total Detectado", len(df))
    hoy = datetime.now().strftime('%Y-%m-%d')
    nuevas = len(df[df['fecha_deteccion'].str.contains(hoy)]) if not df.empty else 0
    c2.metric("Nuevas Hoy", nuevas)

    st.subheader("📋 Últimos Hallazgos")
    if not df.empty:
        st.dataframe(df[['id', 'fecha_deteccion']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos nuevos aún.")
else:
    st.error("Esperando la primera ejecución exitosa del bot...")

with st.expander("📄 Ver Logs del Sistema"):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            st.text(f.read()[-1500:])

if st.button("🔄 Actualizar Datos"):
    st.rerun()