import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re 
import os 

# ===================================================================
# --- CONFIGURACIÓN ---
# ===================================================================
# Archivo de entrada (el que ya tienes)
ARCHIVO_ENTRADA = "propiedades_argenprop_FINAL_COMPLETO.xlsx"
# Archivo de salida (el nuevo archivo que se creará)
ARCHIVO_SALIDA = "propiedades_argenprop_CON_AMENITIES.xlsx"

TIEMPO_MAX_ESPERA = 20      

# ===================================================================
# --- CONFIGURACIÓN DE SELECTORES DE DETALLE ---
# ===================================================================
SELECTOR_TITULO_DETALLE = ("class", "section-description--title")
SELECTOR_PRECIO_DETALLE = ("class", "titlebar__price")
SELECTOR_EXPENSAS_DETALLE = ("class", "titlebar__expenses")
SELECTOR_UBICACION_TITULO = ("class", "titlebar__title") 
SELECTOR_UBICACION_DIRECCION = ("class", "titlebar__address") 
SELECTOR_CARACTERISTICAS_UL = ("class", "property-main-features")

# ¡NUEVO SELECTOR BASADO EN TU IMAGEN!
SELECTOR_AMENITIES_TITULO = ("class", "section-title-s") 

MAPEO_CARACTERISTICAS = {
    'Sup. cubierta': 'M2 cubierta',
    'Dormitorios': 'Dormitorios',
    'Antiguedad': 'Antiguedad',
    'Baños': 'Baños',
    'Ambientes': 'Ambientes',
    'Estado': 'Estado'
}
BARRIOS_BUSCADOS = ['palermo', 'belgrano', 'recoleta', 'colegiales', 'nuñez', 'puerto madero']

# ===================================================================
# --- Lógica de Extracción (Funciones) ---
# ===================================================================

def get_data_by_selector(soup, tipo, selector):
    try:
        tag = None
        if tipo == "class":
            tag = soup.find(class_=lambda c: c and selector in c)
        if tag:
            if selector == SELECTOR_PRECIO_DETALLE[1]:
                return tag.get_text(separator=' ', strip=True) 
            return tag.get_text(strip=True)
        return "No disponible"
    except Exception: return "Error"

def get_barrio_robusto(soup, selector_titulo, selector_direccion):
    try:
        texto_busqueda = ""
        tag_titulo = soup.find('h2', class_=lambda c: c and selector_titulo in c)
        if tag_titulo:
            texto_busqueda += " " + tag_titulo.get_text().lower()
        tag_direccion = soup.find(class_=lambda c: c and selector_direccion in c)
        if tag_direccion:
            texto_busqueda += " " + tag_direccion.get_text().lower()
        for barrio in BARRIOS_BUSCADOS:
            if barrio in texto_busqueda:
                return barrio.title() 
        return "Barrio No Encontrado"
    except Exception as e: return "Error"

def get_expensas(soup, tipo, selector):
    try:
        tag = soup.find('p', class_=lambda c: c and selector in c)
        if tag:
            texto_expensas = tag.get_text(strip=True) 
            match = re.search(r'[\d\.]+', texto_expensas.replace('.', '')) 
            if match:
                return match.group(0) 
            return "No disponible (texto encontrado pero sin número)"
        return "No disponible" 
    except Exception: return "No disponible" 

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
        es_monoambiente = False
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
                if nombre_columna == 'Ambientes':
                    if "monoambiente" in valor_final.lower():
                        valor_final = "1"
                        es_monoambiente = True 
                data[nombre_columna] = valor_final
        if es_monoambiente and 'Dormitorios' not in data:
             data['Dormitorios'] = "1"
        return data
    except Exception as e:
        print(f"  Error en get_caracteristicas: {e}")
        return data

# **************************************************
# ** ¡¡¡NUEVA FUNCIÓN DE AMENITIES!!! **
# **************************************************
def get_amenities(soup, tipo, selector_titulo):
    """
    Busca el título "Amenities" y extrae la lista <ul>
    que le sigue (hermano).
    """
    try:
        amenities_lista = []
        
        # 1. Encontrar el <h3> del TÍTULO (ej. <h3 class="section-title-s">Amenities</h3>)
        title_tag = soup.find('h3', class_=lambda c: c and selector_titulo in c, text=re.compile("Amenities", re.IGNORECASE))
        
        if not title_tag:
            return "No disponible (no se halló título Amenities)"
            
        # 2. Encontrar el <ul> que es su hermano
        ul_tag = title_tag.find_next_sibling('ul')
        
        if not ul_tag:
            return "No disponible (no se halló <ul> después del título)"

        # 3. Iterar sobre los <li>
        items = ul_tag.find_all('li')
        for item in items:
            p_tag = item.find('p')
            if p_tag:
                amenities_lista.append(p_tag.get_text(strip=True))
            
        if not amenities_lista:
            return "No disponible (lista vacía)"
            
        return ", ".join(amenities_lista) # Devuelve "Ascensor, Gimnasio"

    except Exception as e:
        print(f"  Error en get_amenities: {e}")
        return "Error"

