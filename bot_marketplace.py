import os
import sys
import time
import sqlite3
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import requests

# --- CONFIGURACIÓN DE REDIRECCIÓN DE LOGS PARA RENDER ---
# Esto permite que el Dashboard lea lo que el bot está haciendo
sys.stdout = open("bot_log.txt", "a", buffering=1)
sys.stderr = sys.stdout

def log(mensaje):
    """Imprime un mensaje con timestamp y fuerza la escritura en el archivo"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {mensaje}", flush=True)

# --- VARIABLES DE ENTORNO (CONFIGURADAS EN RENDER) ---
USER_KEY = os.getenv("USER_KEY")
API_TOKEN = os.getenv("API_TOKEN")

# --- CONFIGURACIÓN DE BÚSQUEDA ---
PRODUCTO = "bicicleta" # Puedes cambiarlo o hacerlo dinámico luego
PRECIO_MIN = 30000
PRECIO_MAX = 200000
URL_BUSQUEDA = f"https://www.facebook.com/marketplace/category/search?query={PRODUCTO}&minPrice={PRECIO_MIN}&maxPrice={PRECIO_MAX}&exact=false"

# --- FUNCIONES DEL SISTEMA ---
def enviar_pushover(titulo, precio, url_item):
    if not USER_KEY or not API_TOKEN:
        log("⚠️ Error: No se configuraron las llaves de Pushover.")
        return
    
    mensaje = f"💰 {precio}\n📦 {titulo}"
    data = {
        "token": API_TOKEN,
        "user": USER_KEY,
        "message": mensaje,
        "title": "✨ ¡OFERTA DETECTADA!",
        "url": url_item,
        "url_title": "Ver en Marketplace"
    }
    try:
        requests.post("https://api.pushover.net/1/messages.json", data=data)
        log(f"🔔 Notificación enviada: {titulo}")
    except Exception as e:
        log(f"❌ Error al enviar notificación: {e}")

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

def guardar_oferta(id_item, titulo, precio, precio_num):
    conn = sqlite3.connect('marketplace_monitor.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ofertas (id, titulo, precio, precio_num, fecha_deteccion)
            VALUES (?, ?, ?, ?, ?)
        ''', (id_item, titulo, precio, precio_num, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Ya existe
    finally:
        conn.close()

# --- LÓGICA PRINCIPAL DEL SCRAPER ---
def escanear():
    log(f"🚀 Iniciando escaneo de: {PRODUCTO} (Rango: ${PRECIO_MIN} - ${PRECIO_MAX})")
    
    with sync_playwright() as p:
        # Usamos chromium ya instalado en Render
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        stealth_sync(page)
        
        try:
            page.goto(URL_BUSQUEDA, wait_until="networkidle", timeout=60000)
            # Esperamos a que carguen los contenedores de productos
            page.wait_for_selector('div[style*="max-width: 381px"]', timeout=20000)
            
            # Capturamos todos los elementos que parecen ofertas
            ofertas = page.query_selector_all('div[style*="max-width: 381px"]')
            log(f"🔎 Se encontraron {len(ofertas)} elementos en la página.")

            for oferta in ofertas[:15]: # Revisamos las 15 primeras para no saturar
                try:
                    texto = oferta.inner_text().split('\n')
                    if len(texto) >= 2:
                        precio_raw = texto[0]
                        titulo = texto[1]
                        
                        # Limpiar precio para SQL
                        precio_num = int(''.join(filter(str.isdigit, precio_raw)))
                        
                        # Obtener Link
                        link_elem = oferta.query_selector('a')
                        if link_elem:
                            href = link_elem.get_attribute('href')
                            url_completa = f"https://www.facebook.com{href.split('?')[0]}"
                            id_item = url_completa.split('/')[-2]
                            
                            # Intentar guardar y notificar
                            if guardar_oferta(id_item, titulo, precio_raw, precio_num):
                                log(f"✨ ¡NUEVA OFERTA!: {titulo} por {precio_raw}")
                                enviar_pushover(titulo, precio_raw, url_completa)
                except:
                    continue
        except Exception as e:
            log(f"⚠️ Error durante el escaneo: {e}")
        finally:
            browser.close()
            log("😴 Escaneo finalizado. Esperando 5 minutos...")

# --- EJECUCIÓN CONTINUA ---
if __name__ == "__main__":
    inicializar_db()
    while True:
        try:
            escanear()
        except Exception as e:
            log(f"❌ Error crítico en el bucle: {e}")
        time.sleep(300) # Pausa de 5 minutos