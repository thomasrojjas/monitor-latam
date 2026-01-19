import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os
import sys

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
BOT_PATH = os.path.join(BASE_DIR, 'bot_marketplace.py')
LOG_PATH = os.path.join(BASE_DIR, 'bot_log.txt')

st.set_page_config(page_title="Monitor Marketplace Pro", page_icon="🚀", layout="wide")

# --- FUNCIÓN PARA VER LOGS ---
def leer_logs():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, 'r') as f:
                return f.readlines()[-15:]
        except: return ["Error leyendo el archivo de logs."]
    return ["Esperando inicio del bot..."]

# --- ARRANQUE SEGURO DEL BOT ---
if "BOT_STARTED" not in st.session_state:
    st.session_state["BOT_STARTED"] = True
    
    # Instalación silenciosa de navegador si estamos en Render
    if "RENDER" in os.environ:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True)

    # Iniciar bot sin redirección de stdout compleja (evita error fileno)
    try:
        subprocess.Popen([sys.executable, "-u", BOT_PATH])
        st.toast("✅ Proceso del bot iniciado")
    except Exception as e:
        st.error(f"Error al iniciar bot: {e}")

# --- INTERFAZ ---
st.title("📊 Panel de Control - Monitor Marketplace")

with st.expander("🛠️ Ver Logs del Servidor (Debugging)"):
    logs = leer_logs()
    for line in logs:
        st.text(line.strip())

# --- GESTIÓN DE DATOS ---
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ofertas 
                      (id TEXT PRIMARY KEY, titulo TEXT, precio TEXT, 
                       precio_num INTEGER, fecha_deteccion DATETIME)''')
    conn.commit()
    try:
        df = pd.read_sql_query("SELECT * FROM ofertas ORDER BY fecha_deteccion DESC", conn)
    except:
        df = pd.DataFrame(columns=['id', 'titulo', 'precio', 'precio_num', 'fecha_deteccion'])
    conn.close()
    return df

df = cargar_datos()

# --- MÉTRICAS ---
c1, c2, c3 = st.columns(3)
c1.metric("Total Capturado", len(df))
c2.metric("Estado del Bot", "🟢 Online")
c3.metric("DB Path", "Local (Render)")

st.subheader("📋 Últimas Oportunidades")
if df.empty:
    st.info("Buscando ofertas... Revisa los logs de Render para el progreso.")
else:
    st.dataframe(df, use_container_width=True)

if st.button("🔄 Sincronizar"):
    st.rerun()