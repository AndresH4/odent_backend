from flask import Blueprint, jsonify, request
from db import get_db_connection

# Blueprint exclusivo para la tabla intermedia de asociaciones médicas
historial_diag_bp = Blueprint('historial_diagnostico', __name__)

# 1. ASOCIAR ENFERMEDAD A UN REPORTE CLÍNICO (POST /api/historial-diagnostico/agregar)
@historial_diag_bp.route('/historial-diagnostico/agregar', methods=['POST'])
def agregar_diagnostico_a_historial():
    datos = request.get_json()
    historial_id = datos.get('Historial_ID')
    diagnostico_id = datos.get('Diagnostico_ID')
    
    if not historial_id or not diagnostico_id:
        return jsonify({"ok": False, "error": "Faltan campos obligatorios (Historial_ID, Diagnostico_ID)"}), 400
        
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor() # Usando 'conexion' corregido
        
        cursor.execute(
            "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
            (historial_id, diagnostico_id)
        )
        conexion.commit()
        
        return jsonify({"ok": True, "mensaje": "Enfermedad vinculada correctamente al folio del paciente"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()


# 2. VER QUÉ ENFERMEDADES TIENE UN FOLIO CLÍNICO (GET /api/historial-diagnostico/<id>)
@historial_diag_bp.route('/historial-diagnostico/<int:historial_id>', methods=['GET'])
def obtener_diagnosticos_de_historial(historial_id):
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        
        # Unimos la intermedia con la maestra para transformar el ID en texto legible
        cursor.execute(
            """
            SELECT hd.Historial_ID, hd.Diagnostico_ID, d.Nombre_Diagnostico
            FROM historial_diagnostico hd
            INNER JOIN diagnostico d ON hd.Diagnostico_ID = d.Diagnostico_ID
            WHERE hd.Historial_ID = ?
            """,
            (historial_id,)
        )
        filas = cursor.fetchall()
        lista_resultados = [dict(fila) for fila in filas]
        
        return jsonify({"ok": True, "diagnosticos_asignados": lista_resultados}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()