import streamlit as st
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Conexión a la Nube (Datos de tu proyecto Marketplace_Universal)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Monitor Latam Cloud", layout="wide")
st.title("🌍 Monitor Marketplace - Nube")

def cargar_nube():
    # Consultamos la tabla universal que creamos en Supabase
    response = supabase.table("ofertas_universales").select("*").order("fecha_deteccion", desc=True).execute()
    return response.data

try:
    datos = cargar_nube()
    if datos:
        st.metric("Ofertas Sincronizadas", len(datos))
        for oferta in datos:
            with st.expander(f"📦 {oferta['titulo']} - {oferta['precio']}"):
                st.write(f"ID: {oferta['id']}")
                st.link_button("Ir a Marketplace", oferta['url'])
    else:
        st.info("La nube está esperando datos. Ejecuta el bot con el nuevo token.")
except Exception as e:
    st.error(f"Error de conexión: {e}")