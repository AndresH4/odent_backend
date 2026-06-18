from flask import Blueprint, jsonify, request
from db import get_db_connection

# Creamos el Blueprint para la tabla de puntuaciones
puntuacion_bp = Blueprint('puntuacion', __name__)

# =============================================================================
# 1. REGISTRAR UNA NUEVA PUNTUACIÓN (POST /api/puntuacion/crear)
# =============================================================================
@puntuacion_bp.route('/puntuacion/crear', methods=['POST'])
def crear_puntuacion():
    datos = request.get_json()

    # Extraemos solo los campos que pide tu base de datos real
    especialista_id = datos.get('Especialista_ID')
    respuesta_id = datos.get('Respuesta_ID')

    if not all([especialista_id, respuesta_id]):
        return jsonify({"ok": False, "error": "Faltan datos obligatorios (Especialista_ID, Respuesta_ID)"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        # Retiramos dictionary=True
        cursor = conexion.cursor()

        # Cambiamos los %s por signos de interrogación (?)
        cursor.execute(
            """
            INSERT INTO puntuacion_especialista (Especialista_ID, Respuesta_ID)
            VALUES (?, ?)
            """,
            (especialista_id, respuesta_id)
        )
        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Puntuación vinculada al especialista correctamente"
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        # Cierre seguro del cursor y la conexión
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =============================================================================
# 2. VER PUNTUACIONES DE UN ESPECIALISTA (GET /api/puntuacion/especialista/<id>)
# =============================================================================
@puntuacion_bp.route('/puntuacion/especialista/<int:especialista_id>', methods=['GET'])
def obtener_puntuaciones_especialista(especialista_id):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        # Retiramos dictionary=True
        cursor = conexion.cursor()

        # Restauramos la concatenación con || y el marcador ? para SQLite
        cursor.execute(
            """
            SELECT
                pe.Puntuacion_ID,
                rr.Respuesta AS Puntaje,
                pr.Texto_Pregunta,
                (u.Nombres || ' ' || u.Apellidos) AS Nombre_Paciente
            FROM puntuacion_especialista pe
            INNER JOIN respuesta_ranking rr ON pe.Respuesta_ID = rr.Respuesta_ID
            INNER JOIN preguntas_ranking pr ON rr.Preguntas_ID = pr.Preguntas_ID
            INNER JOIN cita c ON rr.Cita_ID = c.Cita_ID
            INNER JOIN paciente p ON c.Paciente_ID = p.Paciente_ID
            INNER JOIN usuarios u ON p.Usuario_ID = u.Usuario_ID
            WHERE pe.Especialista_ID = ?
            ORDER BY pe.Puntuacion_ID DESC
            """,
            (especialista_id,)
        )

        filas = cursor.fetchall()
        
        # Convertimos los objetos Row de SQLite a diccionarios
        lista_puntuaciones = [dict(fila) for fila in filas]

        return jsonify({"ok": True, "puntuaciones": lista_puntuaciones}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        # Cierre seguro del cursor y la conexión
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()