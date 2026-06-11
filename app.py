from flask import Flask, jsonify, request
from flask_cors import CORS

# IMPORTANTE: Importamos la función de conexión desde nuestro archivo db.py
from db import get_db_connection

app = Flask(__name__)

# Habilitamos CORS para que nuestro frontend (HTML/JS) pueda hacer peticiones sin ser bloqueado
CORS(app)

# ==========================================
# RUTAS DE LA API (Endpoints)
# ==========================================

@app.route('/api/usuarios', methods=['GET'])
def obtener_usuarios():
    """Ejemplo de ruta GET: Pide información a la base de datos y la devuelve."""
    conexion = None
    try:
        # Llamamos al portero para que nos abra la conexión
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Hacemos la consulta SQL
        cursor.execute("SELECT Usuario_ID, Nombres, Apellidos, Correo FROM usuarios")
        filas = cursor.fetchall()
        
        # Transformamos las filas a una lista de diccionarios
        lista_usuarios = [dict(fila) for fila in filas]
        
        # Devolvemos la lista en formato JSON al Frontend
        return jsonify(lista_usuarios), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Siempre, SIEMPRE cerramos la conexión al terminar
        if conexion:
            conexion.close()


@app.route('/api/cita/crear', methods=['POST'])
def crear_cita():
    """Ejemplo de ruta POST: Recibe información del Frontend y la guarda."""
    # Obtenemos el JSON que mandó el JavaScript
    datos = request.get_json()
    
    paciente_id = datos.get('Paciente_ID')
    agenda_id = datos.get('Agenda_ID')
    motivo = datos.get('Motivo_Consulta')
    
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Insertamos los datos. Fíjate que NO mandamos el Cita_ID, porque SQLite
        # lo va a generar automáticamente (AUTOINCREMENT)
        cursor.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (paciente_id, agenda_id, motivo)
        )
        
        # Guardamos los cambios permanentemente
        conexion.commit()
        
        return jsonify({"status": "Cita registrada con éxito"}), 201
        
    except Exception as e:
        # Si algo falla (ej. el Paciente_ID no existe y salta la llave foránea), devolvemos el error
        return jsonify({"error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    # Arrancamos el servidor de Flask en modo debug para ver los errores en la consola
    app.run(debug=True)