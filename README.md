# Monitor Latam

Bot de monitoreo de Facebook Marketplace + dashboard en Streamlit.

## Configuración rápida
1. Copia variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Ejecuta bot:
   ```bash
   python bot_marketplace.py
   ```
4. Ejecuta dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## Variables importantes
- `SEARCH_TERMS`: búsquedas separadas por comas.
- `SCAN_INTERVAL_SECONDS`: intervalo entre rondas.
- `MAX_ITEMS_PER_SCAN`: máximo de resultados guardados por búsqueda.
- `ADMIN_PASSWORD`: clave de acceso al dashboard.
- `ALLOW_INSECURE_ADMIN_FALLBACK`: solo local; usa `1234` si no existe `ADMIN_PASSWORD`.

## Commit desde VS Code
1. Abre **Source Control**.
2. Escribe un mensaje en **Message** (obligatorio).
3. Haz clic en **Commit** (✓).
4. Haz clic en **Sync Changes** o **Push** para subir a GitHub.
