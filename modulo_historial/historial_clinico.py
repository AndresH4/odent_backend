from flask import Blueprint, jsonify, request
from db import get_db_connection

# Creamos el Blueprint para el historial clínico
historial_bp = Blueprint('historial', __name__)

# =============================================================================
# 1. CREAR HISTORIAL CLÍNICO (POST /api/historial/crear)
# =============================================================================
@historial_bp.route('/historial/crear', methods=['POST'])
def crear_historial():
    datos = request.get_json()
    
    # Extraemos solo el dato que pide tu BD
    cita_id = datos.get('Cita_ID')
    
    # Validación simple
    if not cita_id:
        return jsonify({"ok": False, "error": "Falta el campo obligatorio (Cita_ID)"}), 400
        
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Insertamos en la tabla historial_clinico (solo requiere Cita_ID)
        cursor.execute(
            """
            INSERT INTO historial_clinico (Cita_ID) 
            VALUES (?)
            """,
            (cita_id,)
        )
        conexion.commit()
        
        # Obtenemos el ID del historial que se acaba de crear automáticamente
        nuevo_id = cursor.lastrowid
        
        return jsonify({
            "ok": True, 
            "mensaje": "Historial clínico creado con éxito",
            "Historial_ID": nuevo_id
        }), 201
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# 2. OBTENER EL HISTORIAL DE UN PACIENTE POR SU ID (GET /api/historial/paciente/<id>)
# =============================================================================
@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def obtener_historial_paciente(paciente_id):
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Consulta corregida: Solo pedimos las columnas que SÍ existen en la BD
        cursor.execute(
            """
            SELECT 
                h.Historial_ID,
                c.Cita_ID,
                c.Motivo_Consulta,
                (u_esp.Nombres || ' ' || u_esp.Apellidos) AS Especialist_Nombre
            FROM historial_clinico h
            INNER JOIN cita c ON h.Cita_ID = c.Cita_ID
            INNER JOIN agenda a ON c.Agenda_ID = a.Agenda_ID
            INNER JOIN especialista e ON a.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios u_esp ON e.Usuario_ID = u_esp.Usuario_ID
            WHERE c.Paciente_ID = ?
            ORDER BY h.Historial_ID DESC
            """,
            (paciente_id,)
        )
        
        filas = cursor.fetchall()
        lista_historial = [dict(fila) for fila in filas]
        
        return jsonify({"ok": True, "historiales": lista_historial}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()