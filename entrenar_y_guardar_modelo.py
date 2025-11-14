import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score
import joblib 
import os

# --- CONFIGURACIÓN INICIAL ---
TASA_CAMBIO_DOLAR = 1430 
ARCHIV_REMAX = 'propiedades_remax_DETALLADO_COMPLETO.xlsx'
ARCHIV_ARGENPROP = 'propiedades_argenprop_FINAL_COMPLETO.xlsx' # <-- Tu nuevo archivo

# Columnas comunes que usaremos para el modelo
COLUMNAS_FINALES = [
    'Barrio',
    'Precio_ARS',
    'Expensas_ARS',
    'M2_cubierta',
    'Ambientes',
    'Dormitorios',
    'Baños',
    'Antiguedad'
]

# --- FUNCIONES DE LIMPIEZA SEPARADAS ---

def limpiar_moneda(texto, tasa_dolar, es_remax=True):
    """Limpia la columna de precio para CUALQUIER formato"""
    texto = str(texto).lower()
    if "no dispor" in texto or "consultar" in texto:
        return None
    
    # Extraer números (ignorando puntos de miles)
    # Quitar $ y .
    valor_str = re.sub(r'[$\.]', '', texto.split(' ')[-1])
    
    # Lógica para Argenprop/Remax (USD 550 vs $ 850.000)
    if es_remax:
        numeros = re.findall(r'[\d\.]+', texto)
        if not numeros: return None
        valor_str = "".join(numeros).replace('.', '')
    else: # Lógica Argenprop
        match = re.search(r'([\d\.]+)', texto.replace('.', ''))
        if not match: return None
        valor_str = match.group(1)

    valor = pd.to_numeric(valor_str, errors='coerce')
    if pd.isna(valor): return None
        
    if "usd" in texto:
        return valor * tasa_dolar
    else:
        return valor

def limpiar_expensas(texto):
    """Limpia expensas de CUALQUIER formato"""
    texto = str(texto).lower()
    if "no disponible" in texto or "+" in texto: # Argenprop a veces solo pone "+"
        return 0
    
    # Quitar puntos
    texto_limpio = texto.replace('.', '')
    
    # Extraer solo el número
    match = re.search(r'([\d\.]+)', texto_limpio)
    if match:
        return pd.to_numeric(match.group(1), errors='coerce')
    return 0


