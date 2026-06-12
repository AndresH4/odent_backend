from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3  # Importación requerida para habilitar el formateador de filas

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
        conexion.row_factory = sqlite3.Row  # Asegura el formateo de diccionarios en esta ruta tradicional
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

# =============================================================================
# LÍNEAS AÑADIDAS: CONEXIÓN CON LA INTERFAZ DE CREACIÓN Y SUS CATÁLOGOS
# =============================================================================
from flask import render_template

@app.route('/vista/crear_usuario')
def vista_creacion_usuario():
    """Ruta encargada de mostrar la interfaz gráfica de registro"""
    return render_template('creacion.html')


@app.route('/roles', methods=['GET'])
def get_roles_creacion():
    """Suministra la lista de roles directamente de la base de datos al select de la interfaz"""
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row 
        cursor = conexion.cursor()
        
        # CORRECCIÓN DE LA CONSULTA: Usamos las columnas reales de tu SQLite (ROL_ID, DESCRIPCION) 
        # y renombramos DESCRIPCION como Nombre_Rol para mantener la compatibilidad con creacion.js
        cursor.execute("SELECT ROL_ID, DESCRIPCION AS Nombre_Rol FROM rol")
        
        filas = cursor.fetchall()
        lista_roles = [dict(fila) for fila in filas]
        return jsonify(lista_roles), 200
    except Exception as e:
        print(f"\n❌ ERROR REAL EN /roles: {str(e)}\n")
        return jsonify({"error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


@app.route('/usuarios', methods=['POST'])
def add_usuario_creacion():
    """Recibe los datos estructurados desde creacion.js y los inserta en la base de datos"""
    datos = request.get_json()
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        cursor.execute(
            """INSERT INTO usuarios (Nombres, Apellidos, Documento, Telefono, Correo, Contrasena, Rol_ID, Genero_ID, Tipo_Documento_ID, Estado_ID) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datos.get('nombres'), 
                datos.get('apellidos'), 
                datos.get('documento'), 
                datos.get('telefono'), 
                datos.get('correo'), 
                datos.get('contrasena'), 
                datos.get('rol_id'), 
                datos.get('genero_id', 1), 
                datos.get('tipo_documento_id', 1), 
                datos.get('estado_id', 1)
            )
        )
        conexion.commit()
        return jsonify({"ok": True, "status": "Usuario creado con éxito en SQLite"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    # Arrancamos el servidor de Flask en modo debug para ver los errores en la consola
    app.run(debug=True)