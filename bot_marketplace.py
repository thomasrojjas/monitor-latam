import os
import time
import sqlite3
import requests
import re
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
LOG_FILE = os.path.join(BASE_DIR, 'bot_log.txt')

def log(mensaje):
    timestamp = time.strftime("%H:%M:%S")
    texto = f"[{timestamp}] {mensaje}"
    print(texto, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

# --- VARIABLES DE ENTORNO (Configurar en Render) ---
USER_KEY = os.getenv("USER_KEY")
API_TOKEN = os.getenv("API_TOKEN")

PRODUCTO = "bicicleta"
URL_BUSQUEDA = f"https://www.facebook.com/marketplace/search/?query={PRODUCTO}"

def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ofertas 
                      (id TEXT PRIMARY KEY, titulo TEXT, precio TEXT, 
                       precio_num INTEGER, fecha_deteccion DATETIME)''')
    conn.commit()
    conn.close()

def enviar_notificacion(titulo, precio, url_item):
    if not USER_KEY or not API_TOKEN: return
    payload = {
        "token": API_TOKEN, "user": USER_KEY,
        "message": f"💰 {precio}\n📦 {titulo}",
        "title": "✨ ¡OFERTA DETECTADA!",
        "url": url_item
    }
    try: requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
    except: pass

def ejecutar_escaneo():
    log(f"🔎 Iniciando escaneo de {PRODUCTO}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            page.goto(URL_BUSQUEDA, wait_until="domcontentloaded", timeout=90000)
            time.sleep(10)
            
            log("📜 Realizando scroll progresivo para cargar datos...")
            for _ in range(4):
                page.mouse.wheel(0, 800)
                time.sleep(3)
            
            # Extracción por Regex de IDs de Marketplace
            html_content = page.content()
            items_encontrados = re.findall(r'item/(\d{10,})', html_content)
            items_unicos = list(set(items_encontrados))
            
            log(f"📊 IDs detectados: {len(items_unicos)}")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for item_id in items_unicos[:10]:
                url_completa = f"https://www.facebook.com/marketplace/item/{item_id}/"
                try:
                    cursor.execute("INSERT INTO ofertas VALUES (?,?,?,?,?)", 
                                 (item_id, f"Bicicleta {item_id}", "Ver en Link", 0, time.strftime('%Y-%m-%d %H:%M:%S')))
                    conn.commit()
                    log(f"✅ NUEVO: {item_id}")
                    enviar_notificacion(f"Bicicleta Detectada", f"ID: {item_id}", url_completa)
                except sqlite3.IntegrityError: pass 
            conn.close()
                
        except Exception as e: log(f"⚠️ Error: {e}")
        finally:
            browser.close()
            log("😴 Fin de ronda.")

if __name__ == "__main__":
    inicializar_db()
    log("🚀 BOT ONLINE")
    while True:
        ejecutar_escaneo()
        time.sleep(300)