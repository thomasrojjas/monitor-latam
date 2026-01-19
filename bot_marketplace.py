import os
import sys
import time
import sqlite3
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- CONFIGURACIÓN DE RUTAS ABSOLUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'marketplace_monitor.db')
LOG_FILE = os.path.join(BASE_DIR, 'bot_log.txt')

# --- SISTEMA DE LOGS ---
def log(mensaje):
    timestamp = time.strftime("%H:%M:%S")
    texto = f"[{timestamp}] {mensaje}"
    print(texto, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except Exception as e:
        print(f"Error escribiendo log: {e}")

# --- VARIABLES DE ENTORNO ---
USER_KEY = os.getenv("USER_KEY")
API_TOKEN = os.getenv("API_TOKEN")

# --- PARÁMETROS DE BÚSQUEDA ---
PRODUCTO = "bicicleta"
PRECIO_MIN = 30000
PRECIO_MAX = 200000
URL_BUSQUEDA = f"https://www.facebook.com/marketplace/category/search?query={PRODUCTO}&minPrice={PRECIO_MIN}&maxPrice={PRECIO_MAX}&exact=false"

# --- BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ofertas (id, titulo, precio, precio_num, fecha_deteccion)
            VALUES (?, ?, ?, ?, ?)
        ''', (id_item, titulo, precio, precio_num, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False 
    finally:
        conn.close()

# --- NOTIFICACIONES ---
def enviar_notificacion(titulo, precio, url_item):
    if not USER_KEY or not API_TOKEN:
        log("⚠️ Llaves de Pushover no configuradas.")
        return
    
    payload = {
        "token": API_TOKEN,
        "user": USER_KEY,
        "message": f"💰 {precio}\n📦 {titulo}",
        "title": "✨ ¡OFERTA DETECTADA!",
        "url": url_item,
        "url_title": "Ver en Marketplace"
    }
    try:
        requests.post("https://api.pushover.net/1/messages.json", data=payload)
        log(f"🔔 Notificación enviada: {titulo}")
    except Exception as e:
        log(f"❌ Error Pushover: {e}")

# --- SCRAPER CON MEJORA DE SELECTORES ---
def ejecutar_escaneo():
    log(f"🔎 Escaneando: {PRODUCTO}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Añadimos un viewport más grande para ver más productos
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            # 1. Navegar con tiempo de espera generoso
            page.goto(URL_BUSQUEDA, wait_until="networkidle", timeout=90000)
            
            # 2. Scroll progresivo para forzar la carga de imágenes y textos
            log("📜 Realizando scroll progresivo...")
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(2)
            
            # 3. Selector Genérico: Buscamos enlaces que contienen la palabra 'item'
            # Es mucho más estable que buscar por estilos de ancho (max-width)
            selector_oferta = 'a[href*="/item/"]'
            page.wait_for_selector(selector_oferta, timeout=45000)
            
            items = page.query_selector_all(selector_oferta)
            log(f"📊 {len(items)} enlaces de productos encontrados.")

            for item in items[:15]:
                try:
                    # Buscamos el texto dentro del contenedor del enlace
                    info = item.inner_text().split('\n')
                    if len(info) < 2: continue
                    
                    # Intentamos identificar el precio buscando el símbolo "$"
                    precio_str = next((t for t in info if "$" in t), None)
                    # El nombre suele ser el texto más largo o el que no tiene "$"
                    nombre = next((t for t in info if len(t) > 5 and "$" not in t), info[1])
                    
                    if not precio_str: continue
                    
                    precio_int = int(''.join(filter(str.isdigit, precio_str)))
                    
                    href = item.get_attribute('href')
                    if href:
                        clean_url = f"https://www.facebook.com{href.split('?')[0]}"
                        item_id = clean_url.split('/')[-2]
                        
                        if guardar_oferta(item_id, nombre, precio_str, precio_int):
                            log(f"✅ ¡NUEVO!: {nombre} ({precio_str})")
                            enviar_notificacion(nombre, precio_str, clean_url)
                except: continue
                
        except Exception as e:
            log(f"⚠️ No se detectaron productos en esta ronda: {e}")
        finally:
            browser.close()
            log("😴 Fin de ronda. Esperando 5 minutos...")

# --- BUCLE PRINCIPAL ---
if __name__ == "__main__":
    inicializar_db()
    log("🚀 BOT ACTIVADO")
    while True:
        try:
            ejecutar_escaneo()
        except Exception as e:
            log(f"❌ Error crítico: {e}")
        time.sleep(300)