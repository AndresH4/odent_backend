from flask import Blueprint, request, jsonify, render_template
import sqlite3
from db import get_db_connection
from . import usuario, rol, genero, tipo_documento, estado_usuario, \
              administrador, aseguramiento_datos, accion_aseguramiento

usuarios_bp = Blueprint('usuarios_bp', __name__)


# =============================================================================
# AUTENTICACIÓN — LOGIN
# =============================================================================
# Consumido por login.js -> fetch('/api/auth/login', { correo, contrasena })
# Respuesta esperada por el frontend:
#   éxito -> { "ok": true,  "usuario": { ..., "Rol_ID": <int>, ... } }
#   error -> { "ok": false, "error": "<mensaje>" }
# =============================================================================

@usuarios_bp.route('/auth/login', methods=['POST'])
def login():
    datos = request.get_json(silent=True) or {}

    correo = (datos.get('correo') or '').strip().lower()
    contrasena = datos.get('contrasena') or ''

    if not correo or not contrasena:
        return jsonify({"ok": False, "error": "Correo y contraseña son requeridos"}), 400

    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE LOWER(Correo) = ? AND Contrasena = ?",
            (correo, contrasena)
        )
        fila = cursor.fetchone()

        if fila is None:
            return jsonify({"ok": False, "error": "Correo o contraseña incorrectos"}), 401

        usuario_data = dict(fila)
        usuario_data.pop('Contrasena', None)  # nunca se devuelve la contraseña al frontend

        return jsonify({"ok": True, "usuario": usuario_data}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# ROLES — devuelve Nombre_Rol para que creacion.js lo lea correctamente
# =============================================================================

@usuarios_bp.route('/roles', methods=['GET'])
def get_roles():
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute("SELECT ROL_ID, DESCRIPCION AS Nombre_Rol FROM rol")
        filas = cursor.fetchall()
        return jsonify([dict(fila) for fila in filas]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()

@usuarios_bp.route('/roles/reporte', methods=['GET'])
def get_reporte_roles():
    return jsonify(rol.reporte_usuarios_por_rol())


# =============================================================================
# USUARIOS — GET lista, POST creación completa desde creacion.html
# =============================================================================

@usuarios_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(usuario.read_all_usuarios())

@usuarios_bp.route('/usuarios', methods=['POST'])
def add_usuario():
    datos = request.get_json()
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """INSERT INTO usuarios
               (Nombres, Apellidos, NumeroDocumento, Telefono, Correo,
                Contrasena, Rol_ID, Genero_ID, TipoDoc_ID, Estado_ID, FechaNacimiento)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datos.get('nombres'),
                datos.get('apellidos'),
                datos.get('documento'),
                datos.get('telefono'),
                datos.get('correo'),
                datos.get('contrasena'),
                datos.get('rol_id'),
                datos.get('genero_id', 1),
                datos.get('tipo_documento_id', 1),
                datos.get('estado_id', 1),
                datos.get('fecha_nacimiento', '2000-01-01')
            )
        )
        conexion.commit()
        return jsonify({"ok": True, "status": "Usuario creado con éxito"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()

@usuarios_bp.route('/usuarios/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def crud_usuario(id):
    if request.method == 'GET':
        data = usuario.read_usuario_by_id(id)
        return jsonify(data) if data else (jsonify({"error": "No encontrado"}), 404)
    if request.method == 'PUT':
        data = request.json
        res = usuario.update_usuario(id, **data)
        return jsonify(res), (200 if res.get('ok') else 400)
    if request.method == 'DELETE':
        res = usuario.delete_usuario(id)
        return jsonify(res), (200 if res.get('ok') else 400)


# =============================================================================
# CATÁLOGOS
# =============================================================================

@usuarios_bp.route('/generos', methods=['GET'])
def get_generos():
    return jsonify(genero.read_all_generos())

@usuarios_bp.route('/generos/reporte', methods=['GET'])
def get_reporte_generos():
    return jsonify(genero.reporte_usuarios_por_genero())

@usuarios_bp.route('/tipos_documento', methods=['GET'])
def get_tipos_doc():
    return jsonify(tipo_documento.read_all_tipos_documento())

@usuarios_bp.route('/estados_usuario', methods=['GET'])
def get_estados():
    return jsonify(estado_usuario.read_all_estados())

@usuarios_bp.route('/acciones_aseguramiento', methods=['GET'])
def get_acciones():
    return jsonify(accion_aseguramiento.read_all_acciones())


# =============================================================================
# ADMINISTRADORES
# =============================================================================

@usuarios_bp.route('/administradores', methods=['GET', 'POST'])
def crud_administradores():
    if request.method == 'GET':
        return jsonify(administrador.read_all_administradores())
    data = request.json
    res = administrador.create_administrador(data['usuario_id'])
    return jsonify(res), (201 if res.get('ok') else 400)

@usuarios_bp.route('/administradores/activos', methods=['GET'])
def get_admins_activos():
    return jsonify(administrador.reporte_administradores_activos())


# =============================================================================
# ASEGURAMIENTO / AUDITORÍA
# =============================================================================

@usuarios_bp.route('/auditoria', methods=['GET', 'POST'])
def crud_auditoria():
    if request.method == 'GET':
        return jsonify(aseguramiento_datos.read_all_aseguramientos())
    data = request.json
    res = aseguramiento_datos.create_aseguramiento(
        data['usuario_id'], data['accion_id'], data['descripcion']
    )
    return jsonify(res), (201 if res.get('ok') else 400)

@usuarios_bp.route('/auditoria/usuario/<int:usuario_id>', methods=['GET'])
def get_auditoria_usuario(usuario_id):
    return jsonify(aseguramiento_datos.read_aseguramiento_by_usuario(usuario_id))

@usuarios_bp.route('/auditoria/reporte/acciones', methods=['GET'])
def get_reporte_acciones():
    return jsonify(aseguramiento_datos.reporte_acciones_por_tipo())

@usuarios_bp.route('/auditoria/reporte/fecha', methods=['GET'])
def get_reporte_fecha():
    inicio = request.args.get('desde')
    fin = request.args.get('hasta')
    return jsonify(aseguramiento_datos.reporte_auditoria_por_fecha(inicio, fin))


# =============================================================================
# VISTA HTML
# =============================================================================

@usuarios_bp.route('/vista/crear_usuario')
def vista_creacion_usuario():
    return render_template('creacion.html')