import os
import time
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

# Configuración
MASTER_FILE = "maestro/Cartera_maestro_datas.xlsx"
DB_FILE = "cartera.db"
TABLE_NAME = "maestro"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cargar_o_actualizar_db():
    if os.path.exists(DB_FILE) and os.path.exists(MASTER_FILE):
        db_time = os.path.getmtime(DB_FILE)
        master_time = os.path.getmtime(MASTER_FILE)

        if master_time < db_time:
            print("📦 Usando base de datos existente.")
            return sqlite3.connect(DB_FILE)

    print("🔄 Actualizando base de datos desde Excel...")
    try:
        start = time.time()
        df = pd.read_excel(MASTER_FILE)
        end = time.time()
        print(f"⏱️ Carga Excel: {round(end - start, 2)} segundos.")

        start = time.time()
        conn = sqlite3.connect(DB_FILE)
        df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
        end = time.time()
        print(f"💾 Guardado en SQLite: {round(end - start, 2)} segundos.")
        print("✅ Base de datos actualizada.")
        return conn
    except Exception as e:
        print("❌ Error al crear base:", e)
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    conn = cargar_o_actualizar_db()
    if not conn:
        return "Error cargando base de datos.", 500

    if request.method == "POST":
        if 'archivo_consulta' not in request.files:
            return "No se seleccionó archivo."

        archivo = request.files['archivo_consulta']
        if archivo.filename == '':
            return "Nombre de archivo vacío."

        if archivo and allowed_file(archivo.filename):
            filename = secure_filename(archivo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(filepath)

            try:
                if filename.endswith('.csv'):
                    df_consulta = pd.read_csv(filepath)
                else:
                    df_consulta = pd.read_excel(filepath)

                if 'Operacion' not in df_consulta.columns:
                    return "Falta la columna 'Operacion' en el archivo."

                operaciones = "','".join(df_consulta['Operacion'].astype(str))
                query = f"SELECT * FROM {TABLE_NAME} WHERE Operacion IN ('{operaciones}')"
                resultados = pd.read_sql_query(query, conn)

                output_path = os.path.join(UPLOAD_FOLDER, "resultado.csv")
                resultados.to_csv(output_path, index=False)

                return render_template("resultados.html", tabla=resultados.to_html(index=False), archivo="resultado.csv")

            except Exception as e:
                return f"❌ Error procesando archivo: {str(e)}"

    return render_template("index.html")


@app.route("/descargar/<archivo>")
def descargar(archivo):
    return send_file(os.path.join(UPLOAD_FOLDER, archivo), as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)