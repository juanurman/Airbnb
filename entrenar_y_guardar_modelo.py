import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score
import joblib 

# --- CONFIGURACIÓN INICIAL ---
TASA_CAMBIO_DOLAR = 1430 

# 1. --- FUNCIÓN DE CARGA Y LIMPIEZA PROFUNDA ---
def cargar_y_limpiar_datos(archivo_excel):
    print(f"Cargando datos desde {archivo_excel}...")
    try:
        df = pd.read_excel(archivo_excel)
    except FileNotFoundError:
        print(f"*** ERROR: No se encontró el archivo '{archivo_excel}' ***")
        return None
    except Exception as e:
        print(f"*** ERROR al cargar el archivo: {e} ***")
        return None

    def limpiar_moneda(texto):
        texto = str(texto).lower()
        if "no dispor" in texto or "consultar" in texto:
            return None
        
        numeros = re.findall(r'[\d\.]+', texto)
        if not numeros:
            return None
        
        valor_str = "".join(numeros).replace('.', '')
        valor = pd.to_numeric(valor_str, errors='coerce')
        
        if pd.isna(valor):
            return None
            
        if "usd" in texto:
            return valor * TASA_CAMBIO_DOLAR
        else:
            return valor

    print("Limpiando y unificando 'Precio' y 'Expensas' a ARS...")
    df['Precio_ARS'] = df['Precio'].apply(limpiar_moneda)
    df['Expensas_ARS'] = df['Expensas'].apply(limpiar_moneda)
    df['Expensas_ARS'] = df['Expensas_ARS'].fillna(0)
    
    print("Limpiando features numéricos (M2, Ambientes, etc.)...")
    columnas_numericas = ['M2 total', 'M2 cubierta', 'M2 descubierta', 
                          'Ambientes', 'Dormitorios', 'Baños', 
                          'Cocheras', 'Antiguedad']
    
    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['Barrio'] = df['Barrio'].replace('No dispor', None)
    
    df = df.dropna(subset=['Precio_ARS', 'Barrio', 'M2 total'])
    
    # Filtro de Outliers (Valores Atípicos)
    limite_precio = df['Precio_ARS'].quantile(0.99)
    print(f"Filtrando precios... Límite de precio (percentil 99): $ {limite_precio:,.0f} ARS")
    df = df[df['Precio_ARS'] <= limite_precio]
    
    # **************************************************
    # ** ¡¡¡NUEVA LÍNEA AQUÍ!!! **
    # **************************************************
    # Crear la bandera (flag) de Amenities
    # Será 0 si no tiene, 1 si tiene (basado en si pudimos scrapear la lista)
    print("Creando nueva feature 'Tiene_Amenities_Flag'...")
    df['Tiene_Amenities_Flag'] = df['Amenities'].apply(lambda x: 0 if pd.isna(x) or 'No disponible' in str(x) or 'ID NO CONFIGURADO' in str(x) else 1)
    # **************************************************
    
    print(f"Limpieza completa. Quedan {len(df)} propiedades válidas para entrenar.")
    return df

# 2. --- FUNCIÓN DE ENTRENAMIENTO DEL MODELO ---
def entrenar_modelo(df):
    print("Iniciando entrenamiento del modelo...")
    
    y = df['Precio_ARS']
    
    # **************************************************
    # ** ¡¡¡CAMBIO AQUÍ!!! **
    # **************************************************
    features_numericos = [
        'M2 total', 'M2 cubierta', 'Ambientes', 
        'Dormitorios', 'Baños', 'Cocheras', 
        'Antiguedad', 'Expensas_ARS', 
        'Tiene_Amenities_Flag' # <-- AÑADIDO
    ]
    # **************************************************
    
    features_categoricos = ['Barrio']
    
    df[features_numericos] = df[features_numericos].fillna(0)
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
    
    print("--- INICIANDO SCRIPT DE ENTRENAMIENTO ---")
    
    nombre_del_archivo = 'propiedades_remax_DETALLADO_COMPLETO.xlsx'
    
    df_limpio = cargar_y_limpiar_datos(nombre_del_archivo)
    
    if df_limpio is None or len(df_limpio) < 50:
        print("\n*** ADVERTENCIA: No hay suficientes datos (menos de 50) para un modelo confiable. ***")
        print("El modelo NO se guardará.")
    else:
        modelo_entrenado = entrenar_modelo(df_limpio)
        
        try:
            joblib.dump(modelo_entrenado, 'modelo_alquiler.pkl')
            print("\n--- ¡ÉXITO! Modelo guardado como 'modelo_alquiler.pkl' ---")
            print("Ya puedes ejecutar 'app.py' para iniciar la calculadora web.")
        except Exception as e:
            print(f"\n*** ERROR AL GUARDAR EL MODELO: {e} ***")