import time
import requests
import os
import sqlite3
import urllib.parse
import re # Para limpiar los precios de forma profesional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
USER_KEY = os.getenv("USER_KEY")
API_TOKEN = os.getenv("API_TOKEN")

# --- CONFIGURACIÓN DE NEGOCIO ---
# Añadimos min_price para evitar los precios de fantasía ($1, $123, etc)
PRODUCTOS_A_BUSCAR = [
    {"query": "auto 2016", "min_price": 500000, "max_price": 5000000}, 
    {"query": "ps5", "min_price": 200000, "max_price": 450000},
    {"query": "tarjeta grafica", "min_price": 50000, "max_price": 350000},
    {"query": "ipad", "min_price": 80000, "max_price": 300000},
    {"query": "bicicleta", "min_price": 30000, "max_price": 200000}
]

PALABRAS_NEGATIVAS = ["busco", "permuto", "repuesto", "arreglo", "compro", "bloqueado", "desbloqueo", "condiciones"]

def limpiar_precio(texto_precio):
    """Extrae solo los números de un texto como '$4.500.000' y lo convierte en entero."""
    solo_numeros = re.sub(r'[^\d]', '', texto_precio)
    return int(solo_numeros) if solo_numeros else 0

def inicializar_db():
    conn = sqlite3.connect('marketplace_monitor.db')
    cursor = conn.cursor()
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
    conn.close()

def es_nuevo(id_unico, titulo, precio, precio_num):
    conn = sqlite3.connect('marketplace_monitor.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM ofertas WHERE id = ?', (id_unico,))
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO ofertas (id, titulo, precio, precio_num, fecha_deteccion) 
            VALUES (?, ?, ?, ?, ?)
        ''', (id_unico, titulo, precio, precio_num, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def enviar_push(titulo, precio, url_producto):
    url_api = "https://api.pushover.net/1/messages.json"
    data = {
        "token": API_TOKEN,
        "user": USER_KEY,
        "message": f"💰 Precio: {precio}\n🔍 Producto: {titulo}",
        "title": "🚀 ¡OFERTA REAL DETECTADA!",
        "url": url_producto
    }
    requests.post(url_api, data=data)

def monitorear():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...")
        page = context.new_page()

        for item in PRODUCTOS_A_BUSCAR:
            query = item['query']
            min_p = item['min_price']
            max_p = item['max_price']
            
            query_encoded = urllib.parse.quote(query)
            url = f"https://www.facebook.com/marketplace/116407435040092/search?minPrice={min_p}&maxPrice={max_p}&query={query_encoded}&exact=false"
            
            print(f"[{time.strftime('%H:%M:%S')}] Escaneando: {query} (Rango: ${min_p} - ${max_p})...")
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(6000)
                page.keyboard.press("Escape")
                
                anuncios = page.query_selector_all('a[href*="/marketplace/item/"]')

                for anuncio in anuncios:
                    try:
                        info = anuncio.inner_text().split('\n')
                        href = anuncio.get_attribute('href')
                        link = f"https://www.facebook.com{href}" if href.startswith('/') else href

                        # Identificar precio y título
                        precio_texto = next((l for l in info if "$" in l), "0")
                        precio_numerico = limpiar_precio(precio_texto)
                        
                        titulo = "Sin título"
                        for linea in info:
                            if len(linea) > 8 and "$" not in linea:
                                titulo = linea
                                break

                        # FILTRO 1: ¿Está dentro del rango de precio real?
                        if precio_numerico < min_p or precio_numerico > max_p:
                            continue

                        # FILTRO 2: Palabras negativas
                        if any(neg in titulo.lower() for neg in PALABRAS_NEGATIVAS):
                            continue

                        if es_nuevo(link, titulo, precio_texto, precio_numerico):
                            print(f"✨ ¡OFERTA VALIDADA!: {titulo} por {precio_texto}")
                            enviar_push(titulo.upper(), precio_texto, link)
                    except:
                        continue
            except Exception as e:
                print(f"⚠️ Error en búsqueda: {e}")
        
        browser.close()

if __name__ == "__main__":
    inicializar_db()
    print("🚀 Monitor LATAM v2.2 (Filtro de Precios Fantasía Activo)")
    while True:
        monitorear()
        print("😴 Esperando 5 minutos...")
        time.sleep(300)