import streamlit as st
import sqlite3
import pandas as pd
import os

# --- CONFIGURACIÓN DE SEGURIDAD ---
ADMIN_PASSWORD = "TU_CONTRASEÑA_AQUI"  # <--- CAMBIA ESTO

st.set_page_config(page_title="Marketplace Monitor Pro", layout="wide")

# Barra lateral de seguridad
st.sidebar.title("🔐 Acceso Privado")
user_pass = st.sidebar.text_input("Ingresa la clave", type="password")

if user_pass != ADMIN_PASSWORD:
    st.warning("🔒 Por favor, ingresa la contraseña en la barra lateral para acceder.")
    st.stop()

# --- SI LA CLAVE ES CORRECTA, SE MUESTRA EL RESTO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
LOG_FILE = os.path.join(BASE_DIR, 'bot_log.txt')

st.title("🚲 Monitor de Ofertas en Tiempo Real")

# Sección de Logs
with st.expander("📄 Ver Logs del Servidor"):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            st.text(f.read()[-2000:]) # Muestra los últimos 2000 caracteres

# Sección de Datos
st.subheader("📦 Últimas Ofertas Detectadas")
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ofertas ORDER BY fecha_deteccion DESC", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aún no hay ofertas en la base de datos.")
else:
    st.error("Base de datos no encontrada.")

if st.button("🔄 Actualizar Datos"):
    st.rerun()