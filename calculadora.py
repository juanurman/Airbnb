import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score

# --- CONFIGURACIÓN INICIAL ---
# ¡IMPORTANTE! Define a cuánto está el dólar para unificar monedas
TASA_CAMBIO_DOLAR = 1430 # <-- ¡ACTUALIZADO!

# 1. --- FUNCIÓN DE CARGA Y LIMPIEZA PROFUNDA ---
def cargar_y_limpiar_datos(archivo_excel):
    print(f"Cargando datos desde {archivo_excel}...")
    df = pd.read_excel(archivo_excel)

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

    print(f"Limpieza completa. Quedan {len(df)} propiedades válidas para entrenar.")
    return df

# 2. --- FUNCIÓN DE ENTRENAMIENTO DEL MODELO ---
def entrenar_modelo(df):
    print("Iniciando entrenamiento del modelo...")
    
    y = df['Precio_ARS']
    
    features_numericos = ['M2 total', 'M2 cubierta', 'Ambientes', 
                          'Dormitorios', 'Baños', 'Cocheras', 
                          'Antiguedad', 'Expensas_ARS']
    
    features_categoricos = ['Barrio']
    
    df[features_numericos] = df[features_numericos].fillna(0)
    X = df[features_numericos + features_categoricos]

    column_transformer = make_column_transformer(
        (OneHotEncoder(handle_unknown='ignore'), features_categoricos),
        remainder='passthrough'
    )
    
    # Usamos RandomForestRegressor, un modelo mucho más robusto
    model = make_pipeline(
        column_transformer,
        RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"\n--- ¡Modelo Entrenado! ---")
    print(f"Puntaje de Precisión (R-cuadrado): {score:.2f}")
    print(f"(Con RandomForest, un puntaje de 0.80 o más es común)")

    return model

# 3. --- FUNCIÓN DE PREDICCIÓN (LA CALCULADORA) ---
def crear_funcion_calculadora(model):
    
    def predecir_alquiler(input_usuario):
        datos_completos = {
            'M2 total': 0,
            'M2 cubierta': 0,
            'Ambientes': 1,
            'Dormitorios': 1,
            'Baños': 1,
            'Cocheras': 0,
            'Antiguedad': 0,
            'Expensas_ARS': 0,
            'Barrio': 'Palermo' 
        }
        datos_completos.update(input_usuario)
        input_df = pd.DataFrame([datos_completos])
        prediccion_ars = model.predict(input_df)
        return prediccion_ars[0]

    return predecir_alquiler

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    
    # El nombre del archivo es el que pediste
    nombre_del_archivo = 'propiedades_remax_DETALLADO_COMPLETO.xlsx'
    
    try:
        df_limpio = cargar_y_limpiar_datos(nombre_del_archivo)
    except FileNotFoundError:
        print(f"*** ERROR: No se encontró el archivo '{nombre_del_archivo}' ***")
        print("Asegúrate de que esté en la misma carpeta que este script .py")
        exit()
    except Exception as e:
        print(f"*** ERROR al cargar el archivo: {e} ***")
        exit()
    
    if len(df_limpio) < 50:
        print("\n*** ADVERTENCIA: Muy pocos datos (menos de 50) para un modelo confiable. ***")
        print("El modelo no se entrenará.")
    else:
        modelo_entrenado = entrenar_modelo(df_limpio)
        predecir_alquiler = crear_funcion_calculadora(modelo_entrenado)
        
        print("\n--- 💰 Probando la Calculadora (Modelo RandomForest) ---")
        
        mi_depto_1 = {
            'M2 total': 50,
            'M2 cubierta': 45,
            'Ambientes': 2,
            'Dormitorios': 1,
            'Baños': 1,
            'Cocheras': 0,
            'Antiguedad': 10,
            'Expensas_ARS': 50000,
            'Barrio': 'Palermo'
        }
        precio_1 = predecir_alquiler(mi_depto_1)
        print(f"Predicción (Palermo, 50m2, 2 amb): $ {precio_1:,.0f} ARS")

        mi_depto_2 = {
            'M2 total': 80,
            'M2 cubierta': 75,
            'Ambientes': 3,
            'Dormitorios': 2,
            'Baños': 2,
            'Cocheras': 1,
            'Antiguedad': 5,
            'Expensas_ARS': 90000,
            'Barrio': 'Belgrano'
        }
        precio_2 = predecir_alquiler(mi_depto_2)
        print(f"Predicción (Belgrano, 80m2, 3 amb): $ {precio_2:,.0f} ARS")

        mi_depto_3 = {
            'M2 total': 40,
            'M2 cubierta': 40,
            'Ambientes': 1,
            'Dormitorios': 1,
            'Baños': 1,
            'Cocheras': 0,
            'Antiguedad': 2,
            'Expensas_ARS': 120000,
            'Barrio': 'Puerto Madero'
        }
        precio_3 = predecir_alquiler(mi_depto_3)
        print(f"Predicción (Pto Madero, 40m2, 1 amb): $ {precio_3:,.0f} ARS")