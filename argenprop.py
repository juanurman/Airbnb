import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re 

# ===================================================================
# --- CONFIGURACIÓN ETAPA 1 (BÚSQUEDA) ---
# ===================================================================
URL_BUSQUEDA = "https://www.argenprop.com/departamentos/alquiler/belgrano-o-colegiales-o-nunez-o-palermo-o-puerto-madero-o-recoleta"
TIEMPO_MAX_ESPERA = 20      
SELECTOR_TARJETA_LISTADO = ("class", "listing__item")
SELECTOR_LINK_TARJETA = ("class", "card") 

# ===================================================================
# --- CONFIGURACIÓN ETAPA 2 (SELECTORES DE DETALLE) ---
# ===================================================================
SELECTOR_TITULO_DETALLE = ("class", "section-description--title")
SELECTOR_PRECIO_DETALLE = ("class", "titlebar__price")
SELECTOR_EXPENSAS_DETALLE = ("class", "titlebar__expenses") 
SELECTOR_UBICACION_DETALLE = ("class", "titlebar__address")
SELECTOR_CARACTERISTICAS_UL = ("class", "property-main-features")

# Mapeo de los 'title' que me pasaste a nombres de columna
MAPEO_CARACTERISTICAS = {
    'Sup. cubierta': 'M2 cubierta',
    'Dormitorios': 'Dormitorios',
    'Antiguedad': 'Antiguedad',
    'Baños': 'Baños',
    'Ambientes': 'Ambientes',
    'Estado': 'Estado'
}

# ===================================================================
# --- Lógica de Extracción (Etapa 2) ---
# ===================================================================

def get_data_by_selector(soup, tipo, selector):
    try:
        tag = None
        if tipo == "class":
            tag = soup.find(class_=lambda c: c and selector in c)
        
        if tag:
            if selector == SELECTOR_EXPENSAS_DETALLE[1]:
                return tag.get_text(strip=True).split(' ')[0]
            if selector == SELECTOR_PRECIO_DETALLE[1]:
                return tag.get_text(separator=' ', strip=True) 
            return tag.get_text(strip=True)
        return "No disponible"
    except Exception: return "Error"

def get_caracteristicas(soup, tipo, selector_ul):
    data = {}
    try:
        container = None
        if tipo == "class":
            container = soup.find('ul', class_=selector_ul)
        if not container:
            print("  Advertencia: No se encontró el <ul> 'property-main-features'")
            return data 

        items = container.find_all('li', title=True) 
        for li in items:
            titulo_li = li['title'].strip()
            if titulo_li in MAPEO_CARACTERISTICAS:
                valor_tag = li.find('p', class_='strong')
                valor_final = "No disponible"
                if valor_tag:
                    texto_completo = valor_tag.get_text(strip=True) 
                    match = re.search(r'([\d\.]+)', texto_completo) 
                    if match:
                        valor_final = match.group(1) 
                    else:
                        valor_final = texto_completo.strip()
                nombre_columna = MAPEO_CARACTERISTICAS[titulo_li]
                data[nombre_columna] = valor_final
        return data
    except Exception as e:
        print(f"  Error en get_caracteristicas: {e}")
        return data

# ===================================================================
# --- FUNCIÓN PRINCIPAL DEL SCRIPT ---
# ===================================================================

