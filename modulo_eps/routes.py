# =============================================================================
# modulo_eps/routes.py  —  FUSIONADO con modulo_config_ranking/routes.py
# =============================================================================

from flask import Blueprint, jsonify, request

from .afiliacion import (
    crear_afiliacion, obtener_afiliaciones, obtener_afiliacion_por_id,
    actualizar_afiliacion, eliminar_afiliacion, reporte_afiliados_por_eps,
)
from .eps import (
    crear_eps, obtener_eps, obtener_eps_por_id, actualizar_eps, eliminar_eps,
    obtener_eps_por_regimen,
)
from .paciente import (
    registrar_paciente, obtener_pacientes, obtener_paciente_por_id,
    actualizar_paciente, eliminar_paciente,
)
from .regimen_eps import (
    crear_regimen, obtener_regimenes, obtener_regimen_por_id,
    actualizar_regimen, eliminar_regimen,
)
from .tipo_afiliacion_eps import (
    crear_tipo_afiliacion_eps, obtener_tipos_afiliacion_eps, obtener_tipo_afiliacion_eps_por_id,
    actualizar_tipo_afiliacion_eps, eliminar_tipo_afiliacion_eps,
)
from .tabla_pregunta import (
    crear_pregunta, obtener_preguntas, obtener_pregunta_por_id,
    actualizar_pregunta, eliminar_pregunta, togglear_activa,
)
from .tabla_respuesta import (
    crear_respuesta, obtener_respuestas, obtener_respuesta_por_id,
    obtener_respuestas_por_paciente, obtener_ranking_especialistas,
    actualizar_respuesta, eliminar_respuesta,
)
from .config_ranking import (
    obtener_config,
    actualizar_config,
    toggle_estado_config,
    reporte_estado_ranking,
    reporte_historial_config,
)
from db import get_db_connection

eps_bp            = Blueprint("eps",            __name__)
config_ranking_bp = Blueprint("config_ranking", __name__)


# =============================================================================
# TIPO AFILIACIÓN EPS
# =============================================================================

@eps_bp.route('/tipo-afiliacion-eps', methods=['GET'])
def listar_tipos_afiliacion_eps():
    try:
        datos = obtener_tipos_afiliacion_eps()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-afiliacion-eps', methods=['POST'])