def cargar_y_limpiar_datos(archivo_remax, archivo_argenprop):
    print("Cargando y limpiando datos...")
    dataframes_limpios = []

    # --- 1. PROCESAR REMAX ---
    if os.path.exists(archivo_remax):
        print(f"Cargando Remax: {archivo_remax}")
        df_remax = pd.read_excel(archivo_remax)
        
        # Limpieza de Moneda
        df_remax['Precio_ARS'] = df_remax['Precio'].apply(lambda x: limpiar_moneda(x, TASA_CAMBIO_DOLAR, es_remax=True))
        df_remax['Expensas_ARS'] = df_remax['Expensas'].apply(limpiar_expensas)
        
        # Limpieza de Numéricos
        cols_numericas_remax = ['M2 cubierta', 'Ambientes', 'Dormitorios', 'Baños', 'Cocheras', 'Antiguedad']
        for col in cols_numericas_remax:
            df_remax[col] = pd.to_numeric(df_remax[col], errors='coerce')
        
        # Renombrar para consistencia
        df_remax = df_remax.rename(columns={'M2 cubierta': 'M2_cubierta'})
        
        # Seleccionar solo las columnas que nos importan
        # NOTA: Remax no tiene "M2 total" ni "Cocheras" en esta versión
        columnas_remax = [
            'Barrio', 'Precio_ARS', 'Expensas_ARS', 'M2_cubierta', 'Ambientes',
            'Dormitorios', 'Baños', 'Antiguedad'
        ]
        df_remax_final = df_remax[columnas_remax].copy()
        dataframes_limpios.append(df_remax_final)
        print(f"Remax procesado: {len(df_remax_final)} filas.")
    else:
        print(f"Advertencia: No se encontró el archivo {archivo_remax}")

    # --- 2. PROCESAR ARGENPROP ---
    if os.path.exists(archivo_argenprop):
        print(f"Cargando Argenprop: {archivo_argenprop}")
        df_argen = pd.read_excel(archivo_argenprop)
        
        # Limpieza de Moneda
        df_argen['Precio_ARS'] = df_argen['Precio'].apply(lambda x: limpiar_moneda(x, TASA_CAMBIO_DOLAR, es_remax=False))
        df_argen['Expensas_ARS'] = df_argen['Expensas'].apply(limpiar_expensas)

        # Renombrar para consistencia
        df_argen = df_argen.rename(columns={'M2 cubierta': 'M2_cubierta'})

        # Limpieza de Numéricos
        cols_numericas_argen = ['M2_cubierta', 'Ambientes', 'Dormitorios', 'Baños', 'Antiguedad']
        for col in cols_numericas_argen:
            df_argen[col] = pd.to_numeric(df_argen[col], errors='coerce')

        # Seleccionar solo las columnas que nos importan
        columnas_argen = [
            'Barrio', 'Precio_ARS', 'Expensas_ARS', 'M2_cubierta', 'Ambientes',
            'Dormitorios', 'Baños', 'Antiguedad'
        ]
        df_argen_final = df_argen[columnas_argen].copy()
        dataframes_limpios.append(df_argen_final)
        print(f"Argenprop procesado: {len(df_argen_final)} filas.")
    else:
        print(f"Advertencia: No se encontró el archivo {archivo_argenprop}")

    # --- 3. COMBINAR DATAFRAMES ---
    if not dataframes_limpios:
        print("¡Error! No se pudo cargar ningún archivo de datos.")
        return None
        
    df_combinado = pd.concat(dataframes_limpios, ignore_index=True)
    
    # --- 4. LIMPIEZA FINAL COMBINADA ---
    # Eliminar filas donde falten datos esenciales
    df_combinado = df_combinado.dropna(subset=['Precio_ARS', 'Barrio', 'M2_cubierta', 'Ambientes'])
    
    # Filtro de Outliers (Valores Atípicos)
    limite_precio = df_combinado['Precio_ARS'].quantile(0.99)
    limite_m2 = df_combinado['M2_cubierta'].quantile(0.99)
    
    print(f"Filtrando outliers... Límite de precio: ${limite_precio:,.0f} | Límite M2: {limite_m2} m²")
    df_combinado = df_combinado[
        (df_combinado['Precio_ARS'] <= limite_precio) &
        (df_combinado['M2_cubierta'] <= limite_m2)
    ]
    
    # Rellenar con 0 el resto de campos (Cocheras, Antiguedad, etc. si faltan)
    df_combinado = df_combinado.fillna(0)

    print(f"Limpieza completa. Total de {len(df_combinado)} propiedades válidas para entrenar.")
    return df_combinado

# 2. --- FUNCIÓN DE ENTRENAMIENTO DEL MODELO ---
def entrenar_modelo(df):
    print("Iniciando entrenamiento del modelo...")
    
    y = df['Precio_ARS']
    
    # Usamos las columnas comunes (sin M2 total, Cocheras, ni Amenities)
    features_numericos = [
        'M2_cubierta', 'Ambientes', 'Dormitorios', 
        'Baños', 'Antiguedad', 'Expensas_ARS'
    ]
    features_categoricos = ['Barrio']
    
    X = df[features_numericos + features_categoricos]

    column_transformer = make_column_transformer(
        (OneHotEncoder(handle_unknown='ignore'), features_categoricos),
        remainder='passthrough'
    )
    
    model = make_pipeline(
        column_transformer,
        RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"\n--- ¡Modelo Entrenado! ---")
    print(f"Puntaje de Precisión (R-cuadrado): {score:.2f}")

    return model

# --- EJECUCIÓN PRINCIPAL PARA ENTRENAR Y GUARDAR ---
if __name__ == "__main__":
    
    print("--- INICIANDO SCRIPT DE ENTRENAMIENTO COMBINADO (Remax + Argenprop) ---")
    
    df_limpio = cargar_y_limpiar_datos(ARCHIV_REMAX, ARCHIV_ARGENPROP)
    
    if df_limpio is None or len(df_limpio) < 50:
        print("\n*** ADVERTENCIA: No hay suficientes datos (menos de 50) para un modelo confiable. ***")
        print("El modelo NO se guardará.")
    else:
        modelo_entrenado = entrenar_modelo(df_limpio)
        
        try:
            joblib.dump(modelo_entrenado, 'modelo_alquiler.pkl')
            print("\n--- ¡ÉXITO! Modelo guardado como 'modelo_alquiler.pkl' ---")
            print("El modelo ahora está entrenado con AMBOS datasets.")
            print("Ya puedes ejecutar 'app.py' para iniciar la calculadora web (¡recuerda actualizarlo!).")
        except Exception as e:
            print(f"\n*** ERROR AL GUARDAR EL MODELO: {e} ***")