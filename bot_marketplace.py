import os
import sys
import time
import sqlite3
import requests
import re
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
    try:
        requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
    except: pass

def ejecutar_escaneo():
    log(f"🔎 Escaneo por patrones iniciado para: {PRODUCTO}...")
    
    with sync_playwright() as p:
        # Lanzamiento estándar sin carpetas persistentes para evitar errores en Render
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            # 1. Carga de página
            page.goto(URL_BUSQUEDA, wait_until="domcontentloaded", timeout=90000)
            time.sleep(10) # Tiempo para que cargue el contenido dinámico
            
            # 2. Scroll para activar carga de más contenido
            page.mouse.wheel(0, 2000)
            time.sleep(5)
            
            # 3. EXTRACCIÓN POR PATRONES (REGEX)
            # Buscamos IDs de 15 o más dígitos que Facebook usa para sus items
            html_content = page.content()
            items_encontrados = re.findall(r'/marketplace/item/(\d{10,})/', html_content)
            items_unicos = list(set(items_encontrados))
            
            log(f"📊 IDs detectados en el código: {len(items_unicos)}")

            for item_id in items_unicos[:10]:
                url_completa = f"https://www.facebook.com/marketplace/item/{item_id}/"
                
                # Intentamos guardar en la base de datos
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                try:
                    # Como no tenemos el título aún, ponemos un genérico o el ID
                    cursor.execute("INSERT INTO ofertas VALUES (?,?,?,?,?)", 
                                 (item_id, f"Oferta {item_id}", "Ver Link", 0, time.strftime('%Y-%m-%d %H:%M:%S')))
                    conn.commit()
                    log(f"✅ ¡NUEVO ID!: {item_id}")
                    enviar_notificacion(f"Bicicleta Detectada ({item_id})", "Revisar en FB", url_completa)
                except sqlite3.IntegrityError:
                    pass # Ya existe
                finally:
                    conn.close()
                
        except Exception as e:
            log(f"⚠️ Error en ronda: {e}")
        finally:
            browser.close()
            log("😴 Ronda terminada. Esperando 5 minutos.")

if __name__ == "__main__":
    inicializar_db()
    log("🚀 BOT ONLINE - Modo Patrones")
    while True:
        ejecutar_escaneo()
        time.sleep(300)