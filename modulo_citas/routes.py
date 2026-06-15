from flask import Blueprint, request, jsonify
import sqlite3
from db import get_db_connection
from . import cita

citas_bp = Blueprint('citas_bp', __name__)


# =============================================================================
# CITAS — LISTAR TODAS
# =============================================================================
@citas_bp.route('/citas', methods=['GET'])
def get_citas():
    return jsonify(cita.read_all_citas())


# =============================================================================
# CITAS — CREAR
# =============================================================================
@citas_bp.route('/citas', methods=['POST'])
def add_cita():
    datos = request.get_json() or {}

    paciente_id = datos.get('paciente_id')
    agenda_id = datos.get('agenda_id')
    motivo_consulta = datos.get('motivo_consulta')

    if not paciente_id or not agenda_id or not motivo_consulta:
        return jsonify({"ok": False, "error": "Datos incompletos"}), 400

    res = cita.create_cita(paciente_id, agenda_id, motivo_consulta)
    return jsonify(res), (201 if res.get('ok') else 400)


# =============================================================================
# CITAS — GET / PUT / DELETE POR ID
# =============================================================================
@citas_bp.route('/citas/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def crud_cita(id):

    # -------------------------
    # GET por ID
    # -------------------------
    if request.method == 'GET':
        data = cita.read_cita_by_id(id)
        if not data:
            return jsonify({"error": "Cita no encontrada"}), 404
        return jsonify(data)


    # -------------------------
    # UPDATE
    # -------------------------
    if request.method == 'PUT':
        datos = request.get_json() or {}
        res = cita.update_cita(id, datos.get('motivo_consulta'))
        return jsonify(res), (200 if res.get('ok') else 400)


    # -------------------------
    # DELETE
    # -------------------------
    if request.method == 'DELETE':
        res = cita.delete_cita(id)
        return jsonify(res), (200 if res.get('ok') else 400)


# =============================================================================
# REPORTES DE CITAS
# =============================================================================
@citas_bp.route('/citas/reporte/estado', methods=['GET'])
def reporte_estado():
    return jsonify(cita.reporte_citas_por_estado())


@citas_bp.route('/citas/reporte/fecha', methods=['GET'])
def reporte_fecha():
    return jsonify(cita.reporte_citas_por_fecha())