def nuevo_tipo_afiliacion_eps():
    body = request.get_json()
    nombre_tipo = body.get('Nombre_Tipo') if body else None
    if not nombre_tipo:
        return jsonify({"ok": False, "error": "El campo Nombre_Tipo es requerido"}), 400
    try:
        nuevo_id = crear_tipo_afiliacion_eps(nombre_tipo)
        return jsonify({"ok": True, "data": {"ID_Tipo_EPS": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-afiliacion-eps/<int:tipo_afiliacion_eps_id>', methods=['GET'])
def ver_tipo_afiliacion_eps(tipo_afiliacion_eps_id):
    try:
        registro = obtener_tipo_afiliacion_eps_por_id(tipo_afiliacion_eps_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Tipo de afiliación EPS no encontrado"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-afiliacion-eps/<int:tipo_afiliacion_eps_id>', methods=['PUT'])
def editar_tipo_afiliacion_eps(tipo_afiliacion_eps_id):
    body = request.get_json()
    nombre_tipo = body.get('Nombre_Tipo') if body else None
    if not nombre_tipo:
        return jsonify({"ok": False, "error": "El campo Nombre_Tipo es requerido"}), 400
    try:
        modificado = actualizar_tipo_afiliacion_eps(tipo_afiliacion_eps_id, nombre_tipo)
        if not modificado:
            return jsonify({"ok": False, "error": "Tipo de afiliación EPS no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Tipo de afiliación EPS actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-afiliacion-eps/<int:tipo_afiliacion_eps_id>', methods=['DELETE'])
def borrar_tipo_afiliacion_eps(tipo_afiliacion_eps_id):
    try:
        eliminado = eliminar_tipo_afiliacion_eps(tipo_afiliacion_eps_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Tipo de afiliación EPS no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Tipo de afiliación EPS eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# RÉGIMEN EPS
# =============================================================================

@eps_bp.route('/regimen-eps', methods=['GET'])
def listar_regimenes():
    try:
        datos = obtener_regimenes()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/regimen-eps', methods=['POST'])
def nuevo_regimen():
    body = request.get_json()
    nombre_regimen = body.get('Nombre_Regimen') if body else None
    if not nombre_regimen:
        return jsonify({"ok": False, "error": "El campo Nombre_Regimen es requerido"}), 400
    try:
        nuevo_id = crear_regimen(nombre_regimen)
        return jsonify({"ok": True, "data": {"ID_Regimen_EPS": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/regimen-eps/<int:regimen_id>', methods=['GET'])
def ver_regimen(regimen_id):
    try:
        registro = obtener_regimen_por_id(regimen_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Régimen no encontrado"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/regimen-eps/<int:regimen_id>', methods=['PUT'])
def editar_regimen(regimen_id):
    body = request.get_json()
    nombre_regimen = body.get('Nombre_Regimen') if body else None
    if not nombre_regimen:
        return jsonify({"ok": False, "error": "El campo Nombre_Regimen es requerido"}), 400
    try:
        modificado = actualizar_regimen(regimen_id, nombre_regimen)
        if not modificado:
            return jsonify({"ok": False, "error": "Régimen no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Régimen actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/regimen-eps/<int:regimen_id>', methods=['DELETE'])
def borrar_regimen(regimen_id):
    try:
        eliminado = eliminar_regimen(regimen_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Régimen no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Régimen eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# EPS
# =============================================================================

@eps_bp.route('/eps', methods=['GET'])
def listar_eps():
    try:
        datos = obtener_eps()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/eps/por-regimen/<int:regimen_id>', methods=['GET'])
def listar_eps_por_regimen(regimen_id):
    try:
        datos = obtener_eps_por_regimen(regimen_id)
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/eps', methods=['POST'])
def nueva_eps():
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    nombre_eps  = body.get('Nombre_EPS')
    tipo_eps_id = body.get('ID_Tipo_EPS')
    nit         = body.get('NIT')
    telefono    = body.get('Telefono')
    direccion   = body.get('Direccion')
    if not nombre_eps or not tipo_eps_id:
        return jsonify({"ok": False, "error": "Los campos Nombre_EPS e ID_Tipo_EPS son requeridos"}), 400
    try:
        nuevo_id = crear_eps(nombre_eps, tipo_eps_id, nit, telefono, direccion)
        return jsonify({"ok": True, "data": {"ID_EPS": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/eps/<int:eps_id>', methods=['GET'])
def ver_eps(eps_id):
    try:
        registro = obtener_eps_por_id(eps_id)
        if registro is None:
            return jsonify({"ok": False, "error": "EPS no encontrada"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/eps/<int:eps_id>', methods=['PUT'])
def editar_eps(eps_id):
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    nombre_eps  = body.get('Nombre_EPS')
    tipo_eps_id = body.get('ID_Tipo_EPS')
    nit         = body.get('NIT')
    telefono    = body.get('Telefono')
    direccion   = body.get('Direccion')
    if not nombre_eps or not tipo_eps_id:
        return jsonify({"ok": False, "error": "Los campos Nombre_EPS e ID_Tipo_EPS son requeridos"}), 400
    try:
        modificado = actualizar_eps(eps_id, nombre_eps, tipo_eps_id, nit, telefono, direccion)
        if not modificado:
            return jsonify({"ok": False, "error": "EPS no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "EPS actualizada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/eps/<int:eps_id>', methods=['DELETE'])
def borrar_eps(eps_id):
    try:
        eliminado = eliminar_eps(eps_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "EPS no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "EPS eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# AFILIACIÓN
# =============================================================================

@eps_bp.route('/afiliacion', methods=['GET'])
def listar_afiliaciones():
    try:
        datos = obtener_afiliaciones()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/afiliacion', methods=['POST'])
def nueva_afiliacion():
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    usuario_id       = body.get('ID_Usuario')
    eps_id           = body.get('ID_EPS')
    tipo_eps_id      = body.get('ID_Tipo_EPS')
    fecha_afiliacion = body.get('Fecha_Afiliacion')
    numero_afiliado  = body.get('Numero_Afiliado')
    estado           = body.get('Estado')
    if not all([usuario_id, eps_id, tipo_eps_id, fecha_afiliacion]):
        return jsonify({"ok": False, "error": "ID_Usuario, ID_EPS, ID_Tipo_EPS y Fecha_Afiliacion son requeridos"}), 400
    try:
        nuevo_id = crear_afiliacion(usuario_id, eps_id, tipo_eps_id, fecha_afiliacion, numero_afiliado, estado)
        return jsonify({"ok": True, "data": {"ID_Afiliacion": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/afiliacion/<int:afiliacion_id>', methods=['GET'])
def ver_afiliacion(afiliacion_id):
    try:
        registro = obtener_afiliacion_por_id(afiliacion_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Afiliación no encontrada"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/afiliacion/<int:afiliacion_id>', methods=['PUT'])
def editar_afiliacion(afiliacion_id):
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    eps_id           = body.get('ID_EPS')
    tipo_eps_id      = body.get('ID_Tipo_EPS')
    fecha_afiliacion = body.get('Fecha_Afiliacion')
    numero_afiliado  = body.get('Numero_Afiliado')
    estado           = body.get('Estado')
    if not all([eps_id, tipo_eps_id, fecha_afiliacion]):
        return jsonify({"ok": False, "error": "ID_EPS, ID_Tipo_EPS y Fecha_Afiliacion son requeridos"}), 400
    try:
        modificado = actualizar_afiliacion(afiliacion_id, eps_id, tipo_eps_id, fecha_afiliacion, numero_afiliado, estado)
        if not modificado:
            return jsonify({"ok": False, "error": "Afiliación no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Afiliación actualizada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/afiliacion/<int:afiliacion_id>', methods=['DELETE'])
def borrar_afiliacion(afiliacion_id):
    try:
        eliminado = eliminar_afiliacion(afiliacion_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Afiliación no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Afiliación eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# PACIENTE (modulo_eps)
# =============================================================================

@eps_bp.route('/paciente', methods=['GET'])
def listar_pacientes():
    try:
        datos = obtener_pacientes()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/paciente', methods=['POST'])
def nuevo_paciente():
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    usuario_id       = body.get('ID_Usuario')
    fecha_nacimiento = body.get('Fecha_Nacimiento')
    genero           = body.get('Genero')
    grupo_sanguineo  = body.get('Grupo_Sanguineo')
    alergias         = body.get('Alergias')
    antecedentes     = body.get('Antecedentes')
    observaciones    = body.get('Observaciones')
    if not usuario_id:
        return jsonify({"ok": False, "error": "El campo ID_Usuario es requerido"}), 400
    try:
        nuevo_id = registrar_paciente(usuario_id, fecha_nacimiento, genero, grupo_sanguineo, alergias, antecedentes, observaciones)
        return jsonify({"ok": True, "data": {"ID_Paciente": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/paciente/<int:paciente_id>', methods=['GET'])
def ver_paciente(paciente_id):
    try:
        registro = obtener_paciente_por_id(paciente_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/paciente/<int:paciente_id>', methods=['PUT'])
def editar_paciente(paciente_id):
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    try:
        modificado = actualizar_paciente(
            paciente_id, body.get('Fecha_Nacimiento'), body.get('Genero'),
            body.get('Grupo_Sanguineo'), body.get('Alergias'),
            body.get('Antecedentes'), body.get('Observaciones')
        )
        if not modificado:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Paciente actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/paciente/<int:paciente_id>', methods=['DELETE'])
def borrar_paciente(paciente_id):
    try:
        eliminado = eliminar_paciente(paciente_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Paciente eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# TABLA PREGUNTA (CRUD completo + toggle de estado Activa)
# =============================================================================

@eps_bp.route('/pregunta', methods=['GET'])
def listar_preguntas():
    solo_activas = request.args.get('activas', 'false').lower() == 'true'
    try:
        datos = obtener_preguntas(solo_activas=solo_activas)
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/pregunta', methods=['POST'])
def nueva_pregunta():
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    texto_pregunta = (body.get('Texto_Pregunta') or '').strip()
    orden          = body.get('Orden')
    activa         = body.get('Activa', 1)
    if not texto_pregunta:
        return jsonify({"ok": False, "error": "El campo Texto_Pregunta es requerido"}), 400
    try:
        nuevo_id = crear_pregunta(texto_pregunta, orden, activa)
        return jsonify({"ok": True, "data": {"ID_Pregunta": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/pregunta/<int:pregunta_id>', methods=['GET'])
def ver_pregunta(pregunta_id):
    try:
        registro = obtener_pregunta_por_id(pregunta_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Pregunta no encontrada"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/pregunta/<int:pregunta_id>', methods=['PUT'])
def editar_pregunta(pregunta_id):
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400
    texto_pregunta = (body.get('Texto_Pregunta') or '').strip()
    orden          = body.get('Orden')
    activa         = body.get('Activa', 1)
    if not texto_pregunta:
        return jsonify({"ok": False, "error": "El campo Texto_Pregunta es requerido"}), 400
    try:
        modificado = actualizar_pregunta(pregunta_id, texto_pregunta, orden, activa)
        if not modificado:
            return jsonify({"ok": False, "error": "Pregunta no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Pregunta actualizada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/pregunta/<int:pregunta_id>/toggle', methods=['POST'])
def toggle_pregunta(pregunta_id):
    try:
        nuevo_estado = togglear_activa(pregunta_id)
        if nuevo_estado is None:
            return jsonify({"ok": False, "error": "Pregunta no encontrada"}), 404
        return jsonify({
            "ok":      True,
            "Activa":  nuevo_estado,
            "mensaje": "Pregunta " + ("activada" if nuevo_estado == 1 else "desactivada")
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/pregunta/<int:pregunta_id>', methods=['DELETE'])
def borrar_pregunta(pregunta_id):
    try:
        eliminado = eliminar_pregunta(pregunta_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Pregunta no encontrada"}), 404
        return jsonify({
            "ok":          True,
            "mensaje":     "Pregunta eliminada correctamente",
            "ID_Pregunta": pregunta_id
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# TABLA RESPUESTA
# =============================================================================

@eps_bp.route('/respuesta', methods=['POST'])
def nueva_respuesta():
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400

    cita_id     = body.get('Cita_ID')
    pregunta_id = body.get('Pregunta_ID')
    respuesta   = body.get('Respuesta')

    if not all([cita_id, pregunta_id, respuesta is not None]):
        return jsonify({
            "ok":    False,
            "error": "Los campos Cita_ID, Pregunta_ID y Respuesta son requeridos"
        }), 400

    try:
        nuevo_id = crear_respuesta(cita_id, pregunta_id, respuesta)
        return jsonify({"ok": True, "data": {"Respuesta_ID": nuevo_id}}), 201

    except RuntimeError as re_:
        return jsonify({"ok": False, "error": str(re_), "bloqueado": True}), 403

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# VERIFICACIÓN DE ESTADO (SOLO LECTURA)
# ---------------------------------------------------------------------------

@eps_bp.route('/encuesta/estado', methods=['GET'])
def consultar_estado_encuesta():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Estado FROM config_ranking WHERE Config_ID = 1")
        fila = cur.fetchone()
        if fila is None:
            return jsonify({
                "ok":    False,
                "activo": False,
                "error": "La configuración no existe. Ejecuta init_db.py o usa PUT /config-ranking para inicializarla."
            }), 404
        estado = int(fila['Estado'])
        return jsonify({
            "ok":           True,
            "activo":       estado == 1,
            "Estado":       estado,
            "Nombre_Estado": "Activo" if estado == 1 else "Inactivo",
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "activo": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


@eps_bp.route('/respuesta/<int:respuesta_id>', methods=['DELETE'])
def borrar_respuesta(respuesta_id):
    try:
        eliminado = eliminar_respuesta(respuesta_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Respuesta no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Respuesta eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# REPORTE: RANKING DE ESPECIALISTAS
# =============================================================================

@eps_bp.route('/reporte/ranking-especialistas', methods=['GET'])
def reporte_ranking_especialistas():
    try:
        datos = obtener_ranking_especialistas()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# ESTADÍSTICAS GENERALES DEL SISTEMA
# =============================================================================

@eps_bp.route('/estadisticas-ranking', methods=['GET'])
def estadisticas_ranking():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                COUNT(DISTINCT ag.Especialista_ID)          AS total_especialistas_evaluados,
                COUNT(rr.Respuesta_ID)                      AS total_evaluaciones,
                ROUND(AVG(CAST(rr.Respuesta AS REAL)), 2)   AS promedio_general
            FROM respuesta_ranking rr
            INNER JOIN cita   c  ON rr.Cita_ID   = c.Cita_ID
            INNER JOIN agenda ag ON c.Agenda_ID  = ag.Agenda_ID
        """)
        row = cur.fetchone()
        return jsonify({
            "ok": True,
            "data": {
                "total_especialistas_evaluados": int(row['total_especialistas_evaluados'] or 0),
                "total_evaluaciones":            int(row['total_evaluaciones'] or 0),
                "promedio_general":              float(row['promedio_general'] or 0.0),
            }
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()


# =============================================================================
# REPORTES ESPECIALES
# =============================================================================

@eps_bp.route('/reporte/afiliados-por-eps', methods=['GET'])
def reporte_afiliados():
    try:
        datos = reporte_afiliados_por_eps()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/reporte/respuestas-paciente/<int:paciente_id>', methods=['GET'])
def reporte_respuestas_paciente(paciente_id):
    try:
        datos = obtener_respuestas_por_paciente(paciente_id)
        if not datos:
            return jsonify({"ok": False, "error": "No se encontraron respuestas para el paciente indicado"}), 404
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# CONFIG RANKING — GET
# =============================================================================

@config_ranking_bp.route('/config-ranking', methods=['GET'])
def leer_config_ranking():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = 1")
        fila = cur.fetchone()
        if fila is None:
            return jsonify({
                "ok":    False,
                "error": "La configuración no existe. Ejecuta init_db.py."
            }), 404
        estado = int(fila['Estado'])
        return jsonify({
            "ok": True,
            "data": {
                "Config_ID":     fila['Config_ID'],
                "Estado":        estado,
                "Nombre_Estado": "Activo" if estado == 1 else "Inactivo",
            }
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


# =============================================================================
# CONFIG RANKING — PUT (solo Estado, mantiene compatibilidad)
# =============================================================================

@config_ranking_bp.route('/config-ranking', methods=['PUT'])
def editar_config_ranking():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido."}), 400

    estado_raw = body.get("Estado")
    if estado_raw is None:
        return jsonify({"ok": False, "error": "El campo 'Estado' es requerido."}), 400

    try:
        estado = int(estado_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "'Estado' debe ser un entero (1 o 2)."}), 400

    if estado not in (1, 2):
        return jsonify({"ok": False, "error": "'Estado' debe ser 1 (Activo) o 2 (Inactivo)."}), 400

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT Config_ID FROM config_ranking WHERE Config_ID = 1")
        existe = cur.fetchone()

        if existe is None:
            cur.execute(
                "INSERT INTO config_ranking (Config_ID, Estado) VALUES (1, ?)",
                (estado,)
            )
        else:
            cur.execute(
                "UPDATE config_ranking SET Estado = ? WHERE Config_ID = 1",
                (estado,)
            )
            if cur.rowcount == 0:
                con.rollback()
                return jsonify({
                    "ok":    False,
                    "error": "El UPDATE no afectó ninguna fila. La configuración no pudo guardarse."
                }), 409

        con.commit()

        cur.execute("SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = 1")
        fila = cur.fetchone()
        if fila is None:
            return jsonify({"ok": False, "error": "Error crítico: la fila desapareció tras el commit."}), 500

        estado_confirmado = int(fila['Estado'])
        if estado_confirmado != estado:
            return jsonify({
                "ok":    False,
                "error": "Mismatch tras commit: se pidió Estado={}, BD tiene Estado={}.".format(estado, estado_confirmado)
            }), 500

        return jsonify({
            "ok":      True,
            "mensaje": "Configuración actualizada correctamente.",
            "data": {
                "Config_ID":     fila['Config_ID'],
                "Estado":        estado_confirmado,
                "Nombre_Estado": "Activo" if estado_confirmado == 1 else "Inactivo",
            }
        }), 200

    except Exception as e:
        if con:
            try:
                con.rollback()
            except Exception:
                pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


# =============================================================================
# CONFIG RANKING — PUT /config-ranking/guardar-todo
#
# Endpoint atómico que persiste en una sola transacción SQLite:
#   1. El Estado del toggle (activo/inactivo)
#   2. El lote completo de preguntas modificadas (preguntas_modificadas[])
#
# Si cualquier operación falla, se ejecuta ROLLBACK y no queda ningún
# cambio parcialmente guardado. El frontend llama a este endpoint desde
# guardarCambiosConfig() con el payload:
#   {
#     "Estado": 1 | 2,
#     "preguntas_modificadas": [
#       { "ID_Pregunta": int, "Texto_Pregunta": str, "Orden": int, "Activa": int },
#       ...
#     ]
#   }
# =============================================================================

@config_ranking_bp.route('/config-ranking/guardar-todo', methods=['PUT'])
def guardar_todo_config_ranking():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido."}), 400

    # ── Validar Estado ────────────────────────────────────────────────────────
    estado_raw = body.get("Estado")
    if estado_raw is None:
        return jsonify({"ok": False, "error": "El campo 'Estado' es requerido."}), 400
    try:
        estado = int(estado_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "'Estado' debe ser un entero (1 o 2)."}), 400
    if estado not in (1, 2):
        return jsonify({"ok": False, "error": "'Estado' debe ser 1 (Activo) o 2 (Inactivo)."}), 400

    # ── Validar lista de preguntas ────────────────────────────────────────────
    preguntas_raw = body.get("preguntas_modificadas", [])
    if not isinstance(preguntas_raw, list):
        return jsonify({"ok": False, "error": "'preguntas_modificadas' debe ser un array."}), 400

    preguntas_validas = []
    for idx, p in enumerate(preguntas_raw):
        pid   = p.get("ID_Pregunta")
        texto = (p.get("Texto_Pregunta") or "").strip()
        if not pid or not texto:
            return jsonify({
                "ok":    False,
                "error": "Pregunta en índice {} inválida: se requieren ID_Pregunta y Texto_Pregunta.".format(idx)
            }), 400
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "ID_Pregunta en índice {} debe ser entero.".format(idx)}), 400

        orden  = p.get("Orden",  0)
        activa = p.get("Activa", 1)
        try:
            orden  = int(orden)
            activa = int(activa)
        except (TypeError, ValueError):
            orden  = 0
            activa = 1

        preguntas_validas.append({
            "ID_Pregunta":    pid,
            "Texto_Pregunta": texto,
            "Orden":          orden,
            "Activa":         activa,
        })

    # ── Transacción única ─────────────────────────────────────────────────────
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # 1. Persistir Estado en config_ranking
        cur.execute("SELECT Config_ID FROM config_ranking WHERE Config_ID = 1")
        existe = cur.fetchone()
        if existe is None:
            cur.execute(
                "INSERT INTO config_ranking (Config_ID, Estado) VALUES (1, ?)",
                (estado,)
            )
        else:
            cur.execute(
                "UPDATE config_ranking SET Estado = ? WHERE Config_ID = 1",
                (estado,)
            )
            if cur.rowcount == 0:
                con.rollback()
                return jsonify({
                    "ok":    False,
                    "error": "No se pudo actualizar el Estado en config_ranking."
                }), 409

        # 2. Actualizar cada pregunta modificada
        preguntas_actualizadas = []
        for p in preguntas_validas:
            cur.execute(
                """
                UPDATE tabla_pregunta
                   SET Texto_Pregunta = ?,
                       Orden          = ?,
                       Activa         = ?
                 WHERE ID_Pregunta    = ?
                """,
                (p["Texto_Pregunta"], p["Orden"], p["Activa"], p["ID_Pregunta"])
            )
            if cur.rowcount == 0:
                # La pregunta no existe — no es error fatal, se registra y continúa
                continue
            preguntas_actualizadas.append({
                "ID_Pregunta":    p["ID_Pregunta"],
                "Texto_Pregunta": p["Texto_Pregunta"],
            })

        # 3. Commit único para todo el lote
        con.commit()

        # 4. Releer Estado confirmado desde BD
        cur.execute("SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = 1")
        fila = cur.fetchone()
        if fila is None:
            return jsonify({"ok": False, "error": "Error crítico: la fila de configuración desapareció tras el commit."}), 500

        estado_confirmado = int(fila["Estado"])
        if estado_confirmado != estado:
            return jsonify({
                "ok":    False,
                "error": "Mismatch tras commit: se pidió Estado={}, BD tiene Estado={}.".format(
                    estado, estado_confirmado
                )
            }), 500

        return jsonify({
            "ok":      True,
            "mensaje": "Todos los cambios guardados correctamente.",
            "data": {
                "Config_ID":             fila["Config_ID"],
                "Estado":                estado_confirmado,
                "Nombre_Estado":         "Activo" if estado_confirmado == 1 else "Inactivo",
                "preguntas_actualizadas": preguntas_actualizadas,
                "total_preguntas":       len(preguntas_actualizadas),
            }
        }), 200

    except Exception as e:
        if con:
            try:
                con.rollback()
            except Exception:
                pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


# =============================================================================
# CONFIG RANKING — toggle Activo ↔ Inactivo (directo en SQLite)
# =============================================================================

@config_ranking_bp.route('/config-ranking/toggle', methods=['POST'])
def toggle_config_ranking():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Estado FROM config_ranking WHERE Config_ID = 1")
        fila = cur.fetchone()
        if fila is None:
            return jsonify({"ok": False, "error": "Configuración no encontrada."}), 404
        nuevo_estado = 2 if int(fila['Estado']) == 1 else 1
        cur.execute(
            "UPDATE config_ranking SET Estado = ? WHERE Config_ID = 1",
            (nuevo_estado,)
        )
        if cur.rowcount == 0:
            con.rollback()
            return jsonify({"ok": False, "error": "No se pudo actualizar el estado."}), 409
        con.commit()
        label = "activado" if nuevo_estado == 1 else "desactivado"
        return jsonify({
            "ok":      True,
            "mensaje": "Ranking {}.".format(label),
            "data": {
                "Config_ID":     1,
                "Estado":        nuevo_estado,
                "Nombre_Estado": "Activo" if nuevo_estado == 1 else "Inactivo",
            }
        }), 200
    except Exception as e:
        if con:
            try:
                con.rollback()
            except Exception:
                pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


# =============================================================================
# CONFIG RANKING — reporte consolidado con estadísticas
# =============================================================================

@config_ranking_bp.route('/config-ranking/reporte', methods=['GET'])
def reporte_config_ranking():
    try:
        data = reporte_estado_ranking()
        return jsonify({"ok": True, "data": data}), 200
    except RuntimeError as re_:
        return jsonify({"ok": False, "error": str(re_)}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# CONFIG RANKING — historial de cambios (aseguramiento_datos)
# =============================================================================

@config_ranking_bp.route('/config-ranking/historial', methods=['GET'])
def historial_config_ranking():
    try:
        data = reporte_historial_config()
        return jsonify({"ok": True, "data": data}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500