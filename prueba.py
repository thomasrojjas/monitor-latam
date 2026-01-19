from playwright.sync_api import sync_playwright

def ejecutar_prueba():
    with sync_playwright() as p:
        # headless=False permite que veas la ventana del navegador
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Abriendo Google para probar el bot...")
        page.goto("https://www.google.com")
        
        # Esperamos 3 segundos para que veas que cargó
        page.wait_for_timeout(3000)
        
        print("Título de la página:", page.title())
        print("¡Prueba exitosa! El navegador se cerrará en breve.")
        
        browser.close()

if __name__ == "__main__":
    ejecutar_prueba()