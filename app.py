from flask import Flask, render_template, request
import pandas as pd
import joblib 

app = Flask(__name__)

# --- CARGAR EL MODELO ENTRENADO ---
try:
    modelo = joblib.load('modelo_alquiler.pkl')
    print("Modelo de alquiler (combinado) cargado exitosamente.")
except Exception as e:
    print(f"ERROR: No se pudo cargar el modelo 'modelo_alquiler.pkl'. {e}")
    modelo = None 

# --- Lista de Barrios ---
BARRIOS_DISPONIBLES = sorted([
    'Palermo', 'Belgrano', 'Recoleta', 'Colegiales', 
    'Puerto Madero', 'Retiro', 'Chacarita', 'Villa Crespo', 'San Nicolás',
    'Nuñez', 'Barrio No Encontrado' # <-- Agregados
])


@app.route('/', methods=['GET', 'POST'])
def index():
    prediccion = None
    form_data = {} 

    if request.method == 'POST':
        if modelo is None:
            prediccion = "Error: El modelo no se pudo cargar."
        else:
            try:
                # 1. Preparar los datos del formulario para el NUEVO MODELO
                datos_input = {
                    'M2_cubierta': float(request.form['m2_cubierta']),
                    'Ambientes': int(request.form['ambientes']),
                    'Dormitorios': int(request.form['dormitorios']),
                    'Baños': int(request.form['banos']),
                    'Antiguedad': int(request.form['antiguedad']),
                    'Expensas_ARS': float(request.form['expensas_ars']),
                    'Barrio': request.form['barrio'],
                    # Campos que ya no usamos: Cocheras, M2 total, Amenities
                }
                
                # 2. Hacer la predicción
                valor_predicho = modelo.predict(pd.DataFrame([datos_input]))[0]
                prediccion = f"${valor_predicho:,.0f} ARS (aprox.)"
                
                form_data = request.form 

            except ValueError:
                prediccion = "Error: Por favor, introduce valores numéricos válidos."
                form_data = request.form 
            except Exception as e:
                prediccion = f"Ocurrió un error inesperado al predecir: {e}"
                form_data = request.form
    
    else: # request.method == 'GET' (primera carga)
        # Valores por defecto para el nuevo formulario
        form_data = {
            'm2_cubierta': 45,
            'ambientes': 2,
            'dormitorios': 1,
            'banos': 1,
            'antiguedad': 10,
            'expensas_ars': 50000,
            'barrio': 'Palermo'
        }

    return render_template(
        'index.html', 
        prediccion=prediccion, 
        barrios=BARRIOS_DISPONIBLES, 
        form_data=form_data 
    )

if __name__ == '__main__':
    app.run(debug=True)