from flask import Blueprint, jsonify, request
from db import get_db_connection

# Creamos el Blueprint para los tratamientos
tratamiento_bp = Blueprint('tratamiento', __name__)

# =============================================================================
# 1. REGISTRAR UN TRATAMIENTO (POST /api/tratamiento/crear)
# =============================================================================
@tratamiento_bp.route('/tratamiento/crear', methods=['POST'])
def crear_tratamiento():
    datos = request.get_json()

    historial_id = datos.get('Historial_ID')
    descripcion = datos.get('Descripcion')

    # Validamos campos obligatorios
    if not historial_id or not descripcion:
        return jsonify({"ok": False, "error": "Faltan campos obligatorios (Historial_ID, Descripcion)"}), 400

    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        # Retiramos dictionary=True para la compatibilidad con SQLite
        cursor = conexion.cursor()

        # Cambiamos los %s por signos de interrogación (?)
        cursor.execute(
            """
            INSERT INTO tratamiento (Historial_ID, Descripcion)
            VALUES (?, ?)
            """,
            (historial_id, descripcion)
        )
        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Tratamiento registrado con éxito en el historial",
            "Tratamiento_ID": cursor.lastrowid
        }), 201

    except Exception as e:
        # Si el Historial_ID no existe, saltará un error por la restricción de llave foránea
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        # Cierre seguro del cursor y la conexión
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =============================================================================
# 2. VER TRATAMIENTOS DE UN HISTORIAL CLÍNICO (GET /api/tratamiento/historial/<id>)
# =============================================================================
@tratamiento_bp.route('/tratamiento/historial/<int:historial_id>', methods=['GET'])
def obtener_tratamientos_historial(historial_id):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        # Retiramos dictionary=True
        cursor = conexion.cursor()

        # Restauramos el marcador ? para SQLite
        cursor.execute(
            """
            SELECT Tratamiento_ID, Historial_ID, Descripcion
            FROM tratamiento
            WHERE Historial_ID = ?
            """,
            (historial_id,)
        )

        filas = cursor.fetchall()
        
        # Convertimos los objetos Row de SQLite a diccionarios estándar
        lista_tratamientos = [dict(fila) for fila in filas]

        return jsonify({"ok": True, "tratamientos": lista_tratamientos}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        # Cierre seguro del cursor y la conexión
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()