def main():
    print("Iniciando Scraper de Argenprop...")
    try:
        driver = webdriver.Chrome()
    except Exception as e:
        print("Error iniciando Selenium. Asegúrate de tener chromedriver instalado.")
        print(f"Error: {e}")
        return

    links_de_propiedades = []
    
    # --- ETAPA 1: BUSCAR LINKS ---
    print(f"--- ETAPA 1: Buscando links en {URL_BUSQUEDA} ---")
    try:
        driver.get(URL_BUSQUEDA)
        WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f'div.{SELECTOR_TARJETA_LISTADO[1]}'))
        )
        print("Página de búsqueda cargada.")
        time.sleep(3) 
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        tarjetas = soup.find_all('div', class_=SELECTOR_TARJETA_LISTADO[1])
        if not tarjetas:
            print("No se encontraron tarjetas en la URL principal.")
            driver.quit()
            return
        print(f"Encontradas {len(tarjetas)} tarjetas.")
        for card in tarjetas:
            link_tag = card.find('a', class_=SELECTOR_LINK_TARJETA[1], href=True)
            if link_tag and 'href' in link_tag.attrs:
                link = link_tag['href']
                link_absoluto = f"https://www.argenprop.com{link}"
                if link_absoluto not in links_de_propiedades:
                    links_de_propiedades.append(link_absoluto)
    except Exception as e:
        print(f"  Error cargando la página de búsqueda: {e}")
        driver.quit()
        return

    print(f"\n--- ETAPA 1 Completa. Se encontraron {len(links_de_propiedades)} links. ---")
    
    # --- ETAPA 2: VISITAR CADA LINK (SÓLO LOS PRIMEROS 3) ---
    print("--- ETAPA 2: Visitando las primeras 3 propiedades ---")
    propiedades_encontradas = []
    
    for i, link in enumerate(links_de_propiedades[:3]):
        if i >= 3: break 
        print(f"Procesando link {i+1}/3: {link}")
        try:
            driver.get(link)
            
            # **************************************************
            # ** ¡¡¡AQUÍ ESTÁ LA CORRECCIÓN!!! **
            # **************************************************
            # Esperar a que cargue el <ul> de CARACTERÍSTICAS
            WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f'ul.{SELECTOR_CARACTERISTICAS_UL[1]}'))
            )
            # **************************************************
            
            time.sleep(1) 
            
            page_source_detalle = driver.page_source
            soup_detalle = BeautifulSoup(page_source_detalle, 'html.parser')
            
            # --- Extracción de datos detallados ---
            titulo = get_data_by_selector(soup_detalle, SELECTOR_TITULO_DETALLE[0], SELECTOR_TITULO_DETALLE[1])
            precio = get_data_by_selector(soup_detalle, SELECTOR_PRECIO_DETALLE[0], SELECTOR_PRECIO_DETALLE[1])
            expensas = get_data_by_selector(soup_detalle, SELECTOR_EXPENSAS_DETALLE[0], SELECTOR_EXPENSAS_DETALLE[1])
            ubicacion = get_data_by_selector(soup_detalle, SELECTOR_UBICACION_DETALLE[0], SELECTOR_UBICACION_DETALLE[1])
            
            barrio = ubicacion.split(',')[0].strip() if ',' in ubicacion else ubicacion
            
            caracteristicas = get_caracteristicas(soup_detalle, SELECTOR_CARACTERISTICAS_UL[0], SELECTOR_CARACTERISTICAS_UL[1])

            info_propiedad = {
                'Link': link, 'Titulo': titulo, 'Barrio': barrio,
                'Precio': precio, 'Expensas': expensas
            }
            info_propiedad.update(caracteristicas)
            propiedades_encontradas.append(info_propiedad)
            time.sleep(1.5) 

        except Exception as e:
            print(f"  Error procesando {link}: {e}")
            print("  Puede ser un CAPTCHA, un ID/Clase incorrecto en el MAPA, o la página es distinta.")

    # --- Cierre y guardado ---
    driver.quit()
    print("\nNavegador cerrado.")

    if propiedades_encontradas:
        print(f"\n--- Scraping Finalizado ---")
        print(f"Total de propiedades detalladas encontradas: {len(propiedades_encontradas)}")
        df = pd.DataFrame(propiedades_encontradas)
        try:
            df.to_excel('propiedades_argenprop_PRUEBA.xlsx', index=False)
            print("\n¡ÉXITO! Datos guardados en 'propiedades_argenprop_PRUEBA.xlsx'")
        except Exception as e:
            print(f"No se pudo guardar el Excel: {e}")
    else:
        print("\nNo se pudo extraer ninguna propiedad detallada.")

if __name__ == "__main__":
    main()