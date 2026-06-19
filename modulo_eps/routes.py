# =============================================================================
# modulo_eps/routes.py
#
# Registro en app.py:
#   from modulo_eps.routes import eps_bp
#   app.register_blueprint(eps_bp, url_prefix='/api')
#
# Esto expone:
#   GET  /api/afiliacion                           ← cargarAfiliacionEPS() en paciente.js
#   GET  /api/afiliacion                           ← cargarPerfilClinicoPaciente() en especialista.js
#   GET  /api/paciente                             ← cargarPacientesEPS() en administrador.js
#   GET  /api/pregunta                             ← _abrirRanking() en paciente.js
#   GET  /api/reporte/afiliados-por-eps            ← cargarReporteAfiliados() en administrador.js
#   GET  /api/reporte/respuestas-paciente/<id>     ← cargarRespuestasFormulario() en especialista.js
#   GET  /api/reporte/ranking-especialistas        ← ranking dashboard
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
from .tipo_eps import (
    crear_tipo_eps, obtener_tipos_eps, obtener_tipo_eps_por_id,
    actualizar_tipo_eps, eliminar_tipo_eps,
)
from .tabla_pregunta import (
    crear_pregunta, obtener_preguntas, obtener_pregunta_por_id,
    actualizar_pregunta, eliminar_pregunta,
)
from .tabla_respuesta import (
    crear_respuesta, obtener_respuestas, obtener_respuesta_por_id,
    obtener_respuestas_por_paciente, obtener_ranking_especialistas,
    actualizar_respuesta, eliminar_respuesta,
)

eps_bp = Blueprint("eps", __name__)


# =============================================================================
# TIPO EPS
# =============================================================================

@eps_bp.route('/tipo-eps', methods=['GET'])
def listar_tipos_eps():
    try:
        datos = obtener_tipos_eps()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-eps', methods=['POST'])
