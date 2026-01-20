import os
import time
import sqlite3
import requests
import re
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
LOG_FILE = os.path.join(BASE_DIR, 'bot_log.txt')

# --- CONFIGURACIÓN DE PROXIES (Webshare) ---
PROXIES_WEBSHARE = [
    "142.111.48.253:7030", "23.95.150.145:6114", "198.23.239.134:6540",
    "107.172.163.27:6543", "198.105.121.200:6462", "64.137.96.74:6641",
    "84.247.60.125:6095", "216.10.27.159:6837", "23.26.71.145:5628",
    "23.27.208.120:5830"
]
# Credenciales leídas desde el .env con valores de respaldo (fallback)
PROXY_AUTH = {
    "user": os.getenv("PROXY_USER", "agfizjph"),
    "pass": os.getenv("PROXY_PASS", "y375ph2ovvo2")
}

def log(mensaje):
    timestamp = time.strftime("%H:%M:%S")
    texto = f"[{timestamp}] {mensaje}"
    print(texto, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

# --- VARIABLES DE ENTORNO (Pushover) ---
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

def ejecutar_escaneo():
    proxy_elegido = random.choice(PROXIES_WEBSHARE)
    log(f"🔎 Escaneo iniciado con Proxy: {proxy_elegido}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{proxy_elegido}",
                "username": PROXY_AUTH["user"],
                "password": PROXY_AUTH["pass"]
            }
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            page.goto(URL_BUSQUEDA, wait_until="domcontentloaded", timeout=120000)
            log("🌐 Contenido recibido. Procesando...")
            time.sleep(15) 
            
            page.mouse.wheel(0, 1500)
            time.sleep(5)
            
            html_content = page.content()
            items_encontrados = re.findall(r'item/(\d{10,})', html_content)
            items_unicos = list(set(items_encontrados))
            
            log(f"📊 IDs detectados: {len(items_unicos)}")

            if len(items_unicos) > 0:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for item_id in items_unicos[:10]:
                    try:
                        cursor.execute("INSERT INTO ofertas VALUES (?,?,?,?,?)", 
                                     (item_id, f"Bicicleta {item_id}", "Ver Link", 0, time.strftime('%Y-%m-%d %H:%M:%S')))
                        conn.commit()
                        log(f"✅ REGISTRADO: {item_id}")
                    except sqlite3.IntegrityError: pass 
                conn.close()
                
        except Exception as e:
            log(f"⚠️ Error en ronda: {e}")
        finally:
            browser.close()
            log("😴 Fin de ronda.")

if __name__ == "__main__":
    inicializar_db()
    log("🚀 BOT ACTIVADO")
    while True:
        ejecutar_escaneo()
        time.sleep(300)