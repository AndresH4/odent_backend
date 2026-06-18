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
    cita_id = datos.get('Cita_ID')

    if not cita_id:
        return jsonify({"ok": False, "error": "Falta el campo obligatorio (Cita_ID)"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        # SQLite no usa dictionary=True aquí, la conversión se hace en db.py o al final
        cursor = conexion.cursor()

        # Usamos (?) propio de SQLite en lugar de %s
        cursor.execute(
            """
            INSERT INTO historial_clinico (Cita_ID)
            VALUES (?)
            """,
            (cita_id,)
        )
        conexion.commit()

        nuevo_id = cursor.lastrowid

        return jsonify({
            "ok": True,
            "mensaje": "Historial clínico creado con éxito",
            "Historial_ID": nuevo_id
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =============================================================================
# 2. OBTENER EL HISTORIAL DE UN PACIENTE POR SU ID (GET /api/historial/paciente/<id>)
# =============================================================================
@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def obtener_historial_paciente(paciente_id):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        # Usamos (?) para variables y (||) para concatenar textos en SQLite
        cursor.execute(
            """
            SELECT
                h.Historial_ID,
                c.Cita_ID,
                c.Motivo_Consulta,
                (u_esp.Nombres || ' ' || u_esp.Apellidos) AS Especialista_Nombre
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
        
        # Como SQLite devuelve objetos tipo "Row", los convertimos a diccionarios
        # para que Flask los pueda transformar a JSON sin errores.
        lista_historial = [dict(fila) for fila in filas]

        return jsonify({"ok": True, "historiales": lista_historial}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()