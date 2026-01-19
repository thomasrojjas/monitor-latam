import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os

# Esto inicia tu bot en segundo plano dentro del servidor de Render
if "BOT_RUNNING" not in os.environ:
    os.environ["BOT_RUNNING"] = "1"
    subprocess.Popen(["python", "bot_marketplace.py"])

# Configuración de la página
st.set_page_config(page_title="Monitor Marketplace LATAM", page_icon="🚗", layout="wide")

st.title("📊 Panel de Control - Ofertas Detectadas")
st.markdown("Revisa el historial de capturas de tu bot y filtra las mejores oportunidades.")

# Función para leer la base de datos
def cargar_datos():
    conn = sqlite3.connect('marketplace_monitor.db')
    query = "SELECT fecha_deteccion, titulo, precio, precio_num, id FROM ofertas ORDER BY fecha_deteccion DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Carga de datos
try:
    df = cargar_datos()

    # --- FILTROS EN LA BARRA LATERAL ---
    st.sidebar.header("Filtros")
    busqueda = st.sidebar.text_input("Buscar por nombre (ej: iPhone)")
    precio_max = st.sidebar.slider("Precio Máximo", 0, int(df['precio_num'].max() or 5000000), int(df['precio_num'].max() or 5000000))

    # Aplicar filtros
    df_filtrado = df[df['precio_num'] <= precio_max]
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado['titulo'].str.contains(busqueda, case=False)]

    # --- MÉTRICAS RÁPIDAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Detectados", len(df))
    col2.metric("Encontrados Hoy", len(df[df['fecha_deteccion'].str.contains(pd.Timestamp.now().strftime('%Y-%m-%d'))]))
    col3.metric("Precio Promedio", f"${int(df_filtrado['precio_num'].mean() or 0):,}")

    # --- TABLA DE DATOS ---
    st.subheader("Listado de Oportunidades")
    
    # Formateamos la tabla para que sea más bonita
    df_mostrar = df_filtrado.copy()
    df_mostrar.columns = ['Fecha', 'Producto', 'Precio Texto', 'Precio ($)', 'Enlace']
    
    # Mostramos la tabla interactiva
    st.dataframe(
        df_mostrar,
        column_config={
            "Enlace": st.column_config.LinkColumn("Link a Facebook"),
            "Precio ($)": st.column_config.NumberColumn(format="$%d")
        },
        hide_index=True,
        use_container_width=True
    )

except Exception as e:
    st.error(f"Aún no hay datos suficientes en la base de datos. Ejecuta el bot primero. Error: {e}")