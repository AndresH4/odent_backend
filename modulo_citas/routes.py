"""
modulo_citas/routes.py — Stylo Dental
======================================
Endpoints REST para:
  • /api/citas            — listar y crear citas
  • /api/citas/<id>       — detalle, actualizar estado y cancelar
  • /api/agenda           — slots disponibles (GET) y creación de slots (POST)
  • /api/especialistas    — lista de especialistas con su especialidad
  • /api/multas           — listar y actualizar multas
  • /api/paciente/<id>/citas — citas de un paciente específico
  • /api/paciente/<id>/multa-activa — verificar multa pendiente
  • /api/paciente/por-usuario/<uid> — resolver Paciente_ID desde Usuario_ID
  • /api/especialista/<id>/citas — citas asignadas a un especialista
  • /api/usuarios         — lista de usuarios (para búsqueda en agendar)
  • /api/historial-clinico — registrar evolución clínica desde especialista
  • /api/respuesta        — registrar respuesta de ranking (Cita_ID explícito)
  • /api/verificar-password — verificar contraseña del paciente
  • /api/actualizar-perfil-paciente — actualizar datos del paciente
  • /api/citas/<id>/cancelar-sin-multa — cancelar sin penalización
  • /api/citas/<id>/cancelar-con-multa — cancelar con multa obligatoria

Registro en app.py:
    from modulo_citas.routes import citas_bp
    app.register_blueprint(citas_bp, url_prefix='/api')
"""

from flask import Blueprint, request, jsonify
from db import get_db_connection
from datetime import date, datetime, timedelta
import re

citas_bp = Blueprint('citas_bp', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES INTERNAS
# ─────────────────────────────────────────────────────────────────────────────

def _rows_to_list(cursor):
    return [dict(row) for row in cursor.fetchall()]


def _json_ok(data, code=200):
    return jsonify(data), code


def _json_error(mensaje, code=400):
    return jsonify({"ok": False, "error": mensaje}), code


def _validar_fecha_no_anterior(fecha_str):
    """Valida que la fecha ISO (YYYY-MM-DD) no sea anterior a hoy."""
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        return fecha >= date.today()
    except (ValueError, TypeError):
        return False


def _validar_hora_minimo_tres_horas(hora_str, fecha_str):
    """
    Si la fecha es hoy, valida que la hora sea al menos 3 horas posterior
    a la hora actual. Si es una fecha futura, siempre es válida.
    """
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        if fecha != date.today():
            return True  # Fecha futura: todas las horas son válidas

        hora = datetime.strptime(hora_str[:5], '%H:%M').time()
        ahora = datetime.now()
        limite = ahora + timedelta(hours=3)
        slot_dt = datetime.combine(date.today(), hora)
        return slot_dt >= limite
    except (ValueError, TypeError):
        return False


def _validar_politica_password(password):
    """
    Valida que la contraseña cumpla la política de seguridad:
      • Mínimo 8 caracteres
      • Al menos una letra mayúscula
      • Al menos una letra minúscula
      • Al menos un número
      • Al menos un carácter especial
    """
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


def _tiene_cita_activa_por_usuario(cur, usuario_id):
    """
    Consulta REAL a la base de datos: verifica si el Usuario_ID (paciente
    logueado) ya tiene una cita registrada cuyo estado de agenda sea
    'Disponible' (EstadoAgenda_ID = 1, slot reservado sintéticamente) u
    'Ocupado' (EstadoAgenda_ID = 2), es decir, una cita Activa/Pendiente,
    Y cuya fecha programada (a.Fecha) sea hoy o una fecha futura.
    No existe en el esquema un estado "Cumplida", por lo que una cita ya
    atendida permanece con EstadoAgenda_ID = 2 (Ocupado) de forma
    indefinida; sin el filtro de fecha, esa cita pasada bloquearía para
    siempre el agendamiento de nuevas citas (falso positivo). Por eso se
    exige adicionalmente que a.Fecha >= hoy para considerarla Activa.
    Se resuelve el Paciente_ID a partir del Usuario_ID mediante JOIN con
    la tabla paciente, sin confiar en ningún dato enviado por el frontend.
    """
    cur.execute("""
        SELECT c.Cita_ID
        FROM cita c
        JOIN paciente p ON p.Paciente_ID = c.Paciente_ID
        JOIN agenda a   ON a.Agenda_ID   = c.Agenda_ID
        WHERE p.Usuario_ID = ?
          AND a.EstadoAgenda_ID IN (1, 2)
          AND a.Fecha >= ?
        LIMIT 1
    """, (usuario_id, date.today().isoformat()))
    return cur.fetchone() is not None


def _calcular_minutos_restantes(fecha_str, hora_str):
    """
    Calcula los minutos que faltan entre ahora y la fecha/hora de la cita.
    Retorna float (puede ser negativo si la cita ya pasó).
    """
    try:
        cita_dt = datetime.strptime(f"{fecha_str} {hora_str[:5]}", '%Y-%m-%d %H:%M')
        delta   = cita_dt - datetime.now()
        return delta.total_seconds() / 60.0
    except (ValueError, TypeError):
        return float('inf')


# ─────────────────────────────────────────────────────────────────────────────
# USUARIOS  —  GET /api/usuarios
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.Estado_ID,
                u.Rol_ID,
                u.FechaNacimiento
            FROM usuarios u
            ORDER BY u.Apellidos
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# PACIENTE POR USUARIO  —  GET /api/paciente/por-usuario/<usuario_id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/por-usuario/<int:usuario_id>', methods=['GET'])
def get_paciente_por_usuario(usuario_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                p.Paciente_ID,
                p.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.FechaNacimiento
            FROM paciente p
            JOIN usuarios u ON u.Usuario_ID = p.Usuario_ID
            WHERE p.Usuario_ID = ?
        """, (usuario_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Paciente no encontrado para ese usuario.', 404)
        return _json_ok(dict(row))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# ESPECIALISTAS  —  GET /api/especialistas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialistas', methods=['GET'])
def get_especialistas():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                e.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos   AS NombreCompleto,
                GROUP_CONCAT(esp.Nombre_Especialidad, ', ') AS Especialidades,
                e.Tarjeta_Profesional
            FROM especialista e
            JOIN usuarios u        ON u.Usuario_ID      = e.Usuario_ID
            JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            JOIN especialidad esp  ON esp.Especialidad_ID = ee.Especialidad_ID
            WHERE u.Estado_ID = 1
            GROUP BY e.Especialista_ID
            ORDER BY u.Apellidos
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CREAR USUARIO  —  POST /api/usuarios
# Crea el usuario y, si Rol_ID = 2 (Especialista), crea también su registro
# en `especialista` incluyendo Tarjeta_Profesional (4-10 caracteres).
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/usuarios', methods=['POST'])
def crear_usuario():
    datos = request.get_json(silent=True) or {}

    nombres          = (datos.get('Nombres') or '').strip()
    apellidos        = (datos.get('Apellidos') or '').strip()
    numero_documento = (datos.get('NumeroDocumento') or '').strip()
    correo           = (datos.get('Correo') or '').strip()
    telefono         = (datos.get('Telefono') or '').strip()
    contrasena       = datos.get('Contrasena')
    rol_id           = datos.get('Rol_ID')
    estado_id        = datos.get('Estado_ID', 1)
    fecha_nacimiento = datos.get('FechaNacimiento')

    tarjeta_profesional = (datos.get('Tarjeta_Profesional') or '').strip()

    if not all([nombres, apellidos, numero_documento, correo, contrasena, rol_id]):
        return _json_error('Nombres, Apellidos, NumeroDocumento, Correo, Contrasena y Rol_ID son obligatorios.')

    rol_id = int(rol_id)

    if rol_id == 2:
        if len(tarjeta_profesional) < 4 or len(tarjeta_profesional) > 10:
            return _json_error('Tarjeta_Profesional debe tener entre 4 y 10 caracteres.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO usuarios
                (Nombres, Apellidos, NumeroDocumento, Correo, Telefono,
                 Contrasena, Rol_ID, Estado_ID, FechaNacimiento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombres, apellidos, numero_documento, correo, telefono,
              contrasena, rol_id, estado_id, fecha_nacimiento))

        usuario_id = cur.lastrowid

        if rol_id == 2:
            cur.execute("""
                INSERT INTO especialista (Usuario_ID, Tarjeta_Profesional)
                VALUES (?, ?)
            """, (usuario_id, tarjeta_profesional))

        con.commit()
        return _json_ok({"ok": True, "Usuario_ID": usuario_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# AGENDA  —  GET /api/agenda?especialista_id=&fecha=
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/agenda', methods=['GET'])
def get_agenda():
    esp_id = request.args.get('especialista_id')
    fecha  = request.args.get('fecha')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        sql = """
            SELECT
                a.Agenda_ID,
                a.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos  AS NombreEspecialista,
                esp.Nombre_Especialidad,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Final                     AS Hora_Fin,
                ea.Nombre_Estado                 AS EstadoAgenda
            FROM agenda a
            JOIN especialista e    ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios u        ON u.Usuario_ID      = e.Usuario_ID
            JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            JOIN especialidad esp  ON esp.Especialidad_ID = ee.Especialidad_ID
            JOIN estado_agenda ea  ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            WHERE a.EstadoAgenda_ID = 1
        """
        params = []

        if esp_id:
            sql += " AND a.Especialista_ID = ?"
            params.append(esp_id)
        if fecha:
            sql += " AND a.Fecha = ?"
            params.append(fecha)

        sql += " ORDER BY a.Fecha, a.Hora_Inicio"
        cur.execute(sql, params)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CREAR SLOT DE AGENDA  —  POST /api/agenda
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/agenda', methods=['POST'])
def crear_agenda():
    datos       = request.get_json(silent=True) or {}
    esp_id      = datos.get('Especialista_ID')
    fecha       = datos.get('Fecha')
    hora_inicio = datos.get('Hora_Inicio')
    hora_fin    = datos.get('Hora_Fin')
    estado_id   = datos.get('Estado_ID', 1)

    if not all([esp_id, fecha, hora_inicio, hora_fin]):
        return _json_error('Especialista_ID, Fecha, Hora_Inicio y Hora_Fin son obligatorios.')

    # ── Validación de fecha no anterior a hoy ─────────────────────────────────
    if not _validar_fecha_no_anterior(fecha):
        return _json_error('No se puede crear un slot con fecha anterior a la actual.')

    # ── Validación de hora mínima 3 horas si es hoy ──────────────────────────
    if not _validar_hora_minimo_tres_horas(hora_inicio, fecha):
        return _json_error(
            'Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.'
        )

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?",
            (esp_id,)
        )
        if not cur.fetchone():
            return _json_error('Especialista no encontrado.', 404)

        cur.execute("""
            SELECT Agenda_ID FROM agenda
            WHERE Especialista_ID = ?
              AND Fecha       = ?
              AND Hora_Inicio = ?
              AND EstadoAgenda_ID = 1
        """, (esp_id, fecha, hora_inicio))
        existente = cur.fetchone()
        if existente:
            return _json_ok({"ok": True, "Agenda_ID": existente['Agenda_ID']}, 200)

        cur.execute("""
            INSERT INTO agenda (Especialista_ID, Fecha, Hora_Inicio, Hora_Final, EstadoAgenda_ID)
            VALUES (?, ?, ?, ?, ?)
        """, (esp_id, fecha, hora_inicio, hora_fin, estado_id))

        agenda_id = cur.lastrowid
        con.commit()
        return _json_ok({"ok": True, "Agenda_ID": agenda_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS  —  GET /api/citas   |   POST /api/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas', methods=['GET'])
def get_citas():
    paciente_id     = request.args.get('paciente_id')
    especialista_id = request.args.get('especialista_id')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        sql = """
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                p.Paciente_ID,
                up.Nombres || ' ' || up.Apellidos  AS NombrePaciente,
                up.NumeroDocumento,
                up.Telefono                        AS TelefonoPaciente,
                up.Correo                          AS CorreoPaciente,
                a.Agenda_ID,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Final                       AS Hora_Fin,
                ea.Nombre_Estado                   AS EstadoAgenda,
                e.Especialista_ID,
                ue.Nombres || ' ' || ue.Apellidos  AS NombreEspecialista,
                esp.Nombre_Especialidad
            FROM cita c
            JOIN paciente p   ON p.Paciente_ID     = c.Paciente_ID
            JOIN usuarios up  ON up.Usuario_ID     = p.Usuario_ID
            JOIN agenda a     ON a.Agenda_ID       = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue  ON ue.Usuario_ID     = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            WHERE 1=1
        """
        params = []
        if paciente_id:
            sql += " AND p.Paciente_ID = ?"
            params.append(paciente_id)
        if especialista_id:
            sql += " AND e.Especialista_ID = ?"
            params.append(especialista_id)

        sql += " ORDER BY a.Fecha DESC, a.Hora_Inicio DESC"
        cur.execute(sql, params)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/citas', methods=['POST'])
def crear_cita():
    datos       = request.get_json(silent=True) or {}
    paciente_id = datos.get('Paciente_ID')
    agenda_id   = datos.get('Agenda_ID')
    motivo      = (datos.get('Motivo_Consulta') or '').strip()

    if not all([paciente_id, agenda_id, motivo]):
        return _json_error('Paciente_ID, Agenda_ID y Motivo_Consulta son obligatorios.')

    con = None
    try:
        con = get_db_connection()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()

        # ── BEGIN TRANSACTION explícita: todas las escrituras relacionadas con
        # esta cita (cita + actualización de agenda) se confirman o revierten
        # como una sola unidad atómica, garantizando integridad referencial. ───
        cur.execute("BEGIN TRANSACTION")

        # ── Verificar que el paciente existe en BD (evita datos falsos) ───────
        cur.execute(
            "SELECT p.Paciente_ID, p.Usuario_ID, u.Rol_ID FROM paciente p JOIN usuarios u ON u.Usuario_ID = p.Usuario_ID WHERE p.Paciente_ID = ?",
            (paciente_id,)
        )
        paciente_row = cur.fetchone()
        if not paciente_row:
            cur.execute("ROLLBACK")
            return _json_error('El paciente no existe en el sistema.', 404)
        if paciente_row['Rol_ID'] != 3:
            cur.execute("ROLLBACK")
            return _json_error('El usuario no tiene rol de paciente.', 403)

        usuario_id_paciente = paciente_row['Usuario_ID']

        # ── Verificar slot de agenda (bloqueado dentro de la misma transacción
        # para evitar condiciones de carrera entre la lectura del estado y el
        # INSERT/UPDATE posteriores) ───────────────────────────────────────────
        cur.execute(
            "SELECT EstadoAgenda_ID, Fecha, Hora_Inicio, Especialista_ID FROM agenda WHERE Agenda_ID = ?",
            (agenda_id,)
        )
        slot = cur.fetchone()
        if not slot:
            cur.execute("ROLLBACK")
            return _json_error('El slot de agenda no existe.', 404)
        if slot['EstadoAgenda_ID'] != 1:
            cur.execute("ROLLBACK")
            return _json_error('Ese horario ya no está disponible.')

        # ── Validar que el especialista referenciado por el slot exista
        # realmente en la tabla especialista (integridad referencial) ─────────
        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?",
            (slot['Especialista_ID'],)
        )
        if not cur.fetchone():
            cur.execute("ROLLBACK")
            return _json_error('El especialista asociado al horario no existe.', 404)

        # ── Validar fecha no anterior a hoy (verificación backend) ────────────
        fecha_agenda = slot['Fecha']
        if not _validar_fecha_no_anterior(fecha_agenda):
            cur.execute("ROLLBACK")
            return _json_error('No se puede agendar una cita con fecha anterior a la actual.')

        # ── Validar hora mínima 3 horas si es hoy (verificación backend) ──────
        hora_inicio = slot['Hora_Inicio']
        if not _validar_hora_minimo_tres_horas(hora_inicio, fecha_agenda):
            cur.execute("ROLLBACK")
            return _json_error(
                'Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.'
            )

        # ── VALIDACIÓN DE CITA ÚNICA — CONSULTA REAL A LA BASE DE DATOS ───────
        if _tiene_cita_activa_por_usuario(cur, usuario_id_paciente):
            cur.execute("ROLLBACK")
            return _json_error('No puedes agendar. Ya tienes una cita activa en el sistema.', 409)

        # ── INSERT en tabla `cita` — vincula Paciente_ID y Agenda_ID ──────────
        cur.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (paciente_id, agenda_id, motivo)
        )
        cita_id = cur.lastrowid
        if not cita_id:
            cur.execute("ROLLBACK")
            return _json_error('No se pudo registrar la cita en el sistema.', 500)

        # ── UPDATE en tabla `agenda` — marca el slot como Ocupado ─────────────
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 2 WHERE Agenda_ID = ?", (agenda_id,)
        )
        if cur.rowcount == 0:
            cur.execute("ROLLBACK")
            return _json_error('No se pudo actualizar el estado de la agenda.', 500)

        cur.execute("COMMIT")

        return _json_ok({"ok": True, "Cita_ID": cita_id, "status": "Cita registrada con éxito."}, 201)

    except Exception as exc:
        if con:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITA INDIVIDUAL  —  GET /api/citas/<id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>', methods=['GET'])
def get_cita(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID, c.Motivo_Consulta,
                p.Paciente_ID,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                up.NumeroDocumento, up.Correo,
                a.Fecha, a.Hora_Inicio,
                a.Hora_Final                      AS Hora_Fin,
                ea.Nombre_Estado                  AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista
            FROM cita c
            JOIN paciente p    ON p.Paciente_ID  = c.Paciente_ID
            JOIN usuarios up   ON up.Usuario_ID  = p.Usuario_ID
            JOIN agenda a      ON a.Agenda_ID    = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue   ON ue.Usuario_ID  = e.Usuario_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        return _json_ok(dict(row))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR CITA (endpoint legado)  —  PUT /api/citas/<id>/cancelar
# Mantiene comportamiento original para compatibilidad con otros módulos.
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar', methods=['PUT'])
def cancelar_cita(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT Agenda_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)

        agenda_id = row['Agenda_ID']

        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (agenda_id,)
        )
        cur.execute(
            "INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,)
        )

        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada."})

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR SIN MULTA  —  PUT /api/citas/<id>/cancelar-sin-multa
# Se usa cuando faltan MÁS de 2 horas para la cita.
# Marca la agenda como Cancelado (EstadoAgenda_ID = 3). No genera multa.
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-sin-multa', methods=['PUT'])
def cancelar_cita_sin_multa(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT c.Agenda_ID, a.Fecha, a.Hora_Inicio
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)

        # ── Verificación backend: confirmar que efectivamente faltan > 2 horas ─
        minutos_restantes = _calcular_minutos_restantes(row['Fecha'], row['Hora_Inicio'])
        if minutos_restantes <= 120:
            return _json_error(
                'No se puede cancelar sin multa: faltan 2 horas o menos para la cita.', 409
            )

        agenda_id = row['Agenda_ID']
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (agenda_id,)
        )

        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada sin penalización."})

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR CON MULTA  —  PUT /api/citas/<id>/cancelar-con-multa
# Se usa cuando faltan 2 horas o MENOS para la cita.
# Marca la agenda como Cancelado (EstadoAgenda_ID = 3) y genera multa.
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-con-multa', methods=['PUT'])
def cancelar_cita_con_multa(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT c.Agenda_ID, a.Fecha, a.Hora_Inicio
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)

        agenda_id = row['Agenda_ID']

        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (agenda_id,)
        )
        cur.execute(
            "INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,)
        )

        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada por poco tiempo de anticipación."})

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR PACIENTE  —  GET /api/paciente/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/citas', methods=['GET'])
def get_citas_paciente(paciente_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Final                      AS Hora_Fin,
                ea.Nombre_Estado                  AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista,
                esp.Nombre_Especialidad,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                up.NumeroDocumento,
                COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta
            FROM cita c
            JOIN agenda a      ON a.Agenda_ID    = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue   ON ue.Usuario_ID  = e.Usuario_ID
            JOIN paciente p    ON p.Paciente_ID  = c.Paciente_ID
            JOIN usuarios up   ON up.Usuario_ID  = p.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m  ON m.Cita_ID  = c.Cita_ID
            LEFT JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            WHERE c.Paciente_ID = ?
            ORDER BY a.Fecha DESC, a.Hora_Inicio DESC
        """, (paciente_id,))
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR ESPECIALISTA  —  GET /api/especialista/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialista/<int:especialista_id>/citas', methods=['GET'])
def get_citas_especialista(especialista_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Final                      AS Hora_Fin,
                ea.Nombre_Estado                  AS EstadoAgenda,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                up.NumeroDocumento,
                up.Telefono                       AS TelefonoPaciente,
                esp.Nombre_Especialidad,
                COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta
            FROM cita c
            JOIN agenda a    ON a.Agenda_ID    = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN paciente p  ON p.Paciente_ID  = c.Paciente_ID
            JOIN usuarios up ON up.Usuario_ID  = p.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = a.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m  ON m.Cita_ID = c.Cita_ID
            LEFT JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            WHERE a.Especialista_ID = ?
            ORDER BY a.Fecha, a.Hora_Inicio
        """, (especialista_id,))
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# MULTAS  —  GET /api/multas   |   PUT /api/multas/<id>/pagar
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/multas', methods=['GET'])
def get_multas():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                m.Multa_ID,
                m.Cita_ID,
                em.Nombre_Estado                  AS EstadoMulta,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                a.Fecha,
                a.Hora_Inicio
            FROM multa m
            JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            JOIN cita c    ON c.Cita_ID    = m.Cita_ID
            JOIN paciente p ON p.Paciente_ID = c.Paciente_ID
            JOIN usuarios up ON up.Usuario_ID = p.Usuario_ID
            JOIN agenda a  ON a.Agenda_ID  = c.Agenda_ID
            ORDER BY m.Multa_ID DESC
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/multas/<int:multa_id>/pagar', methods=['PUT'])
def pagar_multa(multa_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE multa SET EstadoMulta_ID = 2 WHERE Multa_ID = ?", (multa_id,)
        )
        if cur.rowcount == 0:
            return _json_error('Multa no encontrada.', 404)
        con.commit()
        return _json_ok({"ok": True, "status": "Multa marcada como Pagada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR MULTA ACTIVA  —  GET /api/paciente/<id>/multa-activa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/multa-activa', methods=['GET'])
def multa_activa(paciente_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID
            FROM multa m
            JOIN cita c ON c.Cita_ID = m.Cita_ID
            WHERE c.Paciente_ID = ? AND m.EstadoMulta_ID = 1
            LIMIT 1
        """, (paciente_id,))
        row = cur.fetchone()
        return _json_ok({"tiene_multa": row is not None})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# HISTORIAL CLÍNICO  —  POST /api/historial-clinico
# Body JSON: { Cita_ID, Evolucion, Diagnostico, Tratamiento }
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/historial-clinico', methods=['POST'])
def crear_historial_clinico():
    datos       = request.get_json(silent=True) or {}
    cita_id     = datos.get('Cita_ID')
    evolucion   = (datos.get('Evolucion')   or '').strip()
    diagnostico = (datos.get('Diagnostico') or '').strip()
    tratamiento = (datos.get('Tratamiento') or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        if not cur.fetchone():
            return _json_error('Cita no encontrada.', 404)

        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
        )
        existing = cur.fetchone()

        if existing:
            historial_id = existing['Historial_ID']
        else:
            cur.execute(
                "INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,)
            )
            historial_id = cur.lastrowid

        if diagnostico:
            cur.execute(
                "SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?",
                (diagnostico,)
            )
            diag_row = cur.fetchone()
            if not diag_row:
                cur.execute(
                    "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)", (diagnostico,)
                )
                diagnostico_id = cur.lastrowid
            else:
                diagnostico_id = diag_row['Diagnostico_ID']

            cur.execute("""
                INSERT OR IGNORE INTO historial_diagnostico (Historial_ID, Diagnostico_ID)
                VALUES (?, ?)
            """, (historial_id, diagnostico_id))

        if tratamiento or evolucion:
            descripcion = f"{evolucion}\n---\n{tratamiento}".strip() if (evolucion and tratamiento) else (evolucion or tratamiento)
            cur.execute(
                "INSERT INTO tratamiento (Historial_ID, Descripcion) VALUES (?, ?)",
                (historial_id, descripcion)
            )

        con.commit()
        return _json_ok({"ok": True, "Historial_ID": historial_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# RANKING — RESPUESTA  —  POST /api/respuesta
# Body JSON: { ID_Pregunta, ID_Paciente, Texto_Respuesta, Cita_ID }
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/respuesta', methods=['POST'])
def crear_respuesta_ranking():
    datos           = request.get_json(silent=True) or {}
    pregunta_id     = datos.get('ID_Pregunta')
    paciente_id     = datos.get('ID_Paciente')
    texto_respuesta = datos.get('Texto_Respuesta')
    cita_id         = datos.get('Cita_ID')

    if not all([pregunta_id, paciente_id, texto_respuesta]):
        return _json_error('ID_Pregunta, ID_Paciente y Texto_Respuesta son obligatorios.')

    try:
        valor_int = int(texto_respuesta)
        if valor_int < 1 or valor_int > 5:
            return _json_error('Texto_Respuesta debe ser un número entre 1 y 5.')
    except (ValueError, TypeError):
        return _json_error(f'Texto_Respuesta debe ser un número entero, recibido: {texto_respuesta!r}')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        if cita_id:
            cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
            if not cur.fetchone():
                return _json_error(f'Cita_ID {cita_id} no encontrada.', 404)
            cita_id_final = cita_id
        else:
            cur.execute("""
                SELECT c.Cita_ID
                FROM cita c
                WHERE c.Paciente_ID = ?
                ORDER BY c.Cita_ID DESC
                LIMIT 1
            """, (paciente_id,))
            fila = cur.fetchone()
            if not fila:
                return _json_error(f'No se encontró ninguna cita para el paciente ID {paciente_id}.', 404)
            cita_id_final = fila['Cita_ID']

        cur.execute(
            "SELECT Paciente_ID FROM cita WHERE Cita_ID = ?", (cita_id_final,)
        )
        cita_row = cur.fetchone()
        if not cita_row or str(cita_row['Paciente_ID']) != str(paciente_id):
            return _json_error('La cita no pertenece a este paciente.', 403)

        cur.execute("""
            SELECT Respuesta_ID FROM respuesta_ranking
            WHERE Cita_ID = ? AND Preguntas_ID = ?
        """, (cita_id_final, pregunta_id))
        if cur.fetchone():
            return _json_error('Ya existe una respuesta para esta pregunta en esta cita.')

        cur.execute("""
            INSERT INTO respuesta_ranking (Cita_ID, Preguntas_ID, Respuesta)
            VALUES (?, ?, ?)
        """, (cita_id_final, pregunta_id, valor_int))

        respuesta_id = cur.lastrowid

        cur.execute("""
            SELECT a.Especialista_ID
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id_final,))
        esp_row = cur.fetchone()
        if esp_row:
            cur.execute("""
                INSERT INTO puntuacion_especialista (Especialista_ID, Respuesta_ID)
                VALUES (?, ?)
            """, (esp_row['Especialista_ID'], respuesta_id))

        con.commit()
        return _json_ok({"ok": True, "Respuesta_ID": respuesta_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR CONTRASEÑA  —  POST /api/verificar-password
# Body JSON: { usuario_id, password }
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/verificar-password', methods=['POST'])
def verificar_password():
    datos      = request.get_json(silent=True) or {}
    usuario_id = datos.get('usuario_id')
    password   = datos.get('password')

    if not usuario_id or not password:
        return _json_error('usuario_id y password son obligatorios.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT Usuario_ID FROM usuarios WHERE Usuario_ID = ? AND Contrasena = ?",
            (usuario_id, password)
        )
        row = cur.fetchone()
        if row:
            return _json_ok({"ok": True})
        return _json_ok({"ok": False, "error": "Contraseña incorrecta."})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZAR PERFIL PACIENTE  —  POST /api/actualizar-perfil-paciente
# Body JSON: { usuario_id, nombres, apellidos, documento, tipo_documento_id,
#              correo, telefono, nacimiento, nuevaPass,
#              eps_id, tipo_eps_id, regimen_id }
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/actualizar-perfil-paciente', methods=['POST'])
def actualizar_perfil_paciente():
    datos             = request.get_json(silent=True) or {}
    usuario_id        = datos.get('usuario_id')
    correo            = datos.get('correo')
    telefono          = datos.get('telefono')
    nacimiento        = datos.get('nacimiento')
    nueva_pass        = datos.get('nuevaPass')
    nombres           = datos.get('nombres')
    apellidos         = datos.get('apellidos')
    documento         = datos.get('documento')
    tipo_documento_id = datos.get('tipo_documento_id')
    eps_id            = datos.get('eps_id')
    tipo_eps_id       = datos.get('tipo_eps_id')
    regimen_id        = datos.get('regimen_id')

    if not usuario_id:
        return _json_error('usuario_id es obligatorio.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        campos  = []
        valores = []

        if nombres:
            campos.append("Nombres = ?")
            valores.append(nombres)
        if apellidos:
            campos.append("Apellidos = ?")
            valores.append(apellidos)
        if documento:
            campos.append("NumeroDocumento = ?")
            valores.append(documento)
        if tipo_documento_id:
            campos.append("TipoDoc_ID = ?")
            valores.append(tipo_documento_id)
        if correo:
            campos.append("Correo = ?")
            valores.append(correo)
        if telefono:
            campos.append("Telefono = ?")
            valores.append(telefono)
        if nacimiento:
            campos.append("FechaNacimiento = ?")
            valores.append(nacimiento)
        if nueva_pass:
            ok, msg = _validar_politica_password(nueva_pass)
            if not ok:
                return _json_error(msg, 400)
            campos.append("Contrasena = ?")
            valores.append(nueva_pass)

        if not campos and not any([eps_id, tipo_eps_id]):
            return _json_error('No hay campos para actualizar.')

        if campos:
            valores.append(usuario_id)
            cur.execute(
                f"UPDATE usuarios SET {', '.join(campos)} WHERE Usuario_ID = ?",
                tuple(valores)
            )
            if cur.rowcount == 0:
                return _json_error('Usuario no encontrado.', 404)

        # ── Actualizar afiliación (EPS, TipoEPS) si se enviaron ───────────────
        if eps_id or tipo_eps_id:
            cur.execute(
                "SELECT Afiliacion_ID, EPS_ID, TipoEPS_ID FROM afiliacion WHERE Usuario_ID = ?",
                (usuario_id,)
            )
            afil_row = cur.fetchone()

            eps_final      = int(eps_id)      if eps_id      else (afil_row['EPS_ID']     if afil_row else None)
            tipo_eps_final = int(tipo_eps_id) if tipo_eps_id else (afil_row['TipoEPS_ID'] if afil_row else None)

            if afil_row:
                cur.execute("""
                    UPDATE afiliacion
                    SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
                    WHERE Afiliacion_ID = ?
                """, (eps_final, tipo_eps_final, date.today().isoformat(), afil_row['Afiliacion_ID']))
            else:
                if eps_final and tipo_eps_final:
                    cur.execute("""
                        INSERT INTO afiliacion (Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion)
                        VALUES (?, ?, ?, ?)
                    """, (usuario_id, eps_final, tipo_eps_final, date.today().isoformat()))

        con.commit()
        return _json_ok({"ok": True, "mensaje": "Perfil actualizado correctamente."})

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()