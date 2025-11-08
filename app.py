from flask import Flask, render_template, request
import pandas as pd
import joblib 

app = Flask(__name__)

# --- CARGAR EL MODELO ENTRENADO ---
try:
    modelo = joblib.load('modelo_alquiler.pkl')
    print("Modelo de alquiler cargado exitosamente.")
except Exception as e:
    print(f"ERROR: No se pudo cargar el modelo 'modelo_alquiler.pkl'. {e}")
    modelo = None 

# --- Lista de Barrios ---
BARRIOS_DISPONIBLES = sorted([
    'Palermo', 'Belgrano', 'Recoleta', 'Colegiales', 
    'Puerto Madero', 'Retiro', 'Chacarita', 'Villa Crespo', 'San Nicolás'
    # Agrega más si es necesario
])


@app.route('/', methods=['GET', 'POST'])
def index():
    prediccion = None
    if request.method == 'POST':
        if modelo is None:
            prediccion = "Error: El modelo no se pudo cargar."
        else:
            try:
                # **************************************************
                # ** ¡¡¡CAMBIOS AQUÍ!!! **
                # **************************************************
                
                # 1. Preparar los datos del formulario
                datos_input = {
                    'M2 total': float(request.form['m2_total']),
                    'M2 cubierta': float(request.form['m2_cubierta']),
                    'Ambientes': int(request.form['ambientes']),
                    'Dormitorios': int(request.form['dormitorios']),
                    'Baños': int(request.form['banos']),
                    'Cocheras': int(request.form['cocheras']),
                    'Antiguedad': int(request.form['antiguedad']),
                    'Expensas_ARS': float(request.form['expensas_ars']),
                    'Barrio': request.form['barrio'],
                    'Tiene_Amenities_Flag': int(request.form['tiene_amenities']) # <-- AÑADIDO
                }
                # **************************************************

                # 2. Hacer la predicción
                valor_predicho = modelo.predict(pd.DataFrame([datos_input]))[0]
                prediccion = f"${valor_predicho:,.0f} ARS (aprox.)"

            except ValueError:
                prediccion = "Error: Por favor, introduce valores numéricos válidos."
            except Exception as e:
                prediccion = f"Ocurrió un error inesperado al predecir: {e}"

    return render_template('index.html', prediccion=prediccion, barrios=BARRIOS_DISPONIBLES)

if __name__ == '__main__':
    app.run(debug=True)