# ===================================================================
# --- FUNCIÓN PRINCIPAL DEL SCRIPT ---
# ===================================================================

def main():
    
    # --- ETAPA 0: CARGAR DATOS EXISTENTES ---
    links_a_procesar = []
    if os.path.exists(ARCHIVO_ENTRADA):
        print(f"Cargando archivo existente: '{ARCHIVO_ENTRADA}'")
        try:
            df_viejo = pd.read_excel(ARCHIVO_ENTRADA)
            links_a_procesar = df_viejo['Link'].tolist()
            print(f"Se encontraron {len(links_a_procesar)} links para re-escanear.")
        except Exception as e:
            print(f"  Error al leer el archivo Excel: {e}.")
            return
    else:
        print(f"Error: No se encontró el archivo '{ARCHIVO_ENTRADA}'. No hay links para procesar.")
        return

    # --- INICIAR DRIVER ---
    print("Iniciando Scraper de Argenprop...")
    try:
        driver = webdriver.Chrome()
    except Exception as e:
        print("Error iniciando Selenium. Asegúrate de tener chromedriver instalado.")
        print(f"Error: {e}")
        return

    # --- ETAPA 2: VISITAR CADA LINK (SIN LÍMITE) ---
    print("--- ETAPA 2: Visitando todos los links (esto tardará)... ---")
    propiedades_actualizadas = []
    
    for i, link in enumerate(links_a_procesar):
        print(f"Procesando link {i+1}/{len(links_a_procesar)}: {link}")
        try:
            driver.get(link)
            WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f'ul.{SELECTOR_CARACTERISTICAS_UL[1]}'))
            )
            time.sleep(1) 
            
            page_source_detalle = driver.page_source
            soup_detalle = BeautifulSoup(page_source_detalle, 'html.parser')
            
            # --- Extracción de datos detallados ---
            titulo = get_data_by_selector(soup_detalle, SELECTOR_TITULO_DETALLE[0], SELECTOR_TITULO_DETALLE[1])
            precio = get_data_by_selector(soup_detalle, SELECTOR_PRECIO_DETALLE[0], SELECTOR_PRECIO_DETALLE[1])
            expensas = get_expensas(soup_detalle, SELECTOR_EXPENSAS_DETALLE[0], SELECTOR_EXPENSAS_DETALLE[1])
            barrio = get_barrio_robusto(soup_detalle, SELECTOR_UBICACION_TITULO[1], SELECTOR_UBICACION_DIRECCION[1])
            caracteristicas = get_caracteristicas(soup_detalle, SELECTOR_CARACTERISTICAS_UL[0], SELECTOR_CARACTERISTICAS_UL[1])
            
            # ¡¡¡EXTRACCIÓN DE AMENITIES AÑADIDA!!!
            amenities = get_amenities(soup_detalle, SELECTOR_AMENITIES_TITULO[0], SELECTOR_AMENITIES_TITULO[1])

            info_propiedad = {
                'Link': link, 'Titulo': titulo, 'Barrio': barrio,
                'Precio': precio, 'Expensas': expensas,
                'Amenities': amenities # <-- ¡COLUMNA AÑADIDA!
            }
            info_propiedad.update(caracteristicas)
            propiedades_actualizadas.append(info_propiedad)
            time.sleep(1.5) # Pausa de cortesía

        except Exception as e:
            # Si falla, imprime el error y sigue con el próximo link
            print(f"  Error procesando {link}: {e}")
            print("  Continuando con el siguiente link...")

    # --- Cierre y guardado ---
    driver.quit()
    print("\nNavegador cerrado.")

    if propiedades_actualizadas:
        print(f"\n--- Scraping Finalizado ---")
        print(f"Total de propiedades detalladas encontradas: {len(propiedades_actualizadas)}")
        df = pd.DataFrame(propiedades_actualizadas)
        try:
            df.to_excel(ARCHIVO_SALIDA, index=False)
            print(f"\n¡ÉXITO! Datos guardados en '{ARCHIVO_SALIDA}'")
        except Exception as e:
            print(f"No se pudo guardar el Excel: {e}")
    else:
        print("\nNo se pudo extraer ninguna propiedad detallada.")

if __name__ == "__main__":
    main()