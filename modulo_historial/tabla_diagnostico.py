from flask import Blueprint, jsonify, request
from db import get_db_connection

# Blueprint exclusivo para la tabla maestra del catálogo de enfermedades
tabla_diag_bp = Blueprint('tabla_diagnostico', __name__)


def _row_to_dict(fila):
    """
    Serializa una fila de diagnostico al formato canónico requerido por el frontend.
    Retorna: {'id': ..., 'codigo': ..., 'nombre': ...}
    """
    return {
        'id':     fila['Diagnostico_ID'],
        'codigo': fila['Codigo']          if fila['Codigo'] else '',
        'nombre': fila['Nombre_Diagnostico'],
    }


# =============================================================================
# 1. VER TODO EL CATÁLOGO DE ENFERMEDADES (GET /api/diagnosticos)
# =============================================================================
@tabla_diag_bp.route('/diagnosticos', methods=['GET'])
def obtener_catalogo_diagnosticos():
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = __import__('sqlite3').Row
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT Diagnostico_ID, Codigo, Nombre_Diagnostico "
            "FROM diagnostico "
            "ORDER BY Codigo"
        )
        filas = cursor.fetchall()
        lista_diagnosticos = [_row_to_dict(f) for f in filas]

        return jsonify({"ok": True, "data": lista_diagnosticos}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# 2. AGREGAR NUEVA ENFERMEDAD AL CATÁLOGO GENERAL (POST /api/diagnosticos/crear)
# =============================================================================
@tabla_diag_bp.route('/diagnosticos/crear', methods=['POST'])
def crear_diagnostico_maestro():
    datos              = request.get_json() or {}
    nombre_diagnostico = datos.get('Nombre_Diagnostico', '').strip()
    codigo             = datos.get('Codigo', '').strip().upper().replace('.', '')

    if not nombre_diagnostico:
        return jsonify({"ok": False, "error": "El campo Nombre_Diagnostico es obligatorio"}), 400

    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = __import__('sqlite3').Row
        cursor = conexion.cursor()

        cursor.execute(
            "INSERT INTO diagnostico (Codigo, Nombre_Diagnostico) VALUES (?, ?)",
            (codigo if codigo else None, nombre_diagnostico)
        )
        conexion.commit()

        nuevo_id = cursor.lastrowid
        cursor.execute(
            "SELECT Diagnostico_ID, Codigo, Nombre_Diagnostico FROM diagnostico WHERE Diagnostico_ID = ?",
            (nuevo_id,)
        )
        fila = cursor.fetchone()

        return jsonify({
            "ok":      True,
            "mensaje": "Nueva enfermedad agregada al catálogo de ODENT",
            "data":    _row_to_dict(fila),
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()