from flask import Flask, render_template, request
import pandas as pd
import joblib # Para cargar el modelo guardado

app = Flask(__name__)

# --- CARGAR EL MODELO ENTRENADO ---
# Esto se hace UNA VEZ cuando la aplicación inicia, no en cada predicción
try:
    modelo = joblib.load('modelo_alquiler.pkl')
    print("Modelo de alquiler cargado exitosamente.")
except Exception as e:
    print(f"ERROR: No se pudo cargar el modelo 'modelo_alquiler.pkl'. Asegúrate de haberlo entrenado y guardado. {e}")
    modelo = None # Si no hay modelo, no podemos predecir

# --- Lista de Barrios para el Dropdown (IMPORTANTE: deben ser los mismos que en tu Excel) ---
# Extraemos los barrios del DataFrame original para asegurar consistencia
# Si no tienes el df_limpio aquí, puedes poner una lista manual:
# BARRIOS_DISPONIBLES = ['Palermo', 'Belgrano', 'Recoleta', 'Colegiales', 'Puerto Madero', 'Retiro']
# Pero es mejor obtenerlos de los datos reales.
# Para evitar cargar el Excel de nuevo aquí, vamos a asumir una lista común o la cargarías solo para esto.
# Por simplicidad, aquí usaré una lista predefinida que incluye los que vimos.
BARRIOS_DISPONIBLES = sorted([
    'Palermo', 'Belgrano', 'Recoleta', 'Colegiales', 
    'Puerto Madero', 'Retiro', 'Chacarita', 'Villa Crespo', 'San Nicolás', # Agrega más barrios si los tienes en tu data
    # Es crucial que esta lista contenga TODOS los barrios que quieres que el usuario pueda seleccionar
    # y que estén en tu dataset de entrenamiento.
])


@app.route('/', methods=['GET', 'POST'])
def index():
    prediccion = None
    if request.method == 'POST':
        if modelo is None:
            prediccion = "Error: El modelo no se pudo cargar. Contacta al administrador."
        else:
            try:
                # Obtener los datos del formulario
                m2_total = float(request.form['m2_total'])
                m2_cubierta = float(request.form['m2_cubierta'])
                ambientes = int(request.form['ambientes'])
                dormitorios = int(request.form['dormitorios'])
                banos = int(request.form['banos'])
                cocheras = int(request.form['cocheras'])
                antiguedad = int(request.form['antiguedad'])
                expensas_ars = float(request.form['expensas_ars'])
                barrio = request.form['barrio']

                # Preparar los datos para el modelo (como un diccionario)
                datos_input = {
                    'M2 total': m2_total,
                    'M2 cubierta': m2_cubierta,
                    'Ambientes': ambientes,
                    'Dormitorios': dormitorios,
                    'Baños': banos,
                    'Cocheras': cocheras,
                    'Antiguedad': antiguedad,
                    'Expensas_ARS': expensas_ars,
                    'Barrio': barrio
                }

                # Hacer la predicción
                valor_predicho = modelo.predict(pd.DataFrame([datos_input]))[0]
                prediccion = f"${valor_predicho:,.0f} ARS (aprox.)"

            except ValueError:
                prediccion = "Error: Por favor, introduce valores numéricos válidos."
            except KeyError as e:
                prediccion = f"Error: Falta un campo requerido en el formulario: {e}"
            except Exception as e:
                prediccion = f"Ocurrió un error inesperado al predecir: {e}"

    return render_template('index.html', prediccion=prediccion, barrios=BARRIOS_DISPONIBLES)

if __name__ == '__main__':
    app.run(debug=True) # debug=True recarga la app automáticamente si haces cambios