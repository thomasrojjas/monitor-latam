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
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            # 1. Navegar con un timeout extendido y espera de red
            log("🌐 Cargando Marketplace...")
            page.goto(URL_BUSQUEDA, wait_until="domcontentloaded", timeout=90000)
            
            # 2. ESPERA ACTIVA: En lugar de un selector fijo, esperamos cualquier contenido
            # Hacemos scroll lento para imitar a un humano leyendo
            log("📜 Realizando scroll humano...")
            for i in range(5):
                page.mouse.wheel(0, 600)
                time.sleep(3) # Pausa para que Facebook cargue
            
            # 3. SELECTOR DE EMERGENCIA: Buscamos cualquier enlace que parezca producto
            # Si no aparece el '/item/', buscamos por estructura de Grid
            page.wait_for_load_state("networkidle")
            
            # Buscamos todos los links de la página
            all_links = page.query_selector_all('a')
            items = [l for l in all_links if l.get_attribute('href') and '/item/' in l.get_attribute('href')]
            
            if not items:
                log("⚠️ No se detectaron enlaces con '/item/'. Intentando captura directa de texto...")
                # Fallback: capturar cualquier cosa que tenga signo de peso
                items = page.query_selector_all('div[role="main"] div[style*="max-width"]')

            log(f"📊 {len(items)} potenciales ofertas detectadas.")

            for item in items[:15]:
                try:
                    text_content = item.inner_text()
                    if "$" not in text_content: continue
                    
                    info = text_content.split('\n')
                    precio_str = next((t for t in info if "$" in t), None)
                    nombre = next((t for t in info if len(t) > 4 and "$" not in t), "Producto")
                    
                    href = item.get_attribute('href')
                    if href and precio_str:
                        # Limpiar URL de parámetros de seguimiento
                        clean_url = f"https://www.facebook.com{href.split('?')[0]}" if href.startswith('/') else href.split('?')[0]
                        item_id = clean_url.strip('/').split('/')[-1]
                        
                        precio_int = int(''.join(filter(str.isdigit, precio_str)))
                        
                        if guardar_oferta(item_id, nombre, precio_str, precio_int):
                            log(f"✅ ¡NUEVO!: {nombre} ({precio_str})")
                            enviar_notificacion(nombre, precio_str, clean_url)
                except: continue
                
        except Exception as e:
            log(f"⚠️ Error de visibilidad: {e}")
        finally:
            browser.close()
            log("😴 Ronda terminada.")

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