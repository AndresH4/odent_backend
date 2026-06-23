"""
modulo_citas/routes.py — Stylo Dental
======================================
Endpoints REST para:
  • /api/citas                         — listar y crear citas
  • /api/citas/<id>                    — detalle, actualizar estado y cancelar
  • /api/agenda                        — slots disponibles (GET) y creación (POST)
  • /api/especialistas                 — lista de especialistas con especialidad
  • /api/multas                        — listar y actualizar multas
  • /api/paciente/<id>/citas           — citas de un paciente específico
  • /api/paciente/<id>/multa-activa    — verificar multa pendiente
  • /api/paciente/por-usuario/<uid>    — resolver Paciente_ID desde Usuario_ID
  • /api/especialista/<id>/citas       — citas asignadas a un especialista
  • /api/usuarios                      — lista de usuarios
  • /api/historial-clinico             — registrar evolución clínica
  • /api/respuesta                     — registrar respuesta de ranking
  • /api/verificar-password            — verificar contraseña del paciente
  • /api/actualizar-perfil-paciente    — actualizar datos del paciente
  • /api/citas/<id>/cancelar-sin-multa — cancelar sin penalización
  • /api/citas/<id>/cancelar-con-multa — cancelar con multa
  • /api/citas/<id>/atender            — REQ 3: especialista marca "En atención"
  • /api/citas/<id>/finalizar-consulta — REQ 3/4: finaliza y dispara correo encuesta
  • /api/config-ranking                — REQ 8/9: GET y PUT de configuración
"""

from flask import Blueprint, request, jsonify
from db import get_db_connection
from datetime import date, datetime, timedelta
import re
import threading
import logging

logger = logging.getLogger("stylo_dental_smtp")

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
        hora = datetime.strptime(hora_str[:5], '%H:%M').time()
        ahora  = datetime.now()
        limite = ahora + timedelta(hours=3)
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
# REQ 8/9 — CONFIGURACIÓN DE RANKING
# GET /api/config-ranking   → devuelve { Horas_Envio, Estado_Envio }
# PUT /api/config-ranking   → actualiza la fila única de config_ranking
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/config-ranking', methods=['GET'])
def get_config_ranking():
    """
    Devuelve la configuración de envío automático de encuestas.
    REQ 8: Horas_Envio  — retraso en horas desde la finalización de consulta.
    REQ 9: Estado_Envio — 1=ACTIVO (envía correos), 0=INACTIVO (kill-switch).
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Config_ID, Horas_Envio, Estado_Envio FROM config_ranking LIMIT 1")
        row = cur.fetchone()
        if not row:
            # Crear la fila de configuración si no existe (migración segura)
            cur.execute("INSERT INTO config_ranking (Horas_Envio, Estado_Envio) VALUES (2, 1)")
            con.commit()
            return _json_ok({"Config_ID": 1, "Horas_Envio": 2, "Estado_Envio": 1})
        return _json_ok(dict(row))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/config-ranking', methods=['PUT'])
def put_config_ranking():
    """
    Actualiza Horas_Envio y/o Estado_Envio.
    REQ 8: horas_envio  → cuántas horas esperar antes de enviar el correo.
    REQ 9: estado_envio → kill-switch: 0=INACTIVO detiene TODO envío/renderizado.
    """
    datos        = request.get_json(silent=True) or {}
    horas_envio  = datos.get('Horas_Envio')
    estado_envio = datos.get('Estado_Envio')

    if horas_envio is None and estado_envio is None:
        return _json_error('Se requiere al menos Horas_Envio o Estado_Envio.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # Asegurar que existe la fila de configuración
        cur.execute("SELECT Config_ID FROM config_ranking LIMIT 1")
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO config_ranking (Horas_Envio, Estado_Envio) VALUES (2, 1)")
            con.commit()

        campos  = []
        valores = []
        if horas_envio is not None:
            h = int(horas_envio)
            if h < 0:
                return _json_error('Horas_Envio no puede ser negativo.')
            campos.append("Horas_Envio = ?")
            valores.append(h)
        if estado_envio is not None:
            e = 1 if estado_envio else 0
            campos.append("Estado_Envio = ?")
            valores.append(e)

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
# REQ 3 — ATENDER CITA  —  PUT /api/citas/<id>/atender
# El especialista hace clic en "ATENDER": estado permanece Ocupado (2) pero
# el frontend puede usar este endpoint para registrar el inicio de atención.
# En la arquitectura actual EstadoAgenda 2 = "Ocupado" es el estado de "en
# curso"; no se agrega un estado adicional para "En Atención" ya que el flujo
# continúa directamente hasta FINALIZAR.
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/atender', methods=['PUT'])
def atender_cita(cita_id):
    """
    Registra el inicio de atención de una cita.
    Mantiene EstadoAgenda_ID = 2 (Ocupado/En atención).
    Devuelve confirmación para que el frontend habilite el formulario clínico.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID, a.EstadoAgenda_ID
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        if row['EstadoAgenda_ID'] not in (1, 2):
            return _json_error('La cita no está en un estado que permita atención.')
        # Asegurar que la agenda esté en estado "Ocupado"
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 2 WHERE Agenda_ID = (SELECT Agenda_ID FROM cita WHERE Cita_ID = ?)",
            (cita_id,)
        )
        con.commit()
        return _json_ok({"ok": True, "status": "Cita marcada como en atención."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# REQ 3/4 — FINALIZAR CONSULTA  —  PUT /api/citas/<id>/finalizar-consulta
#
# Flujo completo:
#   1. Marca la agenda como Cumplida (EstadoAgenda_ID = 4).
#   2. Verifica el kill-switch (REQ 9): si Estado_Envio = 0, no envía nada.
#   3. Lee Horas_Envio de config_ranking (REQ 8).
#   4. Programa el envío de correo al paciente en un hilo daemon con el
#      retraso configurado.
#   5. El correo incluye llamado a calificar + enlace absoluto a login.html.
#   6. Marca cita.Encuesta_Enviada = 1 una vez despachado el correo.
# ─────────────────────────────────────────────────────────────────────────────

def _html_encuesta_cita(nombre_paciente: str, nombre_especialista: str, login_url: str) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:520px;margin:auto;
                border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#0369a1,#0ea5e9);
                  padding:28px 32px;text-align:center;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;letter-spacing:0.5px;">
          🦷 Stylo Dental
        </h1>
        <p style="color:#bae6fd;margin:6px 0 0;font-size:14px;">
          Evaluación de servicio odontológico
        </p>
      </div>
      <div style="padding:32px;background:#ffffff;">
        <p style="color:#334155;font-size:15px;margin-top:0;">
          Estimado(a) <strong>{nombre_paciente}</strong>,
        </p>
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Su consulta con <strong>Dr(a). {nombre_especialista}</strong> ha finalizado.
          En Clínica Stylo Dental valoramos su opinión y nos gustaría que calificara
          la atención recibida.
        </p>
        <p style="color:#475569;font-size:14px;line-height:1.6;">
          Por favor, ingrese a nuestra plataforma y complete la encuesta de satisfacción.
          Su retroalimentación es fundamental para mejorar nuestro servicio.
        </p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{login_url}"
             style="display:inline-block;background:linear-gradient(135deg,#0369a1,#0ea5e9);
                    color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;
                    font-size:15px;font-weight:700;letter-spacing:0.3px;">
            Calificar mi experiencia ★
          </a>
        </div>
        <p style="color:#64748b;font-size:12px;margin-bottom:0;">
          Si el botón no funciona, copie y pegue este enlace en su navegador:<br>
          <a href="{login_url}" style="color:#0284c7;">{login_url}</a>
        </p>
      </div>
      <div style="background:#f8fafc;padding:16px 32px;text-align:center;
                  border-top:1px solid #e2e8f0;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">
          © 2025 Clínica Stylo Dental · Todos los derechos reservados
        </p>
      </div>
    </div>
    """


def _despachar_correo_encuesta(cita_id: int, correo_paciente: str,
                                nombre_paciente: str, nombre_especialista: str,
                                horas_retraso: int, login_url: str):
    """
    Ejecutado en hilo daemon.
    Espera Horas_Envio horas, verifica el kill-switch nuevamente y envía el correo.
    Tras el envío exitoso marca Encuesta_Enviada = 1 en la BD.
    """
    import time as _time

    if horas_retraso > 0:
        logger.info(
            "[ENCUESTA] Esperando %d hora(s) antes de enviar correo a %s (cita %d)",
            horas_retraso, correo_paciente, cita_id
        )
        _time.sleep(horas_retraso * 3600)

    # Re-verificar el kill-switch DESPUÉS del retraso (REQ 9)
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        if cfg and cfg['Estado_Envio'] == 0:
            logger.info(
                "[ENCUESTA] Kill-switch INACTIVO: no se envía correo para cita %d", cita_id
            )
            return

        # Importar la función de envío centralizada desde app.py a través del contexto
        from app import enviar_correo_smtp

        asunto      = "Califica tu experiencia en Stylo Dental ★"
        cuerpo_html = _html_encuesta_cita(nombre_paciente, nombre_especialista, login_url)

        ok, error = enviar_correo_smtp(correo_paciente, asunto, cuerpo_html)

        if ok:
            # Marcar encuesta como enviada (REQ 4)
            cur.execute(
                "UPDATE cita SET Encuesta_Enviada = 1 WHERE Cita_ID = ?",
                (cita_id,)
            )
            con.commit()
            logger.info("[ENCUESTA] ✓ Correo enviado para cita %d a %s", cita_id, correo_paciente)
        else:
            logger.error("[ENCUESTA] Fallo al enviar correo para cita %d: %s", cita_id, error)

    except Exception as exc:
        logger.error("[ENCUESTA] Error en hilo de envío (cita %d): %s", cita_id, exc)
    finally:
        if con:
            con.close()


@citas_bp.route('/citas/<int:cita_id>/finalizar-consulta', methods=['PUT'])
def finalizar_consulta(cita_id):
    """
    REQ 3/4 — Finalización de consulta por el especialista.
    Pasos:
      1. Valida que la cita exista y esté en estado Ocupado (2).
      2. Cambia EstadoAgenda_ID = 4 (Cumplida).
      3. REQ 9: Verifica kill-switch Estado_Envio en config_ranking.
      4. REQ 8: Lee Horas_Envio de config_ranking.
      5. Obtiene el correo del paciente asociado a la cita.
      6. Programa el envío en hilo daemon con el retraso configurado.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # ── 1. Obtener datos completos de la cita ─────────────────────────────
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Encuesta_Enviada,
                a.Agenda_ID,
                a.EstadoAgenda_ID,
                up.Correo                          AS CorreoPaciente,
                up.Nombres || ' ' || up.Apellidos  AS NombrePaciente,
                ue.Nombres || ' ' || ue.Apellidos  AS NombreEspecialista
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

        # ── 2. Marcar agenda como Cumplida (EstadoAgenda_ID = 4) ─────────────
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 4 WHERE Agenda_ID = ?",
            (row['Agenda_ID'],)
        )
        con.commit()

        # ── 3. Verificar kill-switch (REQ 9) ──────────────────────────────────
        cur.execute("SELECT Horas_Envio, Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        horas_envio  = cfg['Horas_Envio']  if cfg else 2
        estado_envio = cfg['Estado_Envio'] if cfg else 1

        if estado_envio == 0:
            logger.info(
                "[ENCUESTA] Kill-switch INACTIVO: cita %d finalizada sin envío de correo.", cita_id
            )
            return _json_ok({
                "ok":      True,
                "status":  "Consulta finalizada. Envío de encuesta desactivado (kill-switch).",
                "correo_enviado": False,
            })

        # ── 4/5/6. Programar envío en hilo daemon ────────────────────────────
        correo_paciente    = row['CorreoPaciente']
        nombre_paciente    = row['NombrePaciente']
        nombre_especialista = row['NombreEspecialista']

        # URL absoluta a login.html (REQ 4)
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
            logger.info(
                "[ENCUESTA] Hilo iniciado para cita %d → %s (retraso %dh)",
                cita_id, correo_paciente, horas_envio
            )
            correo_msg = f"Correo programado para {correo_paciente} con {horas_envio}h de retraso."
        else:
            correo_msg = "No se encontró correo del paciente; no se enviará notificación."
            logger.warning("[ENCUESTA] Cita %d sin correo de paciente.", cita_id)

        return _json_ok({
            "ok":     True,
            "status": f"Consulta finalizada. {correo_msg}",
            "correo_enviado": bool(correo_paciente),
        })

    except Exception as exc:
        if con:
            try: con.rollback()
            except Exception: pass
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


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
            SELECT u.Usuario_ID, u.Nombres, u.Apellidos, u.NumeroDocumento,
                   u.Correo, u.Telefono, u.Estado_ID, u.Rol_ID, u.FechaNacimiento
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
            SELECT p.Paciente_ID, p.Usuario_ID, u.Nombres, u.Apellidos,
                   u.NumeroDocumento, u.Correo, u.Telefono, u.FechaNacimiento
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
            SELECT e.Especialista_ID,
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
                INSERT INTO especialista (Usuario_ID, Tarjeta_Profesional) VALUES (?, ?)
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
            SELECT a.Agenda_ID, a.Especialista_ID,
                   u.Nombres || ' ' || u.Apellidos  AS NombreEspecialista,
                   esp.Nombre_Especialidad,
                   a.Fecha, a.Hora_Inicio,
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
            sql += " AND a.Especialista_ID = ?"; params.append(esp_id)
        if fecha:
            sql += " AND a.Fecha = ?"; params.append(fecha)
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
    if not _validar_fecha_no_anterior(fecha):
        return _json_error('No se puede crear un slot con fecha anterior a la actual.')
    if not _validar_hora_minimo_tres_horas(hora_inicio, fecha):
        return _json_error('Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?", (esp_id,))
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
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   p.Paciente_ID,
                   up.Nombres || ' ' || up.Apellidos  AS NombrePaciente,
                   up.NumeroDocumento,
                   up.Telefono                        AS TelefonoPaciente,
                   up.Correo                          AS CorreoPaciente,
                   a.Agenda_ID, a.Fecha, a.Hora_Inicio,
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
            sql += " AND p.Paciente_ID = ?"; params.append(paciente_id)
        if especialista_id:
            sql += " AND e.Especialista_ID = ?"; params.append(especialista_id)
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
        cur.execute("BEGIN TRANSACTION")

        cur.execute(
            "SELECT p.Paciente_ID, p.Usuario_ID, u.Rol_ID FROM paciente p JOIN usuarios u ON u.Usuario_ID = p.Usuario_ID WHERE p.Paciente_ID = ?",
            (paciente_id,)
        )
        paciente_row = cur.fetchone()
        if not paciente_row:
            cur.execute("ROLLBACK"); return _json_error('El paciente no existe.', 404)
        if paciente_row['Rol_ID'] != 3:
            cur.execute("ROLLBACK"); return _json_error('El usuario no tiene rol de paciente.', 403)

        usuario_id_paciente = paciente_row['Usuario_ID']

        cur.execute(
            "SELECT EstadoAgenda_ID, Fecha, Hora_Inicio, Especialista_ID FROM agenda WHERE Agenda_ID = ?",
            (agenda_id,)
        )
        slot = cur.fetchone()
        if not slot:
            cur.execute("ROLLBACK"); return _json_error('El slot de agenda no existe.', 404)
        if slot['EstadoAgenda_ID'] != 1:
            cur.execute("ROLLBACK"); return _json_error('Ese horario ya no está disponible.')

        cur.execute("SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?", (slot['Especialista_ID'],))
        if not cur.fetchone():
            cur.execute("ROLLBACK"); return _json_error('El especialista asociado al horario no existe.', 404)

        if not _validar_fecha_no_anterior(slot['Fecha']):
            cur.execute("ROLLBACK"); return _json_error('No se puede agendar con fecha anterior a la actual.')
        if not _validar_hora_minimo_tres_horas(slot['Hora_Inicio'], slot['Fecha']):
            cur.execute("ROLLBACK")
            return _json_error('Para citas del día de hoy, la hora debe ser al menos 3 horas posterior a la hora actual.')

        if _tiene_cita_activa_por_usuario(cur, usuario_id_paciente):
            cur.execute("ROLLBACK"); return _json_error('Ya tienes una cita activa en el sistema.', 409)

        cur.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta, Encuesta_Enviada) VALUES (?, ?, ?, 0)",
            (paciente_id, agenda_id, motivo)
        )
        cita_id = cur.lastrowid
        if not cita_id:
            cur.execute("ROLLBACK"); return _json_error('No se pudo registrar la cita.', 500)

        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 2 WHERE Agenda_ID = ?", (agenda_id,))
        if cur.rowcount == 0:
            cur.execute("ROLLBACK"); return _json_error('No se pudo actualizar la agenda.', 500)

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
# CITA INDIVIDUAL  —  GET /api/citas/<id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>', methods=['GET'])
def get_cita(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
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
# CANCELAR CITA (legado)  —  PUT /api/citas/<id>/cancelar
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
        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (row['Agenda_ID'],))
        cur.execute("INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,))
        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR SIN MULTA  —  PUT /api/citas/<id>/cancelar-sin-multa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-sin-multa', methods=['PUT'])
def cancelar_cita_sin_multa(cita_id):
    con = None
    try:
        con = get_db_connection()
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
            return _json_error('No se puede cancelar sin multa: faltan 2 horas o menos para la cita.', 409)
        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (row['Agenda_ID'],))
        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada sin penalización."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAR CON MULTA  —  PUT /api/citas/<id>/cancelar-con-multa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>/cancelar-con-multa', methods=['PUT'])
def cancelar_cita_con_multa(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Agenda_ID FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        cur.execute("UPDATE agenda SET EstadoAgenda_ID = 3 WHERE Agenda_ID = ?", (row['Agenda_ID'],))
        cur.execute("INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,))
        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR PACIENTE  —  GET /api/paciente/<id>/citas
# REQ 4: Incluye EstadoAgenda "Cumplida" y Encuesta_Enviada para que
# paciente.js pueda mostrar el botón de encuesta dinámicamente.
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/citas', methods=['GET'])
def get_citas_paciente(paciente_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   a.Fecha, a.Hora_Inicio,
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
            SELECT c.Cita_ID, c.Motivo_Consulta, c.Encuesta_Enviada,
                   a.Fecha, a.Hora_Inicio,
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
# MULTAS
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/multas', methods=['GET'])
def get_multas():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID, m.Cita_ID,
                   em.Nombre_Estado                  AS EstadoMulta,
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
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("UPDATE multa SET EstadoMulta_ID = 2 WHERE Multa_ID = ?", (multa_id,))
        if cur.rowcount == 0:
            return _json_error('Multa no encontrada.', 404)
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
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID FROM multa m
            JOIN cita c ON c.Cita_ID = m.Cita_ID
            WHERE c.Paciente_ID = ? AND m.EstadoMulta_ID = 1 LIMIT 1
        """, (paciente_id,))
        row = cur.fetchone()
        return _json_ok({"tiene_multa": row is not None})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# HISTORIAL CLÍNICO  —  POST /api/historial-clinico
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

        cur.execute("SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,))
        existing = cur.fetchone()
        if existing:
            historial_id = existing['Historial_ID']
        else:
            cur.execute("INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,))
            historial_id = cur.lastrowid

        if diagnostico:
            cur.execute("SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?", (diagnostico,))
            diag_row = cur.fetchone()
            if not diag_row:
                cur.execute("INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)", (diagnostico,))
                diagnostico_id = cur.lastrowid
            else:
                diagnostico_id = diag_row['Diagnostico_ID']
            cur.execute("""
                INSERT OR IGNORE INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)
            """, (historial_id, diagnostico_id))

        if tratamiento or evolucion:
            descripcion = (
                f"{evolucion}\n---\n{tratamiento}".strip()
                if (evolucion and tratamiento)
                else (evolucion or tratamiento)
            )
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
# REQ 5/6 — RANKING: REGISTRAR RESPUESTA  —  POST /api/respuesta
#
# crear_promedio() está integrada nativamente aquí:
# Cada vez que se inserta una respuesta, se recalcula el promedio acumulado
# del especialista a partir de TODAS sus respuestas en respuesta_ranking.
# La validación estricta garantiza valores enteros entre 1 y 5.
# ─────────────────────────────────────────────────────────────────────────────

def _crear_promedio(cur, especialista_id: int) -> float:
    """
    REQ 5 — Recalcula el promedio matemático acumulado del especialista
    basado en la totalidad de sus respuestas en respuesta_ranking.
    Retorna el nuevo promedio (0.0 si aún no hay respuestas).
    """
    cur.execute("""
        SELECT ROUND(AVG(CAST(rr.Respuesta AS REAL)), 2) AS Promedio,
               COUNT(rr.Respuesta_ID)                    AS Total
        FROM respuesta_ranking rr
        INNER JOIN cita   c  ON rr.Cita_ID       = c.Cita_ID
        INNER JOIN agenda ag ON c.Agenda_ID       = ag.Agenda_ID
        WHERE ag.Especialista_ID = ?
    """, (especialista_id,))
    row = cur.fetchone()
    return float(row['Promedio']) if row and row['Promedio'] is not None else 0.0


@citas_bp.route('/respuesta', methods=['POST'])
def crear_respuesta_ranking():
    """
    REQ 5/6 — Registra una respuesta de encuesta del paciente.
    Validación estricta: solo enteros 1-5.
    Tras insertar, recalcula el promedio del especialista (crear_promedio).
    REQ 9: Verifica kill-switch antes de persistir (la encuesta ya fue enviada
    por correo; aquí solo se guarda la calificación del paciente).
    """
    datos           = request.get_json(silent=True) or {}
    pregunta_id     = datos.get('ID_Pregunta')
    paciente_id     = datos.get('ID_Paciente')
    texto_respuesta = datos.get('Texto_Respuesta')
    cita_id         = datos.get('Cita_ID')

    if not all([pregunta_id, paciente_id, texto_respuesta]):
        return _json_error('ID_Pregunta, ID_Paciente y Texto_Respuesta son obligatorios.')

    # REQ 6 — Validación estricta: entero entre 1 y 5
    try:
        valor_int = int(texto_respuesta)
        if valor_int < 1 or valor_int > 5:
            return _json_error('Texto_Respuesta debe ser un número entero entre 1 y 5.')
    except (ValueError, TypeError):
        return _json_error(f'Texto_Respuesta debe ser un entero (1-5), recibido: {texto_respuesta!r}')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # REQ 9: Verificar kill-switch
        cur.execute("SELECT Estado_Envio FROM config_ranking LIMIT 1")
        cfg = cur.fetchone()
        if cfg and cfg['Estado_Envio'] == 0:
            return _json_error(
                'El sistema de evaluaciones está temporalmente desactivado.', 503
            )

        # Resolver Cita_ID
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
                return _json_error(f'No se encontró cita para el paciente {paciente_id}.', 404)
            cita_id_final = fila['Cita_ID']

        # Validar que la cita pertenece al paciente
        cur.execute("SELECT Paciente_ID FROM cita WHERE Cita_ID = ?", (cita_id_final,))
        cita_row = cur.fetchone()
        if not cita_row or str(cita_row['Paciente_ID']) != str(paciente_id):
            return _json_error('La cita no pertenece a este paciente.', 403)

        # Evitar respuesta duplicada
        cur.execute("""
            SELECT Respuesta_ID FROM respuesta_ranking
            WHERE Cita_ID = ? AND Preguntas_ID = ?
        """, (cita_id_final, pregunta_id))
        if cur.fetchone():
            return _json_error('Ya existe una respuesta para esta pregunta en esta cita.')

        # Verificar que la pregunta existe y está activa (REQ 7)
        cur.execute(
            "SELECT Preguntas_ID FROM preguntas_ranking WHERE Preguntas_ID = ? AND Activa = 1",
            (pregunta_id,)
        )
        if not cur.fetchone():
            return _json_error('La pregunta no existe o está inactiva.', 404)

        # Insertar respuesta
        cur.execute("""
            INSERT INTO respuesta_ranking (Cita_ID, Preguntas_ID, Respuesta)
            VALUES (?, ?, ?)
        """, (cita_id_final, pregunta_id, valor_int))
        respuesta_id = cur.lastrowid

        # Vincular con puntuacion_especialista
        cur.execute("""
            SELECT a.Especialista_ID
            FROM cita c JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Cita_ID = ?
        """, (cita_id_final,))
        esp_row = cur.fetchone()
        if esp_row:
            especialista_id = esp_row['Especialista_ID']
            cur.execute("""
                INSERT INTO puntuacion_especialista (Especialista_ID, Respuesta_ID)
                VALUES (?, ?)
            """, (especialista_id, respuesta_id))

            # REQ 5 — Recalcular promedio acumulado del especialista
            nuevo_promedio = _crear_promedio(cur, especialista_id)
            logger.info(
                "[RANKING] Especialista %d — nuevo promedio: %.2f", especialista_id, nuevo_promedio
            )

        con.commit()
        return _json_ok({"ok": True, "Respuesta_ID": respuesta_id}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR CONTRASEÑA  —  POST /api/verificar-password
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
        return _json_ok({"ok": row is not None})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZAR PERFIL PACIENTE  —  POST /api/actualizar-perfil-paciente
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

    if not usuario_id:
        return _json_error('usuario_id es obligatorio.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        campos  = []
        valores = []

        if nombres:          campos.append("Nombres = ?");         valores.append(nombres)
        if apellidos:        campos.append("Apellidos = ?");       valores.append(apellidos)
        if documento:        campos.append("NumeroDocumento = ?"); valores.append(documento)
        if tipo_documento_id: campos.append("TipoDoc_ID = ?");    valores.append(tipo_documento_id)
        if correo:           campos.append("Correo = ?");          valores.append(correo)
        if telefono:         campos.append("Telefono = ?");        valores.append(telefono)
        if nacimiento:       campos.append("FechaNacimiento = ?"); valores.append(nacimiento)
        if nueva_pass:
            ok, msg = _validar_politica_password(nueva_pass)
            if not ok:
                return _json_error(msg, 400)
            campos.append("Contrasena = ?"); valores.append(nueva_pass)

        if not campos and not any([eps_id, tipo_eps_id]):
            return _json_error('No hay campos para actualizar.')

        if campos:
            valores.append(usuario_id)
            cur.execute(f"UPDATE usuarios SET {', '.join(campos)} WHERE Usuario_ID = ?", tuple(valores))
            if cur.rowcount == 0:
                return _json_error('Usuario no encontrado.', 404)

        if eps_id or tipo_eps_id:
            cur.execute("SELECT Afiliacion_ID, EPS_ID, TipoEPS_ID FROM afiliacion WHERE Usuario_ID = ?", (usuario_id,))
            afil_row = cur.fetchone()
            eps_final      = int(eps_id)      if eps_id      else (afil_row['EPS_ID']     if afil_row else None)
            tipo_eps_final = int(tipo_eps_id) if tipo_eps_id else (afil_row['TipoEPS_ID'] if afil_row else None)

            if afil_row:
                cur.execute("""
                    UPDATE afiliacion SET EPS_ID = ?, TipoEPS_ID = ?, Fecha_Afiliacion = ?
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