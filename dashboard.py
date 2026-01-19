import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os
import sys

# --- CONFIGURACIÓN PARA RENDER (AUTO-INSTALACIÓN) ---
def asegurar_navegador():
    # Solo intentamos instalar si estamos en el entorno de Render
    if "RENDER" in os.environ or "/opt/render" in os.getcwd():
        try:
            # Verificamos si ya intentamos instalar en esta sesión para no repetir
            if "browser_installed" not in st.session_state:
                st.info("Configurando entorno del bot en la nube... (Esto ocurre solo una vez)")
                # Forzamos la instalación de Chromium
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                st.session_state["browser_installed"] = True
        except Exception as e:
            st.error(f"Error instalando navegador en la nube: {e}")

# Ejecutamos la verificación
asegurar_navegador()

# --- INICIO DEL BOT EN SEGUNDO PLANO ---
if "BOT_RUNNING" not in st.session_state:
    st.session_state["BOT_RUNNING"] = True
    try:
        # Iniciamos el bot de marketplace
        subprocess.Popen([sys.executable, "bot_marketplace.py"])
    except Exception as e:
        st.error(f"No se pudo iniciar el bot: {e}")

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Monitor Marketplace v2.5", page_icon="🚀", layout="wide")

# Estilo personalizado para el Dashboard
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Panel de Control - Monitor Marketplace")
st.markdown("Plataforma de monitoreo en tiempo real para revendedores profesionales.")

# --- GESTIÓN DE BASE DE DATOS ---
def cargar_datos():
    conn = sqlite3.connect('marketplace_monitor.db')
    cursor = conn.cursor()
    
    # Aseguramos que la tabla exista siempre
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ofertas (
            id TEXT PRIMARY KEY,
            titulo TEXT,
            precio TEXT,
            precio_num INTEGER,
            fecha_deteccion DATETIME
        )
    ''')
    conn.commit()
    
    try:
        query = "SELECT fecha_deteccion, titulo, precio, precio_num, id FROM ofertas ORDER BY fecha_deteccion DESC"
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame(columns=['fecha_deteccion', 'titulo', 'precio', 'precio_num', 'id'])
    
    conn.close()
    return df

# Carga de datos
df = cargar_datos()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("⚙️ Configuración y Filtros")
busqueda = st.sidebar.text_input("Filtrar por nombre:", placeholder="Ej: auto, iphone...")

# Calcular precio máximo de forma dinámica
if not df.empty and pd.notnull(df['precio_num'].max()):
    max_slider = int(df['precio_num'].max())
else:
    max_slider = 5000000

precio_max = st.sidebar.slider("Presupuesto Máximo ($)", 0, max_slider, max_slider)

# Aplicar lógica de filtros
df_filtrado = df.copy()
if not df.empty:
    df_filtrado = df_filtrado[df_filtrado['precio_num'] <= precio_max]
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado['titulo'].str.contains(busqueda, case=False)]

# --- DASHBOARD DE MÉTRICAS ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📦 Total Detectados", len(df))

with col2:
    hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
    encontrados_hoy = len(df[df['fecha_deteccion'].str.contains(hoy)]) if not df.empty else 0
    st.metric("✨ Encontrados Hoy", encontrados_hoy)

with col3:
    if not df_filtrado.empty:
        promedio = int(df_filtrado['precio_num'].mean())
    else:
        promedio = 0
    st.metric("💰 Precio Promedio", f"${promedio:,}")

st.divider()

# --- TABLA DE RESULTADOS ---
st.subheader("📋 Listado de Ofertas Activas")

if df_filtrado.empty:
    st.warning("No se han encontrado ofertas aún. El bot está escaneando Marketplace en este momento...")
else:
    # Formatear el DataFrame para la vista del usuario
    df_vista = df_filtrado.copy()
    df_vista.columns = ['Fecha Captura', 'Producto', 'Precio (Texto)', 'Precio Numérico', 'URL Marketplace']
    
    st.dataframe(
        df_vista,
        column_config={
            "URL Marketplace": st.column_config.LinkColumn("Abrir en Facebook 🔗"),
            "Precio Numérico": st.column_config.NumberColumn(format="$%d"),
            "Fecha Captura": st.column_config.TextColumn(width="medium")
        },
        hide_index=True,
        use_container_width=True
    )

# --- BOTÓN DE ACTUALIZACIÓN ---
if st.button("🔄 Refrescar Panel"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Bot operando 24/7 en la nube.")