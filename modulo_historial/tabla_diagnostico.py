from flask import Blueprint, jsonify, request
from db import get_db_connection

# Blueprint exclusivo para la tabla maestra del catálogo de enfermedades
tabla_diag_bp = Blueprint('tabla_diagnostico', __name__)

# 1. VER TODO EL CATÁLOGO DE ENFERMEDADES (GET /api/diagnosticos)
@tabla_diag_bp.route('/diagnosticos', methods=['GET'])
def obtener_catalogo_diagnosticos():
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor() # Usando 'conexion' corregido
        
        cursor.execute("SELECT Diagnostico_ID, Nombre_Diagnostico FROM diagnostico")
        filas = cursor.fetchall()
        
        lista_diagnosticos = [dict(fila) for fila in filas]
        return jsonify({"ok": True, "diagnosticos": lista_diagnosticos}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# 2. AGREGAR NUEVA ENFERMEDAD AL CATÁLOGO GENERAL (POST /api/diagnosticos/crear)
@tabla_diag_bp.route('/diagnosticos/crear', methods=['POST'])
def crear_diagnostico_maestro():
    datos = request.get_json()
    nombre_diagnostico = datos.get('Nombre_Diagnostico')
    
    if not nombre_diagnostico:
        return jsonify({"ok": False, "error": "El campo Nombre_Diagnostico es obligatorio"}), 400
        
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        cursor.execute(
            "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)",
            (nombre_diagnostico,)
        )
        conexion.commit()
        
        return jsonify({
            "ok": True, 
            "mensaje": "Nueva enfermedad agregada al catálogo de ODENT",
            "Diagnostico_ID": cursor.lastrowid
        }), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()