def nuevo_tipo_eps():
    body = request.get_json()
    nombre_tipo = body.get('Nombre_Tipo') if body else None
    if not nombre_tipo:
        return jsonify({"ok": False, "error": "El campo Nombre_Tipo es requerido"}), 400
    try:
        nuevo_id = crear_tipo_eps(nombre_tipo)
        return jsonify({"ok": True, "data": {"ID_Tipo_EPS": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-eps/<int:tipo_eps_id>', methods=['GET'])
def ver_tipo_eps(tipo_eps_id):
    try:
        registro = obtener_tipo_eps_por_id(tipo_eps_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Tipo de EPS no encontrado"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-eps/<int:tipo_eps_id>', methods=['PUT'])
def editar_tipo_eps(tipo_eps_id):
    body = request.get_json()
    nombre_tipo = body.get('Nombre_Tipo') if body else None
    if not nombre_tipo:
        return jsonify({"ok": False, "error": "El campo Nombre_Tipo es requerido"}), 400
    try:
        modificado = actualizar_tipo_eps(tipo_eps_id, nombre_tipo)
        if not modificado:
            return jsonify({"ok": False, "error": "Tipo de EPS no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Tipo de EPS actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/tipo-eps/<int:tipo_eps_id>', methods=['DELETE'])
def borrar_tipo_eps(tipo_eps_id):
    try:
        eliminado = eliminar_tipo_eps(tipo_eps_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Tipo de EPS no encontrado"}), 404
        return jsonify({"ok": True, "mensaje": "Tipo de EPS eliminado correctamente"}), 200
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
        return jsonify({
            "ok": False,
            "error": "Los campos Nombre_EPS e ID_Tipo_EPS son requeridos"
        }), 400

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
        return jsonify({
            "ok": False,
            "error": "Los campos Nombre_EPS e ID_Tipo_EPS son requeridos"
        }), 400

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
# Consumido por:
#   - paciente.js._cargarAfiliacionEPS()  → GET /api/afiliacion
#   - especialista.js.cargarPerfilClinicoPaciente() → GET /api/afiliacion
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
        return jsonify({
            "ok": False,
            "error": "Los campos ID_Usuario, ID_EPS, ID_Tipo_EPS y Fecha_Afiliacion son requeridos"
        }), 400

    try:
        nuevo_id = crear_afiliacion(
            usuario_id, eps_id, tipo_eps_id,
            fecha_afiliacion, numero_afiliado, estado
        )
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
        return jsonify({
            "ok": False,
            "error": "Los campos ID_EPS, ID_Tipo_EPS y Fecha_Afiliacion son requeridos"
        }), 400

    try:
        modificado = actualizar_afiliacion(
            afiliacion_id, eps_id, tipo_eps_id,
            fecha_afiliacion, numero_afiliado, estado
        )
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
# Consumido por:
#   - administrador.js.cargarPacientesEPS() → GET /api/paciente
#   - administrador.js.renderUsuarios()     → GET /api/paciente
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
        nuevo_id = registrar_paciente(
            usuario_id, fecha_nacimiento, genero,
            grupo_sanguineo, alergias, antecedentes, observaciones
        )
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

    fecha_nacimiento = body.get('Fecha_Nacimiento')
    genero           = body.get('Genero')
    grupo_sanguineo  = body.get('Grupo_Sanguineo')
    alergias         = body.get('Alergias')
    antecedentes     = body.get('Antecedentes')
    observaciones    = body.get('Observaciones')

    try:
        modificado = actualizar_paciente(
            paciente_id, fecha_nacimiento, genero,
            grupo_sanguineo, alergias, antecedentes, observaciones
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
# TABLA PREGUNTA
# Consumido por:
#   - paciente.js._abrirRanking() → GET /api/pregunta
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

    texto_pregunta = body.get('Texto_Pregunta')
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

    texto_pregunta = body.get('Texto_Pregunta')
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


@eps_bp.route('/pregunta/<int:pregunta_id>', methods=['DELETE'])
def borrar_pregunta(pregunta_id):
    try:
        eliminado = eliminar_pregunta(pregunta_id)
        if not eliminado:
            return jsonify({"ok": False, "error": "Pregunta no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Pregunta eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# TABLA RESPUESTA (modulo_eps)
# NOTA: El endpoint POST /api/respuesta es manejado por modulo_citas/routes.py
# para garantizar el Cita_ID explícito desde el frontend.
# Estos endpoints son para gestión administrativa de respuestas.
# =============================================================================

@eps_bp.route('/respuesta', methods=['GET'])
def listar_respuestas():
    try:
        datos = obtener_respuestas()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/respuesta/<int:respuesta_id>', methods=['GET'])
def ver_respuesta(respuesta_id):
    try:
        registro = obtener_respuesta_por_id(respuesta_id)
        if registro is None:
            return jsonify({"ok": False, "error": "Respuesta no encontrada"}), 404
        return jsonify({"ok": True, "data": registro}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/respuesta/<int:respuesta_id>', methods=['PUT'])
def editar_respuesta(respuesta_id):
    body = request.get_json()
    if not body:
        return jsonify({"ok": False, "error": "Cuerpo JSON requerido"}), 400

    texto_respuesta = body.get('Texto_Respuesta')
    if not texto_respuesta:
        return jsonify({"ok": False, "error": "El campo Texto_Respuesta es requerido"}), 400

    try:
        modificado = actualizar_respuesta(respuesta_id, texto_respuesta)
        if not modificado:
            return jsonify({"ok": False, "error": "Respuesta no encontrada"}), 404
        return jsonify({"ok": True, "mensaje": "Respuesta actualizada correctamente"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


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
# REPORTES ESPECIALES
# Consumido por:
#   - administrador.js.cargarReporteAfiliados() → GET /api/reporte/afiliados-por-eps
#   - especialista.js.cargarRespuestasFormulario() → GET /api/reporte/respuestas-paciente/<id>
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
            return jsonify({
                "ok": False,
                "error": "No se encontraron respuestas para el paciente indicado"
            }), 404
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@eps_bp.route('/reporte/ranking-especialistas', methods=['GET'])
def reporte_ranking_especialistas():
    try:
        datos = obtener_ranking_especialistas()
        return jsonify({"ok": True, "data": datos}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500