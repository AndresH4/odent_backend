### Archivo: modulo_usuarios/routes.py
"""
modulo_usuarios/routes.py — Stylo Dental
Blueprint de usuarios con creación TRANSACCIONAL y atómica.
"""
 
from flask import Blueprint, request, jsonify, render_template
import sqlite3
from db import get_db_connection
from modulo_usuarios import (
    usuario, rol, genero, tipo_documento, estado_usuario,
    administrador, aseguramiento_datos, accion_aseguramiento
)
from datetime import date
 
usuarios_bp = Blueprint('usuarios_bp', __name__)
 
 
# =============================================================================
# AUTENTICACIÓN — LOGIN
# =============================================================================
 
@usuarios_bp.route('/auth/login', methods=['POST'])
def login():
    datos = request.get_json(silent=True) or {}
 
    correo     = (datos.get('correo') or '').strip().lower()
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
        usuario_data.pop('Contrasena', None)

        # ── CORRECCIÓN: Si es especialista (Rol_ID == 2), adjuntar Especialista_ID
        # para que especialista.js pueda cargar sus citas sin una petición extra.
        if usuario_data.get('Rol_ID') == 2:
            cursor.execute(
                "SELECT Especialista_ID FROM especialista WHERE Usuario_ID = ?",
                (usuario_data['Usuario_ID'],)
            )
            esp_row = cursor.fetchone()
            if esp_row:
                usuario_data['Especialista_ID'] = esp_row['Especialista_ID']

                # Adjuntar también la especialidad del especialista para mostrarlo en UI
                cursor.execute("""
                    SELECT esp.Nombre_Especialidad
                    FROM especialista_especialidad ee
                    JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
                    WHERE ee.Especialista_ID = ?
                    LIMIT 1
                """, (esp_row['Especialista_ID'],))
                esp_nombre = cursor.fetchone()
                if esp_nombre:
                    usuario_data['Especialidad'] = esp_nombre['Nombre_Especialidad']
 
        return jsonify({"ok": True, "usuario": usuario_data}), 200
 
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# ROLES
# =============================================================================
 
@usuarios_bp.route('/roles', methods=['GET'])
def get_roles():
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute("SELECT Rol_ID, Descripcion AS Nombre_Rol FROM rol")
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
# USUARIOS — GET lista
# =============================================================================
 
@usuarios_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(usuario.read_all_usuarios())
 
 
# =============================================================================
# USUARIOS — POST creación TRANSACCIONAL ATÓMICA
# =============================================================================
 
@usuarios_bp.route('/usuarios', methods=['POST'])
def add_usuario():
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"ok": False, "error": "No se recibió JSON válido"}), 400
 
    nombres           = (datos.get('nombres') or '').strip()
    apellidos         = (datos.get('apellidos') or '').strip()
    documento         = (datos.get('documento') or '').strip()
    telefono          = (datos.get('telefono') or '').strip()
    correo            = (datos.get('correo') or '').strip().lower()
    contrasena        = datos.get('contrasena') or ''
    fecha_nacimiento  = datos.get('fecha_nacimiento') or '2000-01-01'
    genero_id         = int(datos.get('genero_id') or 1)
    tipo_documento_id = int(datos.get('tipo_documento_id') or 1)
    estado_id         = int(datos.get('estado_id') or 1)
    rol_id            = int(datos.get('rol_id') or 3)
 
    errores = []
    if not nombres:    errores.append("nombres es requerido")
    if not apellidos:  errores.append("apellidos es requerido")
    if not documento:  errores.append("documento es requerido")
    if not telefono:   errores.append("telefono es requerido")
    if not correo:     errores.append("correo es requerido")
    if not contrasena: errores.append("contrasena es requerida")
    if rol_id not in (1, 2, 3):
        errores.append("rol_id inválido (debe ser 1, 2 o 3)")
 
    eps_id             = datos.get('eps_id')
    tipo_afiliacion_id = datos.get('tipo_afiliacion_id')
 
    if rol_id == 3:
        if not eps_id:
            errores.append("eps_id es obligatorio para Paciente")
        if not tipo_afiliacion_id:
            errores.append("tipo_afiliacion_id es obligatorio para Paciente")
 
    tarjeta_profesional = (datos.get('tarjeta_profesional') or '').strip()
    especialidad_id     = datos.get('especialidad_id')
 
    if rol_id == 2 and not tarjeta_profesional:
        errores.append("tarjeta_profesional es obligatoria para Especialista")
 
    if errores:
        return jsonify({"ok": False, "error": "; ".join(errores)}), 400
 
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.isolation_level = None
        conexion.execute("PRAGMA foreign_keys = ON")
        cursor = conexion.cursor()
 
        cursor.execute("BEGIN")
 
        cursor.execute(
            """INSERT INTO usuarios
               (Nombres, Apellidos, TipoDoc_ID, NumeroDocumento, Contrasena,
                FechaNacimiento, Genero_ID, Correo, Telefono, Estado_ID, Rol_ID)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombres, apellidos, tipo_documento_id, documento, contrasena,
             fecha_nacimiento, genero_id, correo, telefono, estado_id, rol_id)
        )
        usuario_id = cursor.lastrowid
        if not usuario_id:
            raise ValueError("No se obtuvo Usuario_ID tras el INSERT en usuarios")
 
        if rol_id == 1:
            cursor.execute(
                "INSERT INTO administrador (Usuario_ID) VALUES (?)",
                (usuario_id,)
            )
 
        elif rol_id == 2:
            cursor.execute(
                "INSERT INTO especialista (Usuario_ID, Tarjeta_Profesional) VALUES (?, ?)",
                (usuario_id, tarjeta_profesional)
            )
            especialista_id = cursor.lastrowid
            if not especialista_id:
                raise ValueError("No se obtuvo Especialista_ID")
 
            if especialidad_id:
                cursor.execute(
                    """INSERT INTO especialista_especialidad (Especialista_ID, Especialidad_ID)
                       VALUES (?, ?)""",
                    (especialista_id, int(especialidad_id))
                )
 
        elif rol_id == 3:
            cursor.execute(
                "INSERT INTO paciente (Usuario_ID) VALUES (?)",
                (usuario_id,)
            )
            paciente_id = cursor.lastrowid
            if not paciente_id:
                raise ValueError("No se obtuvo Paciente_ID")
 
            cursor.execute(
                """INSERT INTO afiliacion (Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion)
                   VALUES (?, ?, ?, ?)""",
                (usuario_id, int(eps_id), int(tipo_afiliacion_id), date.today().isoformat())
            )
 
        cursor.execute("COMMIT")
 
        return jsonify({
            "ok": True,
            "status": "Usuario creado con éxito",
            "usuario_id": usuario_id
        }), 201
 
    except Exception as e:
        if conexion:
            try:
                conexion.execute("ROLLBACK")
            except Exception:
                pass
        return jsonify({"ok": False, "error": f"Transacción revertida: {str(e)}"}), 400
 
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# USUARIOS — GET / PUT / DELETE por ID
# =============================================================================
 
@usuarios_bp.route('/usuarios/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def crud_usuario(id):
    if request.method == 'GET':
        data = usuario.read_usuario_by_id(id)
        return jsonify(data) if data else (jsonify({"error": "No encontrado"}), 404)
    if request.method == 'PUT':
        data = request.json
        res  = usuario.update_usuario(id, **data)
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
    res  = administrador.create_administrador(data['usuario_id'])
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
    res  = aseguramiento_datos.create_aseguramiento(
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
    fin    = request.args.get('hasta')
    return jsonify(aseguramiento_datos.reporte_auditoria_por_fecha(inicio, fin))
 
 
# =============================================================================
# VISTA HTML
# =============================================================================
 
@usuarios_bp.route('/vista/crear_usuario')
def vista_creacion_usuario():
    return render_template('creacion.html')
 
 
# =============================================================================
# TIPO EPS
# =============================================================================
 
@usuarios_bp.route('/tipo-eps', methods=['GET'])
def get_tipo_eps():
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute("SELECT TipoEPS_ID AS ID_Tipo_EPS, Nombre_Tipo FROM tipo_eps")
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(fila) for fila in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# EPS
# =============================================================================
 
@usuarios_bp.route('/eps', methods=['GET', 'POST'])
def crud_eps():
    if request.method == 'GET':
        conexion = None
        try:
            conexion = get_db_connection()
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()
            cursor.execute(
                "SELECT EPS_ID AS ID_EPS, Nombre_EPS, Telefono_EPS, Regimen_ID AS ID_Tipo_EPS FROM eps"
            )
            filas = cursor.fetchall()
            return jsonify({"ok": True, "data": [dict(fila) for fila in filas]}), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            if conexion:
                conexion.close()
 
    datos = request.get_json(silent=True) or {}
    nombre_eps  = (datos.get('Nombre_EPS') or '').strip()
    tipo_eps_id = datos.get('ID_Tipo_EPS')
    telefono    = (datos.get('Telefono') or '').strip()
 
    if not nombre_eps:
        return jsonify({"ok": False, "error": "Nombre_EPS es requerido"}), 400
    if not tipo_eps_id:
        return jsonify({"ok": False, "error": "ID_Tipo_EPS es requerido"}), 400
 
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO eps (Nombre_EPS, Telefono_EPS, Regimen_ID) VALUES (?, ?, ?)",
            (nombre_eps, telefono or 'N/A', int(tipo_eps_id))
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid
        return jsonify({"ok": True, "data": {"ID_EPS": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# REGIMEN EPS
# =============================================================================
 
@usuarios_bp.route('/regimen-eps', methods=['GET'])
def get_regimen_eps():
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT Regimen_ID AS ID_Regimen_EPS, Descripcion AS Nombre_Regimen FROM regimen_eps"
        )
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(fila) for fila in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# PACIENTE
# =============================================================================
 
@usuarios_bp.route('/paciente', methods=['POST'])
def crear_paciente():
    datos = request.get_json(silent=True) or {}
    usuario_id = datos.get('ID_Usuario')
 
    if not usuario_id:
        return jsonify({"ok": False, "error": "ID_Usuario es requerido"}), 400
 
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
 
        cursor.execute("SELECT Paciente_ID FROM paciente WHERE Usuario_ID = ?", (usuario_id,))
        existente = cursor.fetchone()
        if existente:
            return jsonify({"ok": True, "data": {"ID_Paciente": existente["Paciente_ID"]}}), 200
 
        cursor.execute("INSERT INTO paciente (Usuario_ID) VALUES (?)", (usuario_id,))
        conexion.commit()
        nuevo_id = cursor.lastrowid
        return jsonify({"ok": True, "data": {"ID_Paciente": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()
 
 
@usuarios_bp.route('/paciente/<int:id>', methods=['PUT'])
def actualizar_paciente(id):
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute("SELECT Paciente_ID FROM paciente WHERE Paciente_ID = ?", (id,))
        fila = cursor.fetchone()
        if not fila:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404
        return jsonify({"ok": True, "data": {"ID_Paciente": id}}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# AFILIACION
# =============================================================================
 
@usuarios_bp.route('/afiliacion', methods=['POST'])
def crear_afiliacion():
    datos = request.get_json(silent=True) or {}
    usuario_id     = datos.get('ID_Usuario')
    eps_id         = datos.get('ID_EPS')
    regimen_eps_id = datos.get('ID_Regimen_EPS')
 
    if not usuario_id:
        return jsonify({"ok": False, "error": "ID_Usuario es requerido"}), 400
    if not eps_id:
        return jsonify({"ok": False, "error": "ID_EPS es requerido"}), 400
    if not regimen_eps_id:
        return jsonify({"ok": False, "error": "ID_Regimen_EPS es requerido"}), 400
 
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """INSERT INTO afiliacion (Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion)
               VALUES (?, ?, ?, ?)""",
            (usuario_id, eps_id, regimen_eps_id, date.today().isoformat())
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid
        return jsonify({"ok": True, "data": {"ID_Afiliacion": nuevo_id}}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()
 
 
@usuarios_bp.route('/afiliacion/<int:id>', methods=['PUT'])
def actualizar_afiliacion(id):
    datos = request.get_json(silent=True) or {}
    eps_id         = datos.get('ID_EPS')
    regimen_eps_id = datos.get('ID_Regimen_EPS')
    fecha          = datos.get('Fecha_Afiliacion') or date.today().isoformat()
 
    if not eps_id:
        return jsonify({"ok": False, "error": "ID_EPS es requerido"}), 400
    if not regimen_eps_id:
        return jsonify({"ok": False, "error": "ID_Regimen_EPS es requerido"}), 400
 
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """UPDATE afiliacion
               SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
               WHERE Afiliacion_ID = ?""",
            (eps_id, regimen_eps_id, fecha, id)
        )
        conexion.commit()
        if cursor.rowcount == 0:
            return jsonify({"ok": False, "error": "Afiliación no encontrada"}), 404
        return jsonify({"ok": True, "data": {"ID_Afiliacion": id}}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()