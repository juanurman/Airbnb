import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re 

# ===================================================================
# --- CONFIGURACIÓN ETAPA 1 (PÁGINA DE BÚSQUEDA) ---
CLASE_TARJETA = "card-remax__container"

# ===================================================================
# --- CONFIGURACIÓN ETAPA 2 (PÁGINA DE DETALLE) ---
#
# ¡¡MAPA FINAL!! 
#
MAPA_DE_IDS = {
    # Campo : ( "tipo_extraccion", ...args )
    
    # --- Datos Simples (Estos SÍ usan ID) ---
    "titulo":       ( "simple", "id", "title-container" ),
    "barrio":       ( "simple", "id", "ubication-text" ),
    "precio":       ( "simple", "id", "price-container" ),
    "expensas":     ( "simple", "id", "expenses-container" ),
    
    # --- Datos de "feature-detail" (Estos usan KEYWORDS) ---
    "m2_total":     ( "keyword", "superficie total" ),
    "m2_cubierta":  ( "keyword", "superficie cubierta" ),
    "m2_descubierta": ( "keyword", "superficie semicubierta" ),
    "ambientes":    ( "keyword", "ambientes" ),
    "dormitorios":  ( "keyword", "dormitorios" ),
    "baños":        ( "keyword", "baños" ), 
    "cocheras":     ( "keyword", "cocheras" ), 
    "antiguedad":   ( "keyword", "antigüedad" ),
    
    # --- Datos Especiales (Nueva lógica de Amenity) ---
    "amenities":    ( "amenities", "Amenities" )
}
#
# --- FIN DE LA CONFIGURACIÓN ---
# ===================================================================

# --- Configuración de Selenium ---
try:
    driver = webdriver.Chrome()
except Exception as e:
    print("Error iniciando Selenium. Asegúrate de tener chromedriver instalado.")
    exit()

# --- Configuración de la URL (¡NUEVO LINK!) ---
URL_PRE_PAGE = "https://www.remax.com.ar/listings/rent?"
URL_POST_PAGE = ("&pageSize=24&sort=-createdAt&in:operationId=2&in:eStageId=0,1,2,3,4&in:typeId=1,2,3,4,5,6,7,8"
                 "&locations=in::::25024@palermo,25013@Colegiales,25033@Recoleta,25006@Belgrano,25032@Puerto%20Madero,25034@Retiro:::"
                 "&landingPath=&filterCount=1&viewMode=listViewMode")

links_de_propiedades = []
MAX_PAGINAS_A_SCRAPEAR = 50  # <-- AUMENTADO (31+ páginas)
TIEMPO_MAX_ESPERA = 30 # <-- AUMENTADO (más paciencia)

print("--- ETAPA 1: Buscando links de propiedades ---")

try:
    for page_num in range(MAX_PAGINAS_A_SCRAPEAR):
        url_a_scrapear = f"{URL_PRE_PAGE}page={page_num}{URL_POST_PAGE}"
        print(f"Scrapeando página de búsqueda {page_num}...")
        
        driver.get(url_a_scrapear)
        
        selector_xpath = f"//div[contains(@class, '{CLASE_TARJETA}')]"
        try:
            WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
                EC.presence_of_element_located((By.XPATH, selector_xpath))
            )
            time.sleep(2) 
        except Exception as e:
            print(f"No se encontraron tarjetas en página {page_num}.")
            print("Puede ser el final o un error de carga.")
            break 
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        listado_items = soup.find_all('div', class_=lambda c: c and CLASE_TARJETA in c)
        
        if not listado_items:
            print("No se encontraron más items. Terminando Etapa 1.")
            break 
            
        print(f"Encontradas {len(listado_items)} propiedades en esta página.")

        for item in listado_items:
            link_tag = item.find('a') 
            if link_tag and 'href' in link_tag.attrs:
                link_relativo = link_tag['href']
                link_absoluto = f"https://www.remax.com.ar{link_relativo}"
                if link_absoluto not in links_de_propiedades:
                    links_de_propiedades.append(link_absoluto)
                    
except Exception as e:
    print(f"Se produjo un error en la Etapa 1: {e}")

print(f"\n--- ETAPA 1 Completa. Se encontraron {len(links_de_propiedades)} links únicos. ---")
print("--- ETAPA 2: Visitando cada link (esto tardará)... ---")

propiedades_encontradas = []

# --- Funciones Helper para la Etapa 2 ---

def get_data_smarter(soup_detalle, tipo, tipo_selector, selector_o_keyword):
    """Función MEJORADA con lógica de CONTENEDOR."""
    try:
        # --- Lógica "simple" (con ID) ---
        if tipo == "simple":
            base_tag = None
            if tipo_selector == "id":
                base_tag = soup_detalle.find(id=re.compile(f"^{selector_o_keyword}$"))
            elif tipo_selector == "class":
                base_tag = soup_detalle.find(class_=lambda c: c and selector_o_keyword in c)
            
            if base_tag:
                return base_tag.get_text(strip=True)
            else:
                return 'No disponible (no se halló selector simple)'

        # --- LÓGICA DE KEYWORD (CONTENEDOR) ---
        elif tipo == "keyword":
            keyword = selector_o_keyword.lower() # "ambientes"
            
            # 1. Encontrar TODOS los contenedores (basado en tus imágenes)
            all_containers = soup_detalle.find_all('div', class_=lambda c: c and "column-item" in c)
            
            for container in all_containers:
                texto_completo = container.get_text(strip=True).lower() 
                
                # 2. Si el keyword está en el texto del contenedor
                if keyword in texto_completo:
                    # 3. Extraer el número de ESE contenedor
                    match = re.search(r'[\d\.]+', texto_completo) 
                    if match:
                        return match.group(0) # Retorna "2"
                    else:
                        # Si encontramos "antigüedad" pero no un número (ej. "a estrenar")
                        return texto_completo 
            
            return 'No disponible (no se halló keyword)'
        
        # --- LÓGICA DE AMENITIES ---
        elif tipo == "amenities":
            keyword_titulo = selector_o_keyword.lower() # "amenities"
            amenities_lista = []
            
            title_tag = soup_detalle.find('p', class_=lambda c: c and "bold" in c, text=re.compile(keyword_titulo, re.IGNORECASE))
            
            if not title_tag:
                return "No disponible (no se halló título Amenities)"
                
            title_container_div = title_tag.find_parent('div')
            
            for sibling in title_container_div.find_next_siblings('div'):
                amenity_tag = sibling.find('p', class_=lambda c: c and "regular" in c)
                
                if amenity_tag:
                    amenities_lista.append(amenity_tag.get_text(strip=True))
                else:
                    break 
            
            if not amenities_lista:
                return "No disponible (lista vacía)"
                
            return ", ".join(amenities_lista) 

    except Exception as e:
        return f'Error extrayendo: {e}'
# ----------------------------------------

# !!! --- SIN LÍMITE DE PRUEBA --- !!!
for i, link in enumerate(links_de_propiedades):
    print(f"Procesando link {i+1}/{len(links_de_propiedades)}: {link}")
    
    try:
        driver.get(link)
        
        precio_config = MAPA_DE_IDS["precio"] 
        tipo_selector_espera = precio_config[1]
        selector_espera = precio_config[2]
        
        if tipo_selector_espera == "id":
             WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
                EC.presence_of_element_located((By.ID, selector_espera))
            )
        else: 
            WebDriverWait(driver, TIEMPO_MAX_ESPERA).until(
                EC.presence_of_element_located((By.XPATH, f"//*[contains(@class, '{selector_espera}')]"))
            )
        
        
        page_source_detalle = driver.page_source
        soup_detalle = BeautifulSoup(page_source_detalle, 'html.parser')
        
        info_propiedad = {'Link': link}
        
        campos_numericos_opcionales = [
            "m2_descubierta", 
            "cocheras", 
            "antiguedad",
            "m2_cubierta",
            "ambientes",
            "dormitorios",
            "baños" 
        ]
        
        for campo, (tipo, *args) in MAPA_DE_IDS.items():
            
            campo_bonito = campo.replace("_", " ").capitalize()
            resultado = ""
            
            try:
                if tipo == "simple":
                    resultado = get_data_smarter(soup_detalle, tipo, args[0], args[1]) 
                elif tipo == "amenities" or tipo == "keyword":
                    resultado = get_data_smarter(soup_detalle, tipo, None, args[0]) 
                
                # Limpieza final
                if campo in campos_numericos_opcionales:
                    # Si no es un número, poner 0
                    if "No disponible" in str(resultado) or not re.search(r'[\d\.]+', str(resultado)):
                        info_propiedad[campo_bonito] = "0"
                    else:
                        info_propiedad[campo_bonito] = resultado
                else:
                    info_propiedad[campo_bonito] = resultado
                    
            except IndexError:
                print(f"  Error de Index (BUG) en el campo: {campo}")
                info_propiedad[campo_bonito] = "Error de Script"
                
        propiedades_encontradas.append(info_propiedad)
        time.sleep(1.5) # <-- Pausa de cortesía

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
        df.to_excel('propiedades_remax_DETALLADO_COMPLETO.xlsx', index=False)
        print("\n¡ÉXITO! Datos guardados en 'propiedades_remax_DETALLADO_COMPLETO.xlsx'")
    except Exception as e:
        print(f"No se pudo guardar el Excel: {e} (¿Quizás lo tienes abierto?)")
else:
    print("\nNo se pudo extraer ninguna propiedad detallada.")