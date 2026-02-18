import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Monitor Latam", page_icon="🚲", layout="centered")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ALLOW_INSECURE_ADMIN_FALLBACK = os.getenv("ALLOW_INSECURE_ADMIN_FALLBACK", "false").lower() == "true"

st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; }
    [data-testid="stMetricValue"] { color: #00FFAA; font-size: 2.5rem; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not ADMIN_PASSWORD and ALLOW_INSECURE_ADMIN_FALLBACK:
    ADMIN_PASSWORD = "1234"
    st.sidebar.warning("Modo inseguro activo: usa ADMIN_PASSWORD en .env para producción.")

user_pass = st.sidebar.text_input("Ingresa la clave", type="password")

if not ADMIN_PASSWORD:
    st.error("Define ADMIN_PASSWORD en tu .env para habilitar el panel.")
    st.code("ADMIN_PASSWORD=tu_clave_segura")
    st.stop()

if user_pass != ADMIN_PASSWORD:
    st.title("🔐 Acceso Privado")
    st.warning("Introduce la contraseña en el menú lateral para ver las ofertas.")
    st.stop()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "marketplace_monitor.db")
LOG_FILE = os.path.join(BASE_DIR, "bot_log.txt")

st.title("🚲 Monitor Marketplace")
st.write("Estado: 🟢 Operando")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ofertas ORDER BY fecha_deteccion DESC", conn)
    conn.close()

    c1, c2 = st.columns(2)
    c1.metric("Total Detectado", len(df))
    hoy = datetime.now().strftime("%Y-%m-%d")
    nuevas = len(df[df["fecha_deteccion"].str.contains(hoy)]) if not df.empty else 0
    c2.metric("Nuevas Hoy", nuevas)

    st.subheader("📋 Últimos Hallazgos")
    if not df.empty:
        default_columns = ["id", "search_term", "fecha_deteccion", "url"]
        columns = [column for column in default_columns if column in df.columns]
        st.dataframe(df[columns], use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos nuevos aún.")
else:
    st.error("Esperando la primera ejecución exitosa del bot...")

with st.expander("📄 Ver Logs del Sistema"):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as file:
            st.text(file.read()[-1500:])

if st.button("🔄 Actualizar Datos"):
    st.rerun()
