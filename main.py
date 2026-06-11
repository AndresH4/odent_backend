from flask import Flask, jsonify, request
from flask_cors import CORS  # Permite la comunicación con el frontend separado
import sqlite3

app = Flask(__name__)
CORS(app)  # Esto habilita que tu frontend acceda a las rutas de la API

def conectar_db():
    """Establece una conexión limpia con la base de datos SQLite."""
    conexion = sqlite3.connect('odent.db')
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion

@app.route('/api/usuarios', methods=['GET'])
def obtener_usuarios():
    conexion = None
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute("SELECT Usuario_ID, Nombres, Apellidos, Correo FROM usuarios")
        filas = cursor.fetchall()
        lista_usuarios = [dict(fila) for fila in filas]
        return jsonify(lista_usuarios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()

@app.route('/api/cita/crear', methods=['POST'])
def crear_cita():
    datos = request.get_json()
    paciente_id = datos.get('Paciente_ID')
    agenda_id = datos.get('Agenda_ID')
    motivo = datos.get('Motivo_Consulta')
    
    conexion = None
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (paciente_id, agenda_id, motivo)
        )
        conexion.commit()
        return jsonify({"status": "Cita registrada con éxito"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()

if __name__ == '__main__':
    app.run(debug=True)