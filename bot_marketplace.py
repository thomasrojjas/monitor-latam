import os
import sys
import time
import sqlite3
import requests
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- CONFIGURACIÓN DE RUTAS ---
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

# --- VARIABLES DE ENTORNO ---
USER_KEY = os.getenv("USER_KEY")
API_TOKEN = os.getenv("API_TOKEN")

# --- PARÁMETROS ---
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
    requests.post("https://api.pushover.net/1/messages.json", data=payload)

def ejecutar_escaneo():
    log(f"🔎 Iniciando escaneo profundo de {PRODUCTO}...")
    
    with sync_playwright() as p:
        # Usamos un contexto persistente para engañar a Facebook
        user_data_dir = os.path.join(BASE_DIR, "user_data")
        browser = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = browser.pages[0]
        stealth_sync(page)
        
        try:
            page.goto(URL_BUSQUEDA, wait_until="networkidle", timeout=90000)
            
            # Simulación de lectura humana
            for _ in range(3):
                page.mouse.wheel(0, random.randint(700, 1000))
                time.sleep(random.uniform(3, 5))
            
            # Captura de emergencia para ver qué ve el bot (revisa esto en tu Dashboard si falla)
            page.screenshot(path=os.path.join(BASE_DIR, "debug.png"))

            # Buscamos todos los enlaces que contienen ofertas
            enlaces = page.query_selector_all('a[href*="/item/"]')
            log(f"📊 Se detectaron {len(enlaces)} posibles ofertas.")

            for link in enlaces[:12]:
                try:
                    texto_completo = link.inner_text()
                    if "$" not in texto_completo: continue
                    
                    lineas = texto_completo.split('\n')
                    precio_str = next((l for l in lineas if "$" in l), "Consultar")
                    titulo = next((l for l in lineas if len(l) > 5 and "$" not in l), "Producto")
                    
                    href = link.get_attribute('href')
                    url_limpia = f"https://www.facebook.com{href.split('?')[0]}"
                    item_id = url_limpia.strip('/').split('/')[-1]
                    
                    precio_int = int(''.join(filter(str.isdigit, precio_str)))
                    
                    # Guardar en DB
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO ofertas VALUES (?,?,?,?,?)", 
                                     (item_id, titulo, precio_str, precio_int, time.strftime('%Y-%m-%d %H:%M:%S')))
                        conn.commit()
                        log(f"✅ NUEVO: {titulo} - {precio_str}")
                        enviar_notificacion(titulo, precio_str, url_limpia)
                    except: pass
                    finally: conn.close()
                except: continue
                
        except Exception as e:
            log(f"⚠️ Error en esta ronda: {e}")
        finally:
            browser.close()
            log("😴 Esperando 5 minutos para la próxima ronda.")

if __name__ == "__main__":
    inicializar_db()
    log("🚀 BOT ONLINE")
    while True:
        ejecutar_escaneo()
        time.sleep(300)