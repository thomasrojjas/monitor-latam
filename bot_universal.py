import os
import time
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client

# 1. Cargar configuración desde el .env
load_dotenv()
apify_client = ApifyClient(os.getenv("APIFY_TOKEN"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def ejecutar_escaneo(ciudad, producto):
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔎 Buscando {producto} en {ciudad}...")
    
    # Construcción dinámica de la URL para filtrar por tu ciudad
    url_dinamica = f"https://www.facebook.com/marketplace/{ciudad}/search?query={producto}"
    
    run_input = {
        "startUrls": [{ "url": url_dinamica }],
        "maxResultsPerQuery": 10, # Limite moderado para ahorrar crédito
        "onlyNewListings": True
    }

    try:
        # Ejecución del Actor en la nube de Apify
        run = apify_client.actor("apify/facebook-marketplace-scraper").call(run_input=run_input)
        
        nuevos = 0
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            item_id = str(item.get("id"))
            data = {
                "id": item_id,
                "titulo": item.get("title") or "Sin título",
                "precio": str(item.get("price", "0")),
                "url": f"https://www.facebook.com/marketplace/item/{item_id}",
                "estado": "activo"
            }
            # Sincronización con la Base de Datos Universal (Supabase)
            supabase.table("ofertas_universales").upsert(data).execute()
            print(f"✅ NUBE: {data['titulo'][:30]}... | {data['precio']}")
            nuevos += 1
        
        print(f"📊 Ronda terminada: {nuevos} items procesados.")

    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    print("--- MONITOR LATAM: CONFIGURACIÓN DINÁMICA ---")
    # Preguntamos al usuario para no dejar ubicaciones fijas
    user_ciudad = input("1. Escribe tu ciudad (ej: santiago, concepcion): ").lower().strip()
    user_producto = input("2. ¿Qué producto quieres monitorear?: ").lower().strip()
    
    while True:
        ejecutar_escaneo(user_ciudad, user_producto)
        print(f"😴 Esperando 20 minutos para el siguiente escaneo...")
        time.sleep(1200) # Espera de 20 min para cuidar los $5 USD