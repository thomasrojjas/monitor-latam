import os
import random
import re
import sqlite3
import time
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "marketplace_monitor.db")
LOG_FILE = os.path.join(BASE_DIR, "bot_log.txt")

DEFAULT_PROXIES = [
    "142.111.48.253:7030",
    "23.95.150.145:6114",
    "198.23.239.134:6540",
    "107.172.163.27:6543",
    "198.105.121.200:6462",
    "64.137.96.74:6641",
    "84.247.60.125:6095",
    "216.10.27.159:6837",
    "23.26.71.145:5628",
    "23.27.208.120:5830",
]


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def log(mensaje: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    texto = f"[{timestamp}] {mensaje}"
    print(texto, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(texto + "\n")
    except OSError as exc:
        print(f"[{timestamp}] ⚠️ No se pudo escribir log: {exc}", flush=True)


def parse_int_env(var_name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(var_name, str(default)).strip()
    try:
        parsed = int(value)
        if parsed < minimum:
            raise ValueError
        return parsed
    except ValueError:
        log(f"⚠️ Valor inválido para {var_name}='{value}'. Se usa {default}.")
        return default


def parse_csv_env(var_name: str, default_csv: str) -> List[str]:
    raw = os.getenv(var_name, default_csv)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if values:
        return values
    fallback = [item.strip() for item in default_csv.split(",") if item.strip()]
    log(f"⚠️ {var_name} vacío. Se usará valor por defecto: {fallback}")
    return fallback


SEARCH_TERMS = parse_csv_env("SEARCH_TERMS", "bicicleta")
SCAN_INTERVAL_SECONDS = parse_int_env("SCAN_INTERVAL_SECONDS", default=300)
MAX_ITEMS_PER_SCAN = parse_int_env("MAX_ITEMS_PER_SCAN", default=10)
PROXIES_WEBSHARE = parse_csv_env("PROXIES_WEBSHARE", ",".join(DEFAULT_PROXIES))

PROXY_AUTH = {
    "user": os.getenv("PROXY_USER"),
    "pass": os.getenv("PROXY_PASS"),
}


def get_proxy_config() -> Optional[dict]:
    if not PROXIES_WEBSHARE:
        return None
    server = random.choice(PROXIES_WEBSHARE)
    proxy = {"server": f"http://{server}"}
    if PROXY_AUTH["user"] and PROXY_AUTH["pass"]:
        proxy["username"] = PROXY_AUTH["user"]
        proxy["password"] = PROXY_AUTH["pass"]
    return proxy


def inicializar_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ofertas (
            id TEXT PRIMARY KEY,
            titulo TEXT,
            precio TEXT,
            precio_num INTEGER,
            fecha_deteccion DATETIME,
            search_term TEXT,
            url TEXT
        )
        """
    )

    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(ofertas)").fetchall()}
    if "search_term" not in existing_columns:
        cursor.execute("ALTER TABLE ofertas ADD COLUMN search_term TEXT")
    if "url" not in existing_columns:
        cursor.execute("ALTER TABLE ofertas ADD COLUMN url TEXT")

    conn.commit()
    conn.close()


def build_search_url(search_term: str) -> str:
    return f"https://www.facebook.com/marketplace/search/?query={quote_plus(search_term)}"


def extraer_ids(html_content: str) -> Sequence[str]:
    return sorted(set(re.findall(r"item/(\d{10,})", html_content)))


def guardar_items(search_term: str, item_ids: Iterable[str]) -> int:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    payload: List[Tuple[str, str, str, int, str, str, str]] = []

    for item_id in item_ids:
        listing_url = f"https://www.facebook.com/marketplace/item/{item_id}"
        payload.append(
            (
                item_id,
                f"{search_term.title()} {item_id}",
                "Ver Link",
                0,
                timestamp,
                search_term,
                listing_url,
            )
        )

    if not payload:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0

    for row in payload:
        try:
            cursor.execute(
                """
                INSERT INTO ofertas (id, titulo, precio, precio_num, fecha_deteccion, search_term, url)
                VALUES (?,?,?,?,?,?,?)
                """,
                row,
            )
            inserted += 1
        except sqlite3.IntegrityError:
            continue

    conn.commit()
    conn.close()
    return inserted


def ejecutar_escaneo(search_term: str) -> None:
    search_url = build_search_url(search_term)
    proxy = get_proxy_config()
    proxy_label = proxy["server"] if proxy else "sin proxy"
    log(f"🔎 Escaneo iniciado [{search_term}] con {proxy_label}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, proxy=proxy)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        stealth_sync(page)

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=120000)
            log(f"🌐 [{search_term}] Contenido recibido. Procesando...")
            time.sleep(15)
            page.mouse.wheel(0, 1500)
            time.sleep(5)

            ids = extraer_ids(page.content())
            log(f"📊 [{search_term}] IDs detectados: {len(ids)}")
            nuevos = guardar_items(search_term, ids[:MAX_ITEMS_PER_SCAN])
            log(f"✅ [{search_term}] Nuevos registros: {nuevos}")
        except Exception as exc:
            log(f"⚠️ [{search_term}] Error en ronda: {exc}")
        finally:
            context.close()
            browser.close()
            log(f"😴 [{search_term}] Fin de ronda.")


def main() -> None:
    inicializar_db()
    log(f"🚀 BOT ACTIVADO | búsquedas={SEARCH_TERMS} | intervalo={SCAN_INTERVAL_SECONDS}s")

    while True:
        for term in SEARCH_TERMS:
            try:
                ejecutar_escaneo(term)
            except Exception as exc:
                log(f"❌ Error inesperado en término '{term}': {exc}")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
