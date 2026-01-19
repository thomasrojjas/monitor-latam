import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os
import sys
import time

# --- CONFIGURACIÓN DE RUTAS ABSOLUTAS ---
# Esto ayuda a que Render no se pierda entre carpetas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
BOT_PATH = os.path.join(BASE_DIR, 'bot_marketplace.py')
LOG_PATH = os.path.join(BASE_DIR, 'bot_log.txt')

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor Marketplace Pro", page_icon="🚀", layout="wide")

# --- FUNCIÓN PARA VER LOGS DEL BOT ---
def leer_logs():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            return f.readlines()[-15:] # Muestra las últimas 15 líneas
    return ["Esperando inicio del bot..."]

# --- AUTO-INSTALACIÓN Y ARRANQUE ---
if "BOT_STARTED" not in st.session_state:
    st.session_state["BOT_STARTED"] = True
    
    # 1. Intentar instalar Chromium si falta
    if "RENDER" in os.environ:
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        except:
            pass
            
    # 2. Despertar al bot en segundo plano
    try:
        # Usamos -u para que los logs sean inmediatos
        subprocess.Popen([sys.executable, "-u", BOT_PATH], 
                         stdout=open(LOG_PATH, 'a'), 
                         stderr=st.empty())
        st.toast("✅ Proceso del bot iniciado")
    except Exception as e:
        st.error(f"Error al iniciar bot: {e}")

# --- INTERFAZ DEL DASHBOARD ---
st.title("📊 Panel de Control - Monitor Marketplace")

# --- MÓDULO DE DEPURACIÓN (LOGS EN VIVO) ---
with st.expander("🛠️ Ver Logs del Servidor (Debugging)"):
    logs = leer_logs()
    for line in logs:
        st.text(line.strip())
    if st.button("Limpiar Logs"):
        if os.path.exists(LOG_PATH): os.remove(LOG_PATH)

# --- GESTIÓN DE DATOS ---
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ofertas (
            id TEXT PRIMARY KEY, titulo TEXT, precio TEXT, 
            precio_num INTEGER, fecha_deteccion DATETIME
        )
    ''')
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
c2.metric("Nuevos Hoy", len(df[df['fecha_deteccion'].str.contains(time.strftime("%Y-%m-%d"))]) if not df.empty else 0)
c3.metric("Estado del Bot", "🟢 Online" if "BOT_STARTED" in st.session_state else "🔴 Offline")

# --- TABLA ---
st.subheader("📋 Últimas Oportunidades")
if df.empty:
    st.info("Buscando ofertas... Revisa los logs arriba para ver el progreso del escáner.")
else:
    st.dataframe(df, use_container_width=True)

if st.button("🔄 Sincronizar"):
    st.rerun()