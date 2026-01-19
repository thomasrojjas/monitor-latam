import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os

# --- CONFIGURACIÓN DE INICIO PARA RENDER ---
# Esto asegura que el bot de escaneo se ejecute en segundo plano junto con el Dashboard
if "BOT_RUNNING" not in st.session_state:
    st.session_state["BOT_RUNNING"] = True
    try:
        # Iniciamos el proceso del bot de manera independiente
        subprocess.Popen(["python", "bot_marketplace.py"])
    except Exception as e:
        st.error(f"No se pudo iniciar el bot en segundo plano: {e}")

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Monitor Marketplace LATAM", page_icon="🚗", layout="wide")

st.title("📊 Panel de Control - Ofertas Detectadas")
st.markdown("Revisa el historial de capturas de tu bot y filtra las mejores oportunidades.")

# --- FUNCIÓN PARA LEER LA BASE DE DATOS ---
def cargar_datos():
    conn = sqlite3.connect('marketplace_monitor.db')
    cursor = conn.cursor()
    
    # PROTECCIÓN: Crea la tabla si no existe (evita el error 'no such table')
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
    except Exception as e:
        st.error(f"Error al leer los datos: {e}")
        df = pd.DataFrame(columns=['fecha_deteccion', 'titulo', 'precio', 'precio_num', 'id'])
    
    conn.close()
    return df

# --- CARGA Y FILTRADO ---
df = cargar_datos()

# Sidebar para filtros
st.sidebar.header("Filtros de Búsqueda")
busqueda = st.sidebar.text_input("Buscar por nombre (ej: iPhone, Suzuki)")

# Determinamos el precio máximo para el slider de forma segura
max_p_actual = int(df['precio_num'].max()) if not df.empty and pd.notnull(df['precio_num'].max()) else 5000000
precio_max = st.sidebar.slider("Precio Máximo", 0, max_p_actual, max_p_actual)

# Aplicar filtros al DataFrame
df_filtrado = df.copy()
if not df.empty:
    df_filtrado = df_filtrado[df_filtrado['precio_num'] <= precio_max]
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado['titulo'].str.contains(busqueda, case=False)]

# --- MÉTRICAS RÁPIDAS ---
col1, col2, col3 = st.columns(3)

# Total Histórico
total_detectados = len(df)
col1.metric("Total Detectados", total_detectados)

# Hallazgos de Hoy
hoy_str = pd.Timestamp.now().strftime('%Y-%m-%d')
hoy_detectados = len(df[df['fecha_deteccion'].str.contains(hoy_str)]) if not df.empty else 0
col2.metric("Encontrados Hoy", hoy_detectados)

# Precio Promedio (con protección contra NaN)
if not df_filtrado.empty:
    promedio = int(df_filtrado['precio_num'].mean())
else:
    promedio = 0
col3.metric("Precio Promedio", f"${promedio:,}")

# --- LISTADO DE OPORTUNIDADES ---
st.subheader("Listado de Oportunidades")

if df_filtrado.empty:
    st.info("Aún no hay ofertas registradas que coincidan con los filtros. El bot está trabajando...")
else:
    # Formateamos para mostrar
    df_display = df_filtrado.copy()
    df_display.columns = ['Fecha', 'Producto', 'Precio Texto', 'Precio ($)', 'Link a Facebook']
    
    st.dataframe(
        df_display,
        column_config={
            "Link a Facebook": st.column_config.LinkColumn("Ver en Marketplace"),
            "Precio ($)": st.column_config.NumberColumn(format="$%d")
        },
        hide_index=True,
        use_container_width=True
    )

# Botón manual para refrescar datos
if st.button("🔄 Actualizar Datos"):
    st.rerun()