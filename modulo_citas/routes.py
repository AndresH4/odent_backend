"""
modulo_citas/routes.py — Stylo Dental
"""

from flask import Blueprint, request, jsonify
from datetime import date, datetime, timedelta
import re
import threading
import logging
import os
import sqlite3

logger = logging.getLogger("stylo_dental_smtp")

citas_bp = Blueprint('citas_bp', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'odent.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        return fecha >= date.today()
    except (ValueError, TypeError):
        return False


def _validar_hora_minimo_tres_horas(hora_str, fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        if fecha != date.today():
            return True
        hora    = datetime.strptime(hora_str[:5], '%H:%M').time()
        ahora   = datetime.now()
        limite  = ahora + timedelta(hours=3)
        slot_dt = datetime.combine(date.today(), hora)
        return slot_dt >= limite
    except (ValueError, TypeError):
        return False


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


def _tiene_cita_activa_por_usuario(cur, usuario_id):
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
    try:
        cita_dt = datetime.strptime(f"{fecha_str} {hora_str[:5]}", '%Y-%m-%d %H:%M')
        delta   = cita_dt - datetime.now()
        return delta.total_seconds() / 60.0
    except (ValueError, TypeError):
        return float('inf')


# ─────────────────────────────────────────────────────────────────────────────
# HISTORIAL CLÍNICO — FUNCIÓN INTERNA
# ─────────────────────────────────────────────────────────────────────────────

def _garantizar_historial_clinico(cur, cita_id, diagnosticos=None,
                                   evolucion=None, tratamiento=None):
    cur.execute(
        "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
    )
    existente = cur.fetchone()

    if existente:
        historial_id = existente['Historial_ID']
    else:
        cur.execute("INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,))
        historial_id = cur.lastrowid

    diagnosticos = diagnosticos or []
    for nombre_diag in diagnosticos:
        nombre_diag = (nombre_diag or '').strip()
        if not nombre_diag:
            continue
        cur.execute(
            "SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?",
            (nombre_diag,)
        )
        diag_row = cur.fetchone()
        if diag_row:
            diagnostico_id = diag_row['Diagnostico_ID']
        else:
            cur.execute(
                "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)", (nombre_diag,)
            )
            diagnostico_id = cur.lastrowid
        cur.execute(
            "INSERT OR IGNORE INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
            (historial_id, diagnostico_id)
        )

    evolucion   = (evolucion   or '').strip()
    tratamiento = (tratamiento or '').strip()
    if evolucion or tratamiento:
        descripcion = (
            f"{evolucion}\n---\n{tratamiento}".strip()
            if (evolucion and tratamiento)
            else (evolucion or tratamiento)
        )
        cur.execute(
            "INSERT INTO tratamiento (Historial_ID, Descripcion) VALUES (?, ?)",
            (historial_id, descripcion)
        )

    return historial_id


# ─────────────────────────────────────────────────────────────────────────────
# PROMEDIO DEL ESPECIALISTA
# ─────────────────────────────────────────────────────────────────────────────

def _crear_promedio(cur, especialista_id: int) -> float:
    cur.execute("""
        SELECT ROUND(AVG(CAST(rr.Respuesta AS REAL)), 2) AS Promedio,
               COUNT(rr.Respuesta_ID)                    AS Total
        FROM respuesta_ranking rr
        INNER JOIN cita   c  ON rr.Cita_ID  = c.Cita_ID
        INNER JOIN agenda ag ON c.Agenda_ID = ag.Agenda_ID
        WHERE ag.Especialista_ID = ?
    """, (especialista_id,))
    row = cur.fetchone()
    return float(row['Promedio']) if row and row['Promedio'] is not None else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# CORREO ENCUESTA
# ─────────────────────────────────────────────────────────────────────────────

def _html_encuesta_cita(nombre_paciente: str, nombre_especialista: str,
                         login_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Encuesta de Satisfacción — Stylo Dental</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f1f5f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" border="0"
               style="background:#ffffff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <tr>
            <td style="background:linear-gradient(135deg,#0369a1,#0ea5e9);
                       padding:32px;text-align:center;">
              <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:800;
                          letter-spacing:0.5px;">🦷 Stylo Dental</h1>
              <p style="color:#bae6fd;margin:8px 0 0;font-size:14px;">
                Evaluación de servicio odontológico
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 40px;">
              <p style="color:#1e293b;font-size:16px;margin:0 0 16px;font-weight:600;">
                Estimado(a) {nombre_paciente},
              </p>
              <p style="color:#475569;font-size:14px;line-height:1.7;margin:0 0 16px;">
                Su consulta con <strong>Dr(a). {nombre_especialista}</strong> ha finalizado.
                En Clínica Stylo Dental valoramos profundamente su opinión y nos gustaría
                que calificara la atención recibida.
              </p>
              <p style="color:#475569;font-size:14px;line-height:1.7;margin:0 0 28px;">
                Ingrese a nuestra plataforma y complete la encuesta de satisfacción disponible
                en su <strong>Panel de Paciente → Historial de Citas</strong>.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding:8px 0 28px;">
                    <a href="{login_url}"
                       style="display:inline-block;
                              background:linear-gradient(135deg,#0369a1,#0ea5e9);
                              color:#ffffff;text-decoration:none;
                              padding:16px 40px;border-radius:8px;
                              font-size:15px;font-weight:700;letter-spacing:0.3px;">
                      Calificar mi experiencia ★
                    </a>
                  </td>
                </tr>
              </table>
              <p style="color:#94a3b8;font-size:12px;margin:0;">
                Si el botón no funciona, copie y pegue este enlace en su navegador:<br>
                <a href="{login_url}" style="color:#0284c7;word-break:break-all;">{login_url}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#f8fafc;padding:20px 40px;text-align:center;
                       border-top:1px solid #e2e8f0;">
              <p style="color:#94a3b8;font-size:12px;margin:0;">
                © 2025 Clínica Stylo Dental · Todos los derechos reservados
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _despachar_correo_encuesta(cita_id: int, correo_paciente: str,
                                nombre_paciente: str, nombre_especialista: str,
                                horas_retraso: int, login_url: str):
    import time as _time

    if horas_retraso > 0:
        logger.info(
            "[ENCUESTA] Esperando %d hora(s) antes de enviar correo a %s (cita %d)",
            horas_retraso, correo_paciente, cita_id
        )
        _time.sleep(horas_retraso * 3600)

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("SELECT Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        if cfg and cfg['Estado_Envio'] == 0:
            logger.info(
                "[ENCUESTA] Kill-switch INACTIVO: no se envía correo para cita %d", cita_id
            )
            return

        from app import enviar_correo_smtp

        asunto      = "Tiene una nueva Encuesta de Satisfacción disponible – Stylo Dental"
        cuerpo_html = _html_encuesta_cita(nombre_paciente, nombre_especialista, login_url)

        ok, error = enviar_correo_smtp(correo_paciente, asunto, cuerpo_html)

        if ok:
            cur.execute(
                "UPDATE cita SET Encuesta_Enviada = 1 WHERE Cita_ID = ?", (cita_id,)
            )
            con.commit()
            logger.info(
                "[ENCUESTA] ✓ Correo enviado para cita %d a %s", cita_id, correo_paciente
            )
        else:
            logger.error(
                "[ENCUESTA] Fallo al enviar correo para cita %d: %s", cita_id, error
            )
    except Exception as exc:
        logger.error("[ENCUESTA] Error en hilo de envío (cita %d): %s", cita_id, exc)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE RANKING
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/config-ranking', methods=['GET'])
def get_config_ranking():
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("SELECT Config_ID, Horas_Envio, Estado_Envio FROM config_ranking LIMIT 1")
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO config_ranking (Horas_Envio, Estado_Envio) VALUES (2, 1)"
            )
            con.commit()
            return _json_ok({"Config_ID": 1, "Horas_Envio": 2, "Estado_Envio": 1})
        return _json_ok(dict(row))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/config-ranking', methods=['PUT'])
def put_config_ranking():
    datos        = request.get_json(silent=True) or {}
    horas_envio  = datos.get('Horas_Envio')
    estado_envio = datos.get('Estado_Envio')

    if horas_envio is None and estado_envio is None:
        return _json_error('Se requiere al menos Horas_Envio o Estado_Envio.')

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("SELECT Config_ID FROM config_ranking LIMIT 1")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO config_ranking (Horas_Envio, Estado_Envio) VALUES (2, 1)"
            )
            con.commit()

        campos  = []
        valores = []
        if horas_envio is not None:
            h = int(horas_envio)
            if h < 0:
                return _json_error('Horas_Envio no puede ser negativo.')
            campos.append("Horas_Envio = ?"); valores.append(h)
        if estado_envio is not None:
            campos.append("Estado_Envio = ?"); valores.append(1 if estado_envio else 0)

        cur.execute(
            f"UPDATE config_ranking SET {', '.join(campos)} WHERE Config_ID = 1",
            tuple(valores)
        )
        con.commit()
        return _json_ok({"ok": True, "mensaje": "Configuración actualizada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# USUARIOS — GET /api/usuarios
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT u.Usuario_ID, u.Nombres, u.Apellidos, u.NumeroDocumento,
                   u.Correo, u.Telefono, u.Estado_ID, u.Rol_ID, u.FechaNacimiento
            FROM usuarios u ORDER BY u.Apellidos
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# PACIENTE POR USUARIO — GET /api/paciente/por-usuario/<usuario_id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/por-usuario/<int:usuario_id>', methods=['GET'])
def get_paciente_por_usuario(usuario_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT p.Paciente_ID, p.Usuario_ID, u.Nombres, u.Apellidos,
                   u.NumeroDocumento, u.Correo, u.Telefono, u.FechaNacimiento
            FROM paciente p JOIN usuarios u ON u.Usuario_ID = p.Usuario_ID
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
# ESPECIALISTAS — GET /api/especialistas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialistas', methods=['GET'])
def get_especialistas():
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT e.Especialista_ID,
                   u.Nombres || ' ' || u.Apellidos AS NombreCompleto,
                   GROUP_CONCAT(esp.Nombre_Especialidad, ', ') AS Especialidades,
                   e.Tarjeta_Profesional
            FROM especialista e
            JOIN usuarios u ON u.Usuario_ID = e.Usuario_ID
            JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
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
# PERFIL DEL ESPECIALISTA — GET /api/especialista/perfil/<usuario_id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialista/perfil/<int:usuario_id>', methods=['GET'])
def get_perfil_especialista(usuario_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                td.Nombre_Tipo_Documento AS TipoDocumento,
                e.Especialista_ID,
                e.Tarjeta_Profesional,
                esp.Nombre_Especialidad  AS Especialidad
            FROM usuarios u
            JOIN especialista e
                 ON e.Usuario_ID = u.Usuario_ID
            LEFT JOIN tipo_documento td
                 ON td.TipoDoc_ID = u.TipoDoc_ID
            LEFT JOIN especialista_especialidad ee
                 ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp
                 ON esp.Especialidad_ID = ee.Especialidad_ID
            WHERE u.Usuario_ID = ?
            ORDER BY ee.Especialidad_ID ASC
            LIMIT 1
        """, (usuario_id,))
        fila = cur.fetchone()
        if not fila:
            return _json_error('Especialista no encontrado para ese usuario.', 404)

        perfil = dict(fila)
        defaults = {
            "NumeroDocumento":     "No registrado",
            "Correo":              "No registrado",
            "Telefono":            "No registrado",
            "TipoDocumento":       "—",
            "Tarjeta_Profesional": "No registrado",
            "Especialidad":        "—",
        }
        for campo, defecto in defaults.items():
            if perfil.get(campo) in (None, ""):
                perfil[campo] = defecto

        perfil["NombreCompleto"] = f"{perfil['Nombres']} {perfil['Apellidos']}".strip()
        return _json_ok({"ok": True, "perfil": perfil})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# AGENDA — GET /api/agenda   POST /api/agenda   DELETE /api/agenda/<id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/agenda', methods=['GET'])
def get_agenda():
    esp_id = request.args.get('especialista_id')
    fecha  = request.args.get('fecha')
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        sql = """
            SELECT a.Agenda_ID, a.Especialista_ID,
                   u.Nombres || ' ' || u.Apellidos AS NombreEspecialista,
                   esp.Nombre_Especialidad,
                   a.Fecha, a.Hora_Inicio,
                   a.Hora_Final AS Hora_Fin,
                   ea.Nombre_Estado AS EstadoAgenda
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
            sql += " AND a.Especialista_ID = ?"; params.append(esp_id)
        if fecha:
            sql += " AND a.Fecha = ?"; params.append(fecha)
        sql += " GROUP BY a.Agenda_ID ORDER BY a.Fecha, a.Hora_Inicio"
        cur.execute(sql, params)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


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
    if not _validar_fecha_no_anterior(fecha):
        return _json_error('No se puede crear un slot con fecha anterior a la actual.')
    if not _validar_hora_minimo_tres_horas(hora_inicio, fecha):
        return _json_error(
            'Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.'
        )

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?", (esp_id,)
        )
        if not cur.fetchone():
            return _json_error('Especialista no encontrado.', 404)
        cur.execute("""
            SELECT Agenda_ID FROM agenda
            WHERE Especialista_ID = ? AND Fecha = ? AND Hora_Inicio = ? AND EstadoAgenda_ID = 1
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


@citas_bp.route('/agenda/<int:agenda_id>', methods=['DELETE'])
def eliminar_agenda(agenda_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT Agenda_ID, EstadoAgenda_ID FROM agenda WHERE Agenda_ID = ?",
            (agenda_id,)
        )
        row = cur.fetchone()
        if not row:
            return _json_error('Horario no encontrado.', 404)
        if row['EstadoAgenda_ID'] != 1:
            return _json_error('Solo se pueden eliminar horarios con estado Disponible.', 409)
        cur.execute("DELETE FROM agenda WHERE Agenda_ID = ?", (agenda_id,))
        con.commit()
        return _json_ok({"ok": True, "status": "Horario eliminado correctamente."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS — GET /api/citas   POST /api/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas', methods=['GET'])
def get_citas():
    paciente_id     = request.args.get('paciente_id')
    especialista_id = request.args.get('especialista_id')
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        sql = """
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   p.Paciente_ID,
                   up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                   up.NumeroDocumento,
                   up.Telefono AS TelefonoPaciente,
                   up.Correo AS CorreoPaciente,
                   a.Agenda_ID, a.Fecha, a.Hora_Inicio,
                   a.Hora_Final AS Hora_Fin,
                   ea.Nombre_Estado AS EstadoAgenda,
                   e.Especialista_ID,
                   ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista,
                   esp.Nombre_Especialidad,
                   CASE
                     WHEN EXISTS (
                       SELECT 1 FROM respuesta_ranking rr WHERE rr.Cita_ID = c.Cita_ID
                     ) THEN 1
                     ELSE COALESCE(c.Encuesta_Enviada, 0)
                   END AS Encuesta_Completada
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
            sql += " AND p.Paciente_ID = ?"; params.append(paciente_id)
        if especialista_id:
            sql += " AND e.Especialista_ID = ?"; params.append(especialista_id)
        sql += " GROUP BY c.Cita_ID ORDER BY a.Fecha DESC, a.Hora_Inicio DESC"
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
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        cur.execute(
            """SELECT p.Paciente_ID, p.Usuario_ID, u.Rol_ID
               FROM paciente p JOIN usuarios u ON u.Usuario_ID = p.Usuario_ID
               WHERE p.Paciente_ID = ?""",
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

        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?",
            (slot['Especialista_ID'],)
        )
        if not cur.fetchone():
            cur.execute("ROLLBACK")
            return _json_error('El especialista asociado al horario no existe.', 404)

        if not _validar_fecha_no_anterior(slot['Fecha']):
            cur.execute("ROLLBACK")
            return _json_error('No se puede agendar una cita con fecha anterior a la actual.')
        if not _validar_hora_minimo_tres_horas(slot['Hora_Inicio'], slot['Fecha']):
            cur.execute("ROLLBACK")
            return _json_error(
                'Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.'
            )
        if _tiene_cita_activa_por_usuario(cur, usuario_id_paciente):
            cur.execute("ROLLBACK")
            return _json_error('No puedes agendar. Ya tienes una cita activa en el sistema.', 409)

        cur.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta, Encuesta_Enviada) VALUES (?, ?, ?, 0)",
            (paciente_id, agenda_id, motivo)
        )
        cita_id = cur.lastrowid
        if not cita_id:
            cur.execute("ROLLBACK")
            return _json_error('No se pudo registrar la cita en el sistema.', 500)

        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 2 WHERE Agenda_ID = ?", (agenda_id,))
        if cur.rowcount == 0:
            cur.execute("ROLLBACK")
            return _json_error('No se pudo actualizar el estado de la agenda.', 500)

        cur.execute("COMMIT")
        return _json_ok({"ok": True, "Cita_ID": cita_id, "status": "Cita registrada con éxito."}, 201)

    except Exception as exc:
        if con:
            try: con.execute("ROLLBACK")
            except Exception: pass
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITA INDIVIDUAL — GET /api/citas/<id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>', methods=['GET'])
def get_cita(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   p.Paciente_ID,
                   up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                   up.NumeroDocumento,
                   up.Correo AS CorreoPaciente,
                   up.Telefono AS TelefonoPaciente,
                   COALESCE(td.Nombre_Tipo_Documento, 'DOC') AS TipoDocumento,
                   a.Fecha, a.Hora_Inicio,
                   a.Hora_Final AS Hora_Fin,
                   ea.Nombre_Estado AS EstadoAgenda,
                   ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista,
                   CASE
                     WHEN EXISTS (
                       SELECT 1 FROM respuesta_ranking rr WHERE rr.Cita_ID = c.Cita_ID
                     ) THEN 1
                     ELSE COALESCE(c.Encuesta_Enviada, 0)
                   END AS Encuesta_Completada
            FROM cita c
            JOIN paciente p    ON p.Paciente_ID = c.Paciente_ID
            JOIN usuarios up   ON up.Usuario_ID = p.Usuario_ID
            LEFT JOIN tipo_documento td ON td.TipoDoc_ID = up.TipoDoc_ID
            JOIN agenda a      ON a.Agenda_ID   = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue   ON ue.Usuario_ID = e.Usuario_ID
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
# ATENDER CITA — PUT /api/citas/<id>/atender
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/atender', methods=['PUT'])
def atender_cita(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID, a.EstadoAgenda_ID, a.Agenda_ID
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        if row['EstadoAgenda_ID'] not in (1, 2):
            return _json_error('La cita no está en un estado que permita atención.')
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 2 WHERE Agenda_ID = ?",
            (row['Agenda_ID'],)
        )
        con.commit()
        return _json_ok({"ok": True, "status": "Cita marcada como en atención."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# MARCAR CITA ATENDIDA — PUT /api/citas/<id>/atendido
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/atendido', methods=['PUT'])
def marcar_atendido(cita_id):
    datos        = request.get_json(silent=True) or {}
    diagnosticos = datos.get('Diagnosticos') or datos.get('diagnosticos') or []
    if isinstance(diagnosticos, str):
        diagnosticos = [diagnosticos]
    evolucion   = datos.get('Evolucion')   or datos.get('evolucion')   or ''
    tratamiento = datos.get('Tratamiento') or datos.get('tratamiento') or ''

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        cur.execute("SELECT Agenda_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("ROLLBACK")
            return _json_error('Cita no encontrada.', 404)

        agenda_id      = row['Agenda_ID']
        fecha_hora_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 4 WHERE Agenda_ID = ?",
            (agenda_id,)
        )

        cur.execute("PRAGMA table_info(cita)")
        columnas_cita = [col[1] for col in cur.fetchall()]
        if 'FechaAtencion' not in columnas_cita:
            try:
                cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
            except Exception:
                pass

        cur.execute(
            "UPDATE cita SET FechaAtencion = ? WHERE Cita_ID = ?",
            (fecha_hora_fin, cita_id)
        )

        historial_id = _garantizar_historial_clinico(
            cur, cita_id,
            diagnosticos=diagnosticos,
            evolucion=evolucion,
            tratamiento=tratamiento,
        )

        cur.execute("COMMIT")
        return _json_ok({
            "ok": True,
            "status": "Cita marcada como Atendida.",
            "Historial_ID": historial_id,
            "FechaAtencion": fecha_hora_fin,
        })

    except Exception as exc:
        if con:
            try: con.execute("ROLLBACK")
            except Exception: pass
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# FINALIZAR CONSULTA — PUT /api/citas/<id>/finalizar-consulta
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/finalizar-consulta', methods=['PUT'])
def finalizar_consulta(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Encuesta_Enviada,
                a.Agenda_ID,
                a.EstadoAgenda_ID,
                up.Correo                          AS CorreoPaciente,
                up.Nombres || ' ' || up.Apellidos  AS NombrePaciente,
                ue.Nombres || ' ' || ue.Apellidos  AS NombreEspecialista,
                p.Paciente_ID
            FROM cita c
            JOIN agenda a      ON a.Agenda_ID    = c.Agenda_ID
            JOIN paciente p    ON p.Paciente_ID  = c.Paciente_ID
            JOIN usuarios up   ON up.Usuario_ID  = p.Usuario_ID
            JOIN especialista e   ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios ue   ON ue.Usuario_ID  = e.Usuario_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)

        if row['EstadoAgenda_ID'] not in (1, 2):
            return _json_error(
                'Solo se puede finalizar una cita en estado Disponible u Ocupado.'
            )

        fecha_hora_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 4 WHERE Agenda_ID = ?",
            (row['Agenda_ID'],)
        )

        cur.execute("PRAGMA table_info(cita)")
        columnas_cita = [col[1] for col in cur.fetchall()]
        if 'FechaAtencion' not in columnas_cita:
            try:
                cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
            except Exception:
                pass

        cur.execute(
            "UPDATE cita SET FechaAtencion = ? WHERE Cita_ID = ?",
            (fecha_hora_fin, cita_id)
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS encuesta_pendiente (
                Pendiente_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
                Cita_ID        INT NOT NULL,
                Paciente_ID    INT NOT NULL,
                Fecha_Creacion TEXT NOT NULL,
                Completada     INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (Cita_ID)     REFERENCES cita(Cita_ID),
                FOREIGN KEY (Paciente_ID) REFERENCES paciente(Paciente_ID)
            )
        """)

        cur.execute(
            "SELECT Pendiente_ID FROM encuesta_pendiente WHERE Cita_ID = ?", (cita_id,)
        )
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO encuesta_pendiente (Cita_ID, Paciente_ID, Fecha_Creacion, Completada)
                VALUES (?, ?, ?, 0)
            """, (cita_id, row['Paciente_ID'], fecha_hora_fin))

        con.commit()

        cur.execute("SELECT Horas_Envio, Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        horas_envio  = cfg['Horas_Envio']  if cfg else 2
        estado_envio = cfg['Estado_Envio'] if cfg else 1

        if estado_envio == 0:
            return _json_ok({
                "ok": True,
                "status": "Consulta finalizada. Envío de encuesta desactivado (kill-switch).",
                "correo_enviado": False,
                "FechaAtencion": fecha_hora_fin,
            })

        correo_paciente     = row['CorreoPaciente']
        nombre_paciente     = row['NombrePaciente']
        nombre_especialista = row['NombreEspecialista']

        base_url  = request.host_url.rstrip('/')
        login_url = f"{base_url}/login.html"

        if correo_paciente:
            hilo = threading.Thread(
                target=_despachar_correo_encuesta,
                args=(
                    cita_id,
                    correo_paciente,
                    nombre_paciente,
                    nombre_especialista,
                    horas_envio,
                    login_url,
                ),
                daemon=True,
                name=f"encuesta-cita-{cita_id}",
            )
            hilo.start()
            correo_msg = (
                f"Correo de encuesta programado para {correo_paciente} "
                f"con {horas_envio}h de retraso."
            )
        else:
            correo_msg = "No se encontró correo del paciente; no se enviará notificación."

        return _json_ok({
            "ok": True,
            "status": f"Consulta finalizada. {correo_msg}",
            "correo_enviado": bool(correo_paciente),
            "FechaAtencion": fecha_hora_fin,
        })

    except Exception as exc:
        if con:
            try: con.rollback()
            except Exception: pass
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# ENCUESTAS PENDIENTES — GET /api/paciente/<id>/encuestas-pendientes
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/encuestas-pendientes', methods=['GET'])
def get_encuestas_pendientes(paciente_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS encuesta_pendiente (
                Pendiente_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
                Cita_ID        INT NOT NULL,
                Paciente_ID    INT NOT NULL,
                Fecha_Creacion TEXT NOT NULL,
                Completada     INTEGER NOT NULL DEFAULT 0
            )
        """)
        con.commit()

        cur.execute("""
            SELECT ep.Pendiente_ID, ep.Cita_ID, ep.Fecha_Creacion,
                   c.Motivo_Consulta,
                   ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista,
                   a.Fecha AS FechaCita
            FROM encuesta_pendiente ep
            JOIN cita c         ON c.Cita_ID       = ep.Cita_ID
            JOIN agenda a       ON a.Agenda_ID      = c.Agenda_ID
            JOIN especialista e ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios ue    ON ue.Usuario_ID    = e.Usuario_ID
            WHERE ep.Paciente_ID = ? AND ep.Completada = 0
            ORDER BY ep.Fecha_Creacion DESC
        """, (paciente_id,))
        pendientes = _rows_to_list(cur)
        return _json_ok({
            "ok": True,
            "total": len(pendientes),
            "pendientes": pendientes
        })
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR CITA SIN MULTA — PUT /api/citas/<id>/cancelar-sin-multa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-sin-multa', methods=['PUT'])
def cancelar_cita_sin_multa(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Agenda_ID, a.Fecha, a.Hora_Inicio
            FROM cita c JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        if _calcular_minutos_restantes(row['Fecha'], row['Hora_Inicio']) <= 120:
            return _json_error(
                'No se puede cancelar sin multa: faltan 2 horas o menos para la cita.', 409
            )
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (row['Agenda_ID'],)
        )
        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada sin penalización."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR CITA CON MULTA — PUT /api/citas/<id>/cancelar-con-multa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-con-multa', methods=['PUT'])
def cancelar_cita_con_multa(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Agenda_ID FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        agenda_id = row['Agenda_ID']
        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (agenda_id,))
        cur.execute("INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,))
        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR PACIENTE — GET /api/paciente/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/citas', methods=['GET'])
def get_citas_paciente(paciente_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID,
                   c.Motivo_Consulta,
                   c.Encuesta_Enviada,
                   a.Fecha,
                   a.Hora_Inicio,
                   a.Hora_Final                          AS Hora_Fin,
                   ea.Nombre_Estado                      AS EstadoAgenda,
                   ue.Nombres || ' ' || ue.Apellidos     AS NombreEspecialista,
                   esp.Nombre_Especialidad,
                   up.Nombres || ' ' || up.Apellidos     AS NombrePaciente,
                   up.NumeroDocumento,
                   COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta,
                   CASE
                     WHEN EXISTS (
                       SELECT 1 FROM respuesta_ranking rr WHERE rr.Cita_ID = c.Cita_ID
                     ) THEN 1
                     ELSE COALESCE(c.Encuesta_Enviada, 0)
                   END AS Encuesta_Completada
            FROM cita c
            JOIN agenda a         ON a.Agenda_ID       = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue      ON ue.Usuario_ID      = e.Usuario_ID
            JOIN paciente p       ON p.Paciente_ID      = c.Paciente_ID
            JOIN usuarios up      ON up.Usuario_ID      = p.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp             ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m      ON m.Cita_ID         = c.Cita_ID
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
# CITAS POR ESPECIALISTA — GET /api/especialista/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialista/<int:especialista_id>/citas', methods=['GET'])
def get_citas_especialista(especialista_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("PRAGMA table_info(cita)")
        columnas_cita = [col[1] for col in cur.fetchall()]
        fecha_atencion_col = "c.FechaAtencion" if 'FechaAtencion' in columnas_cita else "NULL AS FechaAtencion"

        cur.execute(f"""
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   {fecha_atencion_col},
                   a.Fecha, a.Hora_Inicio,
                   a.Hora_Final AS Hora_Fin,
                   ea.Nombre_Estado AS EstadoAgenda,
                   up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                   up.NumeroDocumento,
                   COALESCE(td.Nombre_Tipo_Documento, 'DOC') AS TipoDocumento,
                   up.Telefono AS TelefonoPaciente,
                   esp.Nombre_Especialidad,
                   COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta
            FROM cita c
            JOIN agenda a    ON a.Agenda_ID    = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN paciente p  ON p.Paciente_ID  = c.Paciente_ID
            JOIN usuarios up ON up.Usuario_ID  = p.Usuario_ID
            LEFT JOIN tipo_documento td ON td.TipoDoc_ID = up.TipoDoc_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = a.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m  ON m.Cita_ID = c.Cita_ID
            LEFT JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            WHERE a.Especialista_ID = ?
            GROUP BY c.Cita_ID
            ORDER BY a.Fecha, a.Hora_Inicio
        """, (especialista_id,))
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# MULTAS
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/multas', methods=['GET'])
def get_multas():
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID, m.Cita_ID,
                   em.Nombre_Estado AS EstadoMulta,
                   up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                   a.Fecha, a.Hora_Inicio
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
        con = _get_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT Multa_ID, EstadoMulta_ID FROM multa WHERE Multa_ID = ?", (multa_id,)
        )
        row = cur.fetchone()
        if not row:
            return _json_error('Multa no encontrada.', 404)
        if row['EstadoMulta_ID'] == 2:
            return _json_error('La multa ya está marcada como Pagada.', 409)
        cur.execute("UPDATE multa SET EstadoMulta_ID = 2 WHERE Multa_ID = ?", (multa_id,))
        con.commit()
        return _json_ok({"ok": True, "status": "Multa marcada como Pagada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/paciente/<int:paciente_id>/multa-activa', methods=['GET'])
def multa_activa(paciente_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID FROM multa m
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
# HISTORIAL CLÍNICO — POST /api/historial-clinico
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
        con = _get_conn()
        cur = con.cursor()
        cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        if not cur.fetchone():
            return _json_error('Cita no encontrada.', 404)

        historial_id = _garantizar_historial_clinico(
            cur, cita_id,
            diagnosticos=[diagnostico] if diagnostico else [],
            evolucion=evolucion,
            tratamiento=tratamiento,
        )
        con.commit()
        return _json_ok({"ok": True, "Historial_ID": historial_id}, 201)
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# HISTORIAL CLÍNICO — GET /api/historial-clinico/<cita_id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/historial-clinico/<int:cita_id>', methods=['GET'])
def get_historial_clinico(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
        )
        hc_row = cur.fetchone()
        if not hc_row:
            return _json_ok(
                {"ok": False, "error": "Sin historial clínico registrado para esta cita."}, 200
            )

        historial_id = hc_row['Historial_ID']

        cur.execute("""
            SELECT d.Nombre_Diagnostico AS Diagnostico
            FROM historial_diagnostico hd
            JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
            WHERE hd.Historial_ID = ?
            ORDER BY hd.rowid DESC LIMIT 1
        """, (historial_id,))
        diag_row = cur.fetchone()

        cur.execute("""
            SELECT Descripcion, FechaRegistro
            FROM tratamiento
            WHERE Historial_ID = ?
            ORDER BY rowid DESC LIMIT 1
        """, (historial_id,))
        trat_row = cur.fetchone()

        diagnostico    = diag_row['Diagnostico']   if diag_row else 'Sin diagnóstico'
        fecha_registro = trat_row['FechaRegistro'] if trat_row else 'N/A'
        descripcion    = trat_row['Descripcion']   if trat_row else ''

        if '---' in descripcion:
            partes      = descripcion.split('---', 1)
            evolucion   = partes[0].strip()
            tratamiento = partes[1].strip()
        else:
            evolucion   = descripcion
            tratamiento = ''

        return _json_ok({
            "ok": True,
            "data": {
                "Historial_ID":  historial_id,
                "Cita_ID":       cita_id,
                "Diagnostico":   diagnostico,
                "Evolucion":     evolucion,
                "Tratamiento":   tratamiento,
                "FechaRegistro": fecha_registro,
            }
        })
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# RANKING — POST /api/respuesta
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
            return _json_error('Texto_Respuesta debe ser un número entero entre 1 y 5.')
    except (ValueError, TypeError):
        return _json_error(
            f'Texto_Respuesta debe ser un entero (1-5), recibido: {texto_respuesta!r}'
        )

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("SELECT Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        if cfg and cfg['Estado_Envio'] == 0:
            return _json_error(
                'El sistema de evaluaciones está temporalmente desactivado.', 503
            )

        if cita_id:
            cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
            if not cur.fetchone():
                return _json_error(f'Cita_ID {cita_id} no encontrada.', 404)
            cita_id_final = cita_id
        else:
            cur.execute("""
                SELECT c.Cita_ID FROM cita c
                WHERE c.Paciente_ID = ? ORDER BY c.Cita_ID DESC LIMIT 1
            """, (paciente_id,))
            fila = cur.fetchone()
            if not fila:
                return _json_error(
                    f'No se encontró ninguna cita para el paciente ID {paciente_id}.', 404
                )
            cita_id_final = fila['Cita_ID']

        cur.execute("SELECT Paciente_ID FROM cita WHERE Cita_ID = ?", (cita_id_final,))
        cita_row = cur.fetchone()
        if not cita_row or str(cita_row['Paciente_ID']) != str(paciente_id):
            return _json_error('La cita no pertenece a este paciente.', 403)

        cur.execute("""
            SELECT Respuesta_ID FROM respuesta_ranking
            WHERE Cita_ID = ? AND Preguntas_ID = ?
        """, (cita_id_final, pregunta_id))
        if cur.fetchone():
            return _json_error('Ya existe una respuesta para esta pregunta en esta cita.')

        cur.execute(
            "SELECT Preguntas_ID FROM preguntas_ranking WHERE Preguntas_ID = ? AND Activa = 1",
            (pregunta_id,)
        )
        if not cur.fetchone():
            return _json_error('La pregunta no existe o está inactiva.', 404)

        cur.execute("""
            INSERT INTO respuesta_ranking (Cita_ID, Preguntas_ID, Respuesta)
            VALUES (?, ?, ?)
        """, (cita_id_final, pregunta_id, valor_int))
        respuesta_id = cur.lastrowid

        cur.execute("""
            SELECT a.Especialista_ID FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id_final,))
        esp_row = cur.fetchone()
        if esp_row:
            especialista_id = esp_row['Especialista_ID']
            cur.execute("""
                INSERT INTO puntuacion_especialista (Especialista_ID, Respuesta_ID)
                VALUES (?, ?)
            """, (especialista_id, respuesta_id))
            nuevo_promedio = _crear_promedio(cur, especialista_id)
            logger.info(
                "[RANKING] Especialista %d — nuevo promedio: %.2f",
                especialista_id, nuevo_promedio
            )

        cur.execute(
            "SELECT COUNT(*) AS total FROM preguntas_ranking WHERE Activa = 1"
        )
        total_preguntas = cur.fetchone()['total']
        cur.execute(
            "SELECT COUNT(*) AS respondidas FROM respuesta_ranking WHERE Cita_ID = ?",
            (cita_id_final,)
        )
        total_respondidas = cur.fetchone()['respondidas']

        if total_respondidas >= total_preguntas:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS encuesta_pendiente (
                    Pendiente_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
                    Cita_ID        INT NOT NULL,
                    Paciente_ID    INT NOT NULL,
                    Fecha_Creacion TEXT NOT NULL,
                    Completada     INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute(
                "UPDATE encuesta_pendiente SET Completada = 1 WHERE Cita_ID = ?",
                (cita_id_final,)
            )
            logger.info("[RANKING] Encuesta completada para cita %d", cita_id_final)

        con.commit()
        return _json_ok({"ok": True, "Respuesta_ID": respuesta_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR CONTRASEÑA — POST /api/verificar-password
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/verificar-password', methods=['POST'])
def verificar_password():
    from werkzeug.security import check_password_hash

    datos      = request.get_json(silent=True) or {}
    usuario_id = datos.get('usuario_id')
    password   = datos.get('password')

    if not usuario_id or not password:
        return _json_error('usuario_id y password son obligatorios.')

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (usuario_id,))
        row = cur.fetchone()
        if not row:
            return _json_ok({"ok": False, "error": "Usuario no encontrado."})

        hash_bd = row['Contrasena']
        if hash_bd.startswith('scrypt:') or hash_bd.startswith('pbkdf2:'):
            autenticado = check_password_hash(hash_bd, password)
        else:
            autenticado = (hash_bd == password)

        if autenticado:
            return _json_ok({"ok": True})
        return _json_ok({"ok": False, "error": "Contraseña incorrecta."})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZAR PERFIL PACIENTE — POST /api/actualizar-perfil-paciente
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/actualizar-perfil-paciente', methods=['POST'])
def actualizar_perfil_paciente():
    from werkzeug.security import generate_password_hash, check_password_hash

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
        return _json_error('usuario_id es obligatorio.')

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        campos  = []
        valores = []

        if nombres:           campos.append("Nombres = ?");          valores.append(nombres)
        if apellidos:         campos.append("Apellidos = ?");        valores.append(apellidos)
        if documento:         campos.append("NumeroDocumento = ?");  valores.append(documento)
        if tipo_documento_id: campos.append("TipoDoc_ID = ?");       valores.append(tipo_documento_id)
        if correo:            campos.append("Correo = ?");           valores.append(correo)
        if telefono:          campos.append("Telefono = ?");         valores.append(telefono)
        if nacimiento:        campos.append("FechaNacimiento = ?");  valores.append(nacimiento)

        if nueva_pass:
            if not contrasena_actual:
                return _json_error('Debes ingresar tu contraseña actual para cambiarla.', 400)

            cur.execute("SELECT Contrasena FROM usuarios WHERE Usuario_ID = ?", (usuario_id,))
            fila_pwd = cur.fetchone()
            if not fila_pwd:
                return _json_error('Usuario no encontrado.', 404)

            hash_bd = fila_pwd['Contrasena']
            if hash_bd.startswith('scrypt:') or hash_bd.startswith('pbkdf2:'):
                pwd_ok = check_password_hash(hash_bd, contrasena_actual)
            else:
                pwd_ok = (hash_bd == contrasena_actual)

            if not pwd_ok:
                return _json_error('La contraseña actual es incorrecta.', 401)

            ok, msg = _validar_politica_password(nueva_pass)
            if not ok:
                return _json_error(msg, 400)
            campos.append("Contrasena = ?")
            valores.append(generate_password_hash(nueva_pass, method='scrypt'))

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
                    UPDATE afiliacion SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
                    WHERE Afiliacion_ID = ?
                """, (eps_final, tipo_eps_final, date.today().isoformat(), afil_row['Afiliacion_ID']))
            elif eps_final and tipo_eps_final:
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