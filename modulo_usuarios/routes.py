"""
modulo_usuarios/routes.py — Stylo Dental
"""

from flask import Blueprint, request, jsonify, render_template, session
import sqlite3
import os
import re
from modulo_usuarios import (
    usuario, rol, genero, tipo_documento, estado_usuario,
    administrador, aseguramiento_datos, accion_aseguramiento
)
from datetime import date

usuarios_bp = Blueprint('usuarios_bp', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'odent.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── POLÍTICA DE CONTRASEÑA ───────────────────────────────────────────────────

def _validar_politica_password(password):
    if len(password) < 8:
        return False, 'La contraseña debe tener al menos 8 caracteres.'
    if not re.search(r'[A-Z]', password):
        return False, 'La contraseña debe contener al menos una letra mayúscula.'
    if not re.search(r'[a-z]', password):
        return False, 'La contraseña debe contener al menos una letra minúscula.'
    if not re.search(r'[0-9]', password):
        return False, 'La contraseña debe contener al menos un número.'
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, 'La contraseña debe contener al menos un carácter especial.'
    return True, ''


def _verificar_password_contra_hash(hash_bd, password_ingresada):
    from werkzeug.security import check_password_hash
    if hash_bd.startswith('scrypt:') or hash_bd.startswith('pbkdf2:'):
        return check_password_hash(hash_bd, password_ingresada)
    return hash_bd == password_ingresada


# =============================================================================
# AUTENTICACIÓN — LOGIN
# BLOQUEO ABSOLUTO: verifica Estado_ID antes de crear sesión.
# Si el usuario está Inactivo (Estado_ID != 1), se rechaza el acceso
# incluso con credenciales correctas y no se escribe ningún dato de sesión.
# =============================================================================

@usuarios_bp.route('/auth/login', methods=['POST'])
def login():
    datos      = request.get_json(silent=True) or {}
    correo     = (datos.get('correo') or '').strip().lower()
    contrasena = datos.get('contrasena') or ''

    if not correo or not contrasena:
        return jsonify({"ok": False, "error": "Correo y contraseña son requeridos"}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        fila = cursor.fetchone()

        if fila is None:
            return jsonify({"ok": False, "error": "Correo o contraseña incorrectos"}), 401

        if not _verificar_password_contra_hash(fila['Contrasena'], contrasena):
            return jsonify({"ok": False, "error": "Correo o contraseña incorrectos"}), 401

        # BLOQUEO ABSOLUTO: cuenta inactiva — no se crea sesión bajo ninguna circunstancia
        if fila['Estado_ID'] != 1:
            return jsonify({
                "ok": False,
                "error": "Cuenta inactiva. Acceso denegado. Contacta al administrador.",
                "inactivo": True
            }), 403

        usuario_data = dict(fila)
        usuario_data.pop('Contrasena', None)

        # Registrar usuario_id en sesión del servidor para el interceptor before_request
        session['usuario_id'] = usuario_data['Usuario_ID']

        if usuario_data.get('Rol_ID') == 2:
            cursor.execute(
                "SELECT Especialista_ID FROM especialista WHERE Usuario_ID = ?",
                (usuario_data['Usuario_ID'],)
            )
            esp_row = cursor.fetchone()
            if esp_row:
                usuario_data['Especialista_ID'] = esp_row['Especialista_ID']
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
        conexion = _get_conn()
        cursor   = conexion.cursor()
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
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute("""
            SELECT
                u.Usuario_ID,
                esp.Especialista_ID,
                pac.Paciente_ID,
                u.Nombres,
                u.Apellidos,
                u.TipoDoc_ID,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.Estado_ID,
                u.Rol_ID,
                u.FechaNacimiento
            FROM usuarios u
            LEFT JOIN especialista esp ON esp.Usuario_ID = u.Usuario_ID
            LEFT JOIN paciente pac ON pac.Usuario_ID = u.Usuario_ID
            ORDER BY u.Usuario_ID ASC
        """)
        filas = cursor.fetchall()
        return jsonify([dict(f) for f in filas]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# USUARIOS — GET / PUT / DELETE por ID
# PERSISTENCIA DEL CAMBIO DE ESTADO: el PUT actualiza Estado_ID de forma
# inmediata y segura en la BD, lo que activa el interceptor before_request
# en la siguiente petición del usuario afectado, forzando su expulsión.
# =============================================================================

@usuarios_bp.route('/usuarios/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def crud_usuario(id):

    if request.method == 'GET':
        conexion = None
        try:
            conexion = _get_conn()
            cursor   = conexion.cursor()
            cursor.execute("""
                SELECT
                    u.Usuario_ID,
                    u.Nombres,
                    u.Apellidos,
                    u.TipoDoc_ID,
                    td.Nombre_Tipo_Documento,
                    u.NumeroDocumento,
                    u.Correo,
                    u.Telefono,
                    u.Estado_ID,
                    u.Rol_ID,
                    u.FechaNacimiento
                FROM usuarios u
                LEFT JOIN tipo_documento td ON td.TipoDoc_ID = u.TipoDoc_ID
                WHERE u.Usuario_ID = ?
            """, (id,))
            fila = cursor.fetchone()
            if not fila:
                return jsonify({"error": "No encontrado"}), 404
            return jsonify(dict(fila)), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if conexion:
                conexion.close()

    if request.method == 'PUT':
        from werkzeug.security import generate_password_hash

        datos    = request.get_json(silent=True) or {}
        conexion = None
        try:
            conexion = _get_conn()
            cursor   = conexion.cursor()

            contrasena_actual = datos.get('ContrasenaActual')

            if contrasena_actual and contrasena_actual != '_skip_':
                cursor.execute(
                    "SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (id,)
                )
                fila_pwd = cursor.fetchone()
                if not fila_pwd:
                    return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
                if not _verificar_password_contra_hash(
                    fila_pwd['Contrasena'], contrasena_actual
                ):
                    return jsonify({
                        "ok": False,
                        "error": "La contraseña actual es incorrecta."
                    }), 401

            campos  = []
            valores = []

            nombres    = (datos.get('Nombres')   or '').strip()
            apellidos  = (datos.get('Apellidos') or '').strip()
            correo     = (datos.get('Correo')    or '').strip()
            telefono   = (datos.get('Telefono')  or '').strip()
            estado_id  = datos.get('Estado_ID')
            nueva_pass = datos.get('nuevaPass') or datos.get('NuevaPass')

            if nombres:   campos.append("Nombres = ?");   valores.append(nombres)
            if apellidos: campos.append("Apellidos = ?"); valores.append(apellidos)
            if correo:    campos.append("Correo = ?");    valores.append(correo)
            if telefono:  campos.append("Telefono = ?");  valores.append(telefono)

            # PERSISTENCIA DEL CAMBIO DE ESTADO: se persiste de forma inmediata
            # en la BD sin condiciones adicionales, garantizando que el interceptor
            # before_request detecte el cambio en la siguiente request del usuario.
            if estado_id is not None:
                campos.append("Estado_ID = ?")
                valores.append(int(estado_id))

            if nueva_pass:
                valida, msg_pwd = _validar_politica_password(nueva_pass)
                if not valida:
                    return jsonify({"ok": False, "error": msg_pwd}), 400
                campos.append("Contrasena = ?")
                valores.append(generate_password_hash(nueva_pass, method='scrypt'))

            if not campos:
                return jsonify({"ok": False, "error": "No hay campos para actualizar."}), 400

            valores.append(id)
            cursor.execute(
                f"UPDATE usuarios SET {', '.join(campos)} WHERE Usuario_ID = ?",
                tuple(valores)
            )
            if cursor.rowcount == 0:
                return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

            conexion.commit()
            return jsonify({"ok": True, "mensaje": "Perfil actualizado correctamente."}), 200

        except Exception as e:
            if conexion:
                try: conexion.rollback()
                except Exception: pass
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            if conexion: conexion.close()

    if request.method == 'DELETE':
        res = usuario.delete_usuario(id)
        return jsonify(res), (200 if res.get('ok') else 400)


# =============================================================================
# VERIFICAR CONTRASEÑA — POST /api/usuarios/verificar-password
# =============================================================================

@usuarios_bp.route('/usuarios/verificar-password', methods=['POST'])
def verificar_password_usuario():
    datos             = request.get_json(silent=True) or {}
    usuario_id        = datos.get('usuario_id')
    contrasena_actual = datos.get('contrasena_actual')

    if not usuario_id:
        return jsonify({"ok": False, "error": "usuario_id es obligatorio."}), 400
    if not contrasena_actual:
        return jsonify({"ok": False, "error": "contrasena_actual es obligatoria."}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

        if _verificar_password_contra_hash(row['Contrasena'], contrasena_actual):
            return jsonify({"ok": True}), 200
        return jsonify({"ok": False, "error": "Contraseña incorrecta."}), 401

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# CAMBIAR CONTRASEÑA — POST /api/usuarios/cambiar-password
# =============================================================================

@usuarios_bp.route('/usuarios/cambiar-password', methods=['POST'])
def cambiar_password():
    from werkzeug.security import generate_password_hash

    datos                = request.get_json(silent=True) or {}
    usuario_id           = datos.get('usuario_id')
    contrasena_actual    = datos.get('contrasena_actual')
    contrasena_nueva     = datos.get('contrasena_nueva')
    contrasena_confirmar = datos.get('contrasena_confirmar')

    if not usuario_id:
        return jsonify({"ok": False, "error": "usuario_id es obligatorio."}), 400
    if not contrasena_actual:
        return jsonify({"ok": False, "error": "contrasena_actual es obligatoria."}), 400
    if not contrasena_nueva:
        return jsonify({"ok": False, "error": "contrasena_nueva es obligatoria."}), 400
    if not contrasena_confirmar:
        return jsonify({"ok": False, "error": "contrasena_confirmar es obligatoria."}), 400
    if contrasena_nueva != contrasena_confirmar:
        return jsonify({"ok": False, "error": "Las contraseñas nuevas no coinciden."}), 400

    valida, msg = _validar_politica_password(contrasena_nueva)
    if not valida:
        return jsonify({"ok": False, "error": msg}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()

        cursor.execute(
            "SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

        if not _verificar_password_contra_hash(row['Contrasena'], contrasena_actual):
            return jsonify({"ok": False, "error": "La contraseña actual es incorrecta."}), 401

        nuevo_hash = generate_password_hash(contrasena_nueva, method='scrypt')
        cursor.execute(
            "UPDATE usuarios SET Contrasena = ? WHERE Usuario_ID = ?",
            (nuevo_hash, usuario_id)
        )
        if cursor.rowcount == 0:
            return jsonify({"ok": False, "error": "No se pudo actualizar la contraseña."}), 500

        conexion.commit()
        return jsonify({"ok": True, "mensaje": "Contraseña actualizada correctamente."}), 200

    except Exception as e:
        if conexion:
            try: conexion.rollback()
            except Exception: pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# USUARIOS — POST creación TRANSACCIONAL ATÓMICA
# =============================================================================

@usuarios_bp.route('/usuarios', methods=['POST'])
def add_usuario():
    from werkzeug.security import generate_password_hash

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
    if not nombres:   errores.append("nombres es requerido")
    if not apellidos: errores.append("apellidos es requerido")
    if not documento: errores.append("documento es requerido")
    if not telefono:  errores.append("telefono es requerido")
    if not correo:    errores.append("correo es requerido")
    if not contrasena:
        errores.append("contrasena es requerida")
    else:
        valida, msg_pwd = _validar_politica_password(contrasena)
        if not valida:
            errores.append(msg_pwd)
    if rol_id not in (1, 2, 3):
        errores.append("rol_id inválido (debe ser 1, 2 o 3)")

    eps_id = datos.get('eps_id')
    tipo_afiliacion_id = (
        datos.get('tipo_eps_id') or
        datos.get('tipo_afiliacion_eps_id') or
        datos.get('tipo_afiliacion_id')
    )

    if rol_id == 3:
        if not eps_id:
            errores.append("eps_id es obligatorio para Paciente")
        if not tipo_afiliacion_id:
            errores.append("tipo_afiliacion_id es obligatorio para Paciente")

    tarjeta_profesional = (datos.get('tarjeta_profesional') or '').strip()
    especialidad_id     = datos.get('especialidad_id')

    if rol_id == 2 and not tarjeta_profesional:
        errores.append("tarjeta_profesional es obligatoria para Especialista")
    if rol_id == 2 and tarjeta_profesional and (
        len(tarjeta_profesional) < 4 or len(tarjeta_profesional) > 10
    ):
        errores.append("tarjeta_profesional debe tener entre 4 y 10 caracteres")

    if errores:
        return jsonify({"ok": False, "error": "; ".join(errores)}), 400

    conexion = None
    try:
        conexion = sqlite3.connect(DB_PATH)
        conexion.row_factory = sqlite3.Row
        conexion.isolation_level = None
        conexion.execute("PRAGMA foreign_keys = ON")
        cursor = conexion.cursor()

        cursor.execute("BEGIN")

        cursor.execute("SELECT 1 FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        if cursor.fetchone():
            cursor.execute("ROLLBACK")
            return jsonify({"ok": False, "error": "El correo electrónico ya está registrado."}), 409

        cursor.execute("SELECT 1 FROM usuarios WHERE NumeroDocumento = ?", (documento,))
        if cursor.fetchone():
            cursor.execute("ROLLBACK")
            return jsonify({"ok": False, "error": "El número de documento ya está registrado."}), 409

        if rol_id == 2:
            cursor.execute(
                "SELECT 1 FROM especialista WHERE Tarjeta_Profesional = ?", (tarjeta_profesional,)
            )
            if cursor.fetchone():
                cursor.execute("ROLLBACK")
                return jsonify({"ok": False, "error": "La tarjeta profesional ya está registrada."}), 409
            if especialidad_id:
                cursor.execute(
                    "SELECT 1 FROM especialidad WHERE Especialidad_ID = ?", (int(especialidad_id),)
                )
                if not cursor.fetchone():
                    cursor.execute("ROLLBACK")
                    return jsonify({"ok": False, "error": "La especialidad seleccionada no existe."}), 400

        if rol_id == 3:
            cursor.execute("SELECT 1 FROM eps WHERE EPS_ID = ?", (int(eps_id),))
            if not cursor.fetchone():
                cursor.execute("ROLLBACK")
                return jsonify({"ok": False, "error": "La EPS seleccionada no existe."}), 400
            cursor.execute(
                "SELECT 1 FROM tipo_afiliacion_eps WHERE TipoEPS_ID = ?", (int(tipo_afiliacion_id),)
            )
            if not cursor.fetchone():
                cursor.execute("ROLLBACK")
                return jsonify({"ok": False, "error": "El tipo de EPS seleccionado no existe."}), 400

        cursor.execute(
            """INSERT INTO usuarios
               (Nombres, Apellidos, TipoDoc_ID, NumeroDocumento, Contrasena,
                FechaNacimiento, Genero_ID, Correo, Telefono, Estado_ID, Rol_ID)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombres, apellidos, tipo_documento_id, documento,
             generate_password_hash(contrasena, method='scrypt'),
             fecha_nacimiento, genero_id, correo, telefono, estado_id, rol_id)
        )
        usuario_id = cursor.lastrowid
        if not usuario_id:
            raise ValueError("No se obtuvo Usuario_ID tras el INSERT en usuarios")

        if rol_id == 1:
            cursor.execute(
                "INSERT INTO administrador (Usuario_ID) VALUES (?)", (usuario_id,)
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
                "INSERT INTO paciente (Usuario_ID) VALUES (?)", (usuario_id,)
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
            try: conexion.execute("ROLLBACK")
            except Exception: pass
        return jsonify({"ok": False, "error": f"Transacción revertida: {str(e)}"}), 400
    finally:
        if conexion:
            conexion.close()


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

@usuarios_bp.route('/tipo-afiliacion-eps', methods=['GET'])
def get_tipo_afiliacion_eps():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT TipoEPS_ID AS ID_Tipo_EPS, Nombre_Tipo FROM tipo_afiliacion_eps ORDER BY TipoEPS_ID"
        )
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(fila) for fila in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


@usuarios_bp.route('/tipo-eps', methods=['GET'])
def get_tipo_eps():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT TipoEPS_ID, Nombre_Tipo FROM tipo_afiliacion_eps ORDER BY TipoEPS_ID"
        )
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
            conexion = _get_conn()
            cursor   = conexion.cursor()
            cursor.execute(
                "SELECT EPS_ID AS ID_EPS, Nombre_EPS, Telefono_EPS, Regimen_ID FROM eps ORDER BY EPS_ID"
            )
            filas = cursor.fetchall()
            return jsonify({"ok": True, "data": [dict(fila) for fila in filas]}), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            if conexion:
                conexion.close()

    datos       = request.get_json(silent=True) or {}
    nombre_eps  = (datos.get('Nombre_EPS') or '').strip()
    tipo_eps_id = datos.get('ID_Tipo_EPS')
    telefono    = (datos.get('Telefono') or '').strip()

    if not nombre_eps:
        return jsonify({"ok": False, "error": "Nombre_EPS es requerido"}), 400
    if not tipo_eps_id:
        return jsonify({"ok": False, "error": "ID_Tipo_EPS es requerido"}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
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
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            """SELECT Regimen_ID AS ID_Regimen_EPS, Descripcion AS Nombre_Regimen
               FROM regimen_eps ORDER BY Regimen_ID"""
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
    datos           = request.get_json(silent=True) or {}
    usuario_id      = datos.get('ID_Usuario')
    grupo_sanguineo = (datos.get('Grupo_Sanguineo') or '').strip() or None
    alergias        = (datos.get('Alergias') or '').strip() or None
    antecedentes    = (datos.get('Antecedentes') or '').strip() or None
    observaciones   = (datos.get('Observaciones') or '').strip() or None

    if not usuario_id:
        return jsonify({"ok": False, "error": "ID_Usuario es requerido"}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()

        cursor.execute("SELECT Paciente_ID FROM paciente WHERE Usuario_ID = ?", (usuario_id,))
        existente = cursor.fetchone()
        if existente:
            try:
                cursor.execute(
                    """UPDATE paciente
                       SET Grupo_Sanguineo = ?, Alergias = ?, Antecedentes = ?, Observaciones = ?
                       WHERE Paciente_ID = ?""",
                    (grupo_sanguineo, alergias, antecedentes, observaciones, existente["Paciente_ID"])
                )
            except Exception:
                pass
            conexion.commit()
            return jsonify({"ok": True, "data": {"ID_Paciente": existente["Paciente_ID"]}}), 200

        try:
            cursor.execute(
                """INSERT INTO paciente (Usuario_ID, Grupo_Sanguineo, Alergias, Antecedentes, Observaciones)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario_id, grupo_sanguineo, alergias, antecedentes, observaciones)
            )
        except Exception:
            cursor.execute(
                "INSERT INTO paciente (Usuario_ID) VALUES (?)", (usuario_id,)
            )
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
        conexion = _get_conn()
        cursor   = conexion.cursor()
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
    datos          = request.get_json(silent=True) or {}
    usuario_id     = datos.get('ID_Usuario')
    eps_id         = datos.get('ID_EPS')
    regimen_eps_id = datos.get('ID_Tipo_EPS') or datos.get('ID_Regimen_EPS')

    if not usuario_id:
        return jsonify({"ok": False, "error": "ID_Usuario es requerido"}), 400
    if not eps_id:
        return jsonify({"ok": False, "error": "ID_EPS es requerido"}), 400
    if not regimen_eps_id:
        return jsonify({"ok": False, "error": "ID_Regimen_EPS es requerido"}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()

        cursor.execute(
            "SELECT Afiliacion_ID FROM afiliacion WHERE Usuario_ID = ?", (usuario_id,)
        )
        existente = cursor.fetchone()
        if existente:
            cursor.execute(
                """UPDATE afiliacion
                   SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
                   WHERE Afiliacion_ID = ?""",
                (eps_id, regimen_eps_id, date.today().isoformat(), existente["Afiliacion_ID"])
            )
            conexion.commit()
            return jsonify({"ok": True, "data": {"ID_Afiliacion": existente["Afiliacion_ID"]}}), 200

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


@usuarios_bp.route('/afiliacion', methods=['GET'])
def get_afiliacion():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Afiliacion_ID, Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion FROM afiliacion"
        )
        filas = cursor.fetchall()
        return jsonify([dict(fila) for fila in filas]), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


@usuarios_bp.route('/afiliacion/por-usuario/<int:usuario_id>', methods=['GET'])
def get_afiliacion_por_usuario(usuario_id):
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                a.Afiliacion_ID,
                a.EPS_ID,
                a.TipoEPS_ID,
                a.Fecha_Afiliacion,
                e.Regimen_ID
            FROM afiliacion a
            LEFT JOIN eps e ON e.EPS_ID = a.EPS_ID
            WHERE a.Usuario_ID = ?
            ORDER BY a.Afiliacion_ID DESC
            LIMIT 1
            """,
            (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Sin afiliación registrada."}), 404
        return jsonify({"ok": True, "data": dict(row)}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if conexion:
            conexion.close()


@usuarios_bp.route('/afiliacion/<int:id>', methods=['PUT'])
def actualizar_afiliacion(id):
    datos          = request.get_json(silent=True) or {}
    eps_id         = datos.get('ID_EPS')
    regimen_eps_id = datos.get('ID_Tipo_EPS') or datos.get('ID_Regimen_EPS')
    fecha          = datos.get('Fecha_Afiliacion') or date.today().isoformat()

    if not eps_id:
        return jsonify({"ok": False, "error": "ID_EPS es requerido"}), 400
    if not regimen_eps_id:
        return jsonify({"ok": False, "error": "ID_Regimen_EPS es requerido"}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
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


# =============================================================================
# ACTUALIZAR PERFIL PACIENTE — POST /api/actualizar-perfil-paciente
# =============================================================================

@usuarios_bp.route('/actualizar-perfil-paciente', methods=['POST'])
def actualizar_perfil_paciente():
    from werkzeug.security import generate_password_hash

    datos             = request.get_json(silent=True) or {}
    usuario_id        = datos.get('usuario_id')
    correo            = datos.get('correo')
    telefono          = datos.get('telefono')
    nacimiento        = datos.get('nacimiento')
    nueva_pass        = datos.get('nuevaPass')
    contrasena_actual = datos.get('contrasena_actual') or datos.get('ContrasenaActual')
    nombres           = datos.get('nombres')
    apellidos         = datos.get('apellidos')
    documento         = datos.get('documento')
    tipo_documento_id = datos.get('tipo_documento_id')
    eps_id            = datos.get('eps_id')
    tipo_eps_id       = datos.get('tipo_eps_id')

    if not usuario_id:
        return jsonify({"ok": False, "error": "usuario_id es obligatorio."}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        campos   = []
        valores  = []

        if nombres:           campos.append("Nombres = ?");         valores.append(nombres)
        if apellidos:         campos.append("Apellidos = ?");       valores.append(apellidos)
        if documento:         campos.append("NumeroDocumento = ?"); valores.append(documento)
        if tipo_documento_id: campos.append("TipoDoc_ID = ?");      valores.append(tipo_documento_id)
        if correo:            campos.append("Correo = ?");          valores.append(correo)
        if telefono:          campos.append("Telefono = ?");        valores.append(telefono)
        if nacimiento:        campos.append("FechaNacimiento = ?"); valores.append(nacimiento)

        if nueva_pass:
            if not contrasena_actual:
                return jsonify({
                    "ok": False,
                    "error": "Debes ingresar tu contraseña actual para cambiarla."
                }), 400

            cursor.execute("SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (usuario_id,))
            fila_pwd = cursor.fetchone()
            if not fila_pwd:
                return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

            if not _verificar_password_contra_hash(fila_pwd['Contrasena'], contrasena_actual):
                return jsonify({"ok": False, "error": "La contraseña actual es incorrecta."}), 401

            ok, msg = _validar_politica_password(nueva_pass)
            if not ok:
                return jsonify({"ok": False, "error": msg}), 400
            campos.append("Contrasena = ?")
            valores.append(generate_password_hash(nueva_pass, method='scrypt'))

        if not campos and not any([eps_id, tipo_eps_id]):
            return jsonify({"ok": False, "error": "No hay campos para actualizar."}), 400

        if campos:
            valores.append(usuario_id)
            cursor.execute(
                f"UPDATE usuarios SET {', '.join(campos)} WHERE Usuario_ID = ?",
                tuple(valores)
            )
            if cursor.rowcount == 0:
                return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

        if eps_id or tipo_eps_id:
            cursor.execute(
                "SELECT Afiliacion_ID, EPS_ID, TipoEPS_ID FROM afiliacion WHERE Usuario_ID = ?",
                (usuario_id,)
            )
            afil_row = cursor.fetchone()
            eps_final      = int(eps_id)      if eps_id      else (afil_row['EPS_ID']     if afil_row else None)
            tipo_eps_final = int(tipo_eps_id) if tipo_eps_id else (afil_row['TipoEPS_ID'] if afil_row else None)

            if afil_row:
                cursor.execute(
                    """UPDATE afiliacion
                       SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
                       WHERE Afiliacion_ID = ?""",
                    (eps_final, tipo_eps_final, date.today().isoformat(), afil_row['Afiliacion_ID'])
                )
            elif eps_final and tipo_eps_final:
                cursor.execute(
                    """INSERT INTO afiliacion (Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion)
                       VALUES (?, ?, ?, ?)""",
                    (usuario_id, eps_final, tipo_eps_final, date.today().isoformat())
                )

        conexion.commit()
        return jsonify({"ok": True, "mensaje": "Perfil actualizado correctamente."}), 200

    except Exception as e:
        if conexion:
            try: conexion.rollback()
            except Exception: pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# MULTAS — GET todas (Administrador) con JOINs completos
# =============================================================================

@usuarios_bp.route('/multas', methods=['GET'])
def get_multas():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute("""
            SELECT
                m.Multa_ID,
                m.Cita_ID,
                u.Nombres || ' ' || u.Apellidos        AS NombrePaciente,
                u.NumeroDocumento,
                td.Nombre_Tipo_Documento,
                c.Motivo_Consulta                      AS Concepto,
                a.Fecha,
                a.Hora_Inicio,
                COALESCE(esp.Nombre_Especialidad, '—') AS Especialidad,
                em.Nombre_Estado                       AS EstadoMulta,
                m.EstadoMulta_ID,
                re.Descripcion                         AS RegimenEPS,
                e.Nombre_EPS                           AS NombreEPS,
                tae.Nombre_Tipo                        AS TipoAfiliacion
            FROM multa m
            JOIN cita c                   ON c.Cita_ID            = m.Cita_ID
            JOIN agenda a                 ON a.Agenda_ID           = c.Agenda_ID
            JOIN paciente p               ON p.Paciente_ID         = c.Paciente_ID
            JOIN usuarios u               ON u.Usuario_ID          = p.Usuario_ID
            LEFT JOIN tipo_documento td   ON td.TipoDoc_ID         = u.TipoDoc_ID
            LEFT JOIN afiliacion af       ON af.Usuario_ID         = u.Usuario_ID
            LEFT JOIN eps e               ON e.EPS_ID              = af.EPS_ID
            LEFT JOIN regimen_eps re      ON re.Regimen_ID         = e.Regimen_ID
            LEFT JOIN tipo_afiliacion_eps tae ON tae.TipoEPS_ID   = af.TipoEPS_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = a.Especialista_ID
            LEFT JOIN especialidad esp    ON esp.Especialidad_ID   = ee.Especialidad_ID
            JOIN estado_multa em          ON em.EstadoMulta_ID     = m.EstadoMulta_ID
            GROUP BY m.Multa_ID
            ORDER BY m.Multa_ID DESC
        """)
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# MULTAS — GET por paciente
# =============================================================================

@usuarios_bp.route('/multas/paciente/<int:paciente_id>', methods=['GET'])
def get_multas_paciente(paciente_id):
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute("""
            SELECT
                m.Multa_ID,
                m.Cita_ID,
                c.Motivo_Consulta  AS Concepto,
                a.Fecha,
                a.Hora_Inicio,
                esp.Nombres || ' ' || esp.Apellidos AS NombreEspecialista,
                esp2.Nombre_Especialidad,
                em.Nombre_Estado   AS EstadoMulta,
                m.EstadoMulta_ID
            FROM multa m
            JOIN cita c              ON c.Cita_ID          = m.Cita_ID
            JOIN agenda a            ON a.Agenda_ID         = c.Agenda_ID
            JOIN especialista e      ON e.Especialista_ID   = a.Especialista_ID
            JOIN usuarios esp        ON esp.Usuario_ID      = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee  ON ee.Especialista_ID  = e.Especialista_ID
            LEFT JOIN especialidad esp2             ON esp2.Especialidad_ID = ee.Especialidad_ID
            JOIN estado_multa em     ON em.EstadoMulta_ID  = m.EstadoMulta_ID
            WHERE c.Paciente_ID = ?
            ORDER BY m.Multa_ID DESC
        """, (paciente_id,))
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# MULTAS — PUT cambiar estado (genérico, usado por el admin)
# =============================================================================

@usuarios_bp.route('/multas/<int:multa_id>/estado', methods=['PUT'])
def cambiar_estado_multa(multa_id):
    datos           = request.get_json(silent=True) or {}
    nuevo_estado_id = datos.get('EstadoMulta_ID')

    if nuevo_estado_id is None:
        return jsonify({"ok": False, "error": "EstadoMulta_ID es obligatorio."}), 400

    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Multa_ID FROM multa WHERE Multa_ID = ?", (multa_id,)
        )
        if not cursor.fetchone():
            return jsonify({"ok": False, "error": "Multa no encontrada."}), 404

        cursor.execute(
            "UPDATE multa SET EstadoMulta_ID = ? WHERE Multa_ID = ?",
            (int(nuevo_estado_id), multa_id)
        )
        conexion.commit()

        cursor.execute(
            "SELECT Nombre_Estado FROM estado_multa WHERE EstadoMulta_ID = ?",
            (int(nuevo_estado_id),)
        )
        row = cursor.fetchone()
        nombre_estado = row['Nombre_Estado'] if row else '—'

        return jsonify({
            "ok": True,
            "mensaje": f"Multa #{multa_id} actualizada a '{nombre_estado}'.",
            "EstadoMulta_ID": int(nuevo_estado_id),
            "EstadoMulta": nombre_estado
        }), 200
    except Exception as e:
        if conexion:
            try: conexion.rollback()
            except Exception: pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# MULTAS — PUT marcar como pagada (compatibilidad)
# =============================================================================

@usuarios_bp.route('/multas/<int:multa_id>/pagar', methods=['PUT'])
def pagar_multa(multa_id):
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Multa_ID, EstadoMulta_ID FROM multa WHERE Multa_ID = ?", (multa_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Multa no encontrada."}), 404
        if row['EstadoMulta_ID'] == 2:
            return jsonify({"ok": False, "error": "La multa ya está marcada como Pagada."}), 409

        cursor.execute(
            "UPDATE multa SET EstadoMulta_ID = 2 WHERE Multa_ID = ?", (multa_id,)
        )
        conexion.commit()
        return jsonify({"ok": True, "mensaje": f"Multa #{multa_id} marcada como Pagada."}), 200
    except Exception as e:
        if conexion:
            try: conexion.rollback()
            except Exception: pass
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# ESPECIALISTAS — GET vista admin con ID real de BD
# =============================================================================

@usuarios_bp.route('/especialistas-admin', methods=['GET'])
def get_especialistas_admin():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute("""
            SELECT
                ROW_NUMBER() OVER (ORDER BY e.Especialista_ID) AS ID_Secuencial,
                e.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos                AS NombreCompleto,
                COALESCE(GROUP_CONCAT(esp.Nombre_Especialidad, ', '), '—') AS Especialidad,
                COALESCE(eu.Nombre_Estado, '—')                AS EstadoUsuario,
                u.Estado_ID
            FROM especialista e
            JOIN usuarios u               ON u.Usuario_ID       = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp    ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN estado_usuario eu   ON eu.Estado_ID        = u.Estado_ID
            GROUP BY e.Especialista_ID
            ORDER BY e.Especialista_ID
        """)
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# PACIENTES — GET vista admin con ID real de BD
# =============================================================================

@usuarios_bp.route('/pacientes-admin', methods=['GET'])
def get_pacientes_admin():
    conexion = None
    try:
        conexion = _get_conn()
        cursor   = conexion.cursor()
        cursor.execute("""
            SELECT
                ROW_NUMBER() OVER (ORDER BY p.Paciente_ID) AS ID_Secuencial,
                p.Paciente_ID,
                u.Nombres || ' ' || u.Apellidos            AS NombreCompleto,
                COALESCE(re.Descripcion, '—')              AS RegimenEPS,
                COALESCE(tae.Nombre_Tipo, '—')             AS TipoAfiliacion,
                COALESCE(e.Nombre_EPS, '—')                AS NombreEPS,
                COALESCE(eu.Nombre_Estado, '—')            AS EstadoUsuario,
                u.Estado_ID
            FROM paciente p
            JOIN usuarios u                   ON u.Usuario_ID    = p.Usuario_ID
            LEFT JOIN afiliacion af           ON af.Usuario_ID   = u.Usuario_ID
            LEFT JOIN eps e                   ON e.EPS_ID        = af.EPS_ID
            LEFT JOIN regimen_eps re          ON re.Regimen_ID   = e.Regimen_ID
            LEFT JOIN tipo_afiliacion_eps tae ON tae.TipoEPS_ID  = af.TipoEPS_ID
            LEFT JOIN estado_usuario eu       ON eu.Estado_ID    = u.Estado_ID
            GROUP BY p.Paciente_ID
            ORDER BY p.Paciente_ID
        """)
        filas = cursor.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()