"""
app.py — Stylo Dental
Punto de entrada de Flask. Registra todos los blueprints y sirve las vistas HTML.
"""

from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS

import os
import random
import time
import logging
import smtplib
import ssl
import socket
import sqlite3
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

# ── CORRECCIÓN CRÍTICA ────────────────────────────────────────────────────────
# ANTES (incorrecto):
#   from modulo_historial.historial_clinico import historial_bp
#   → Importaba el blueprint LEGACY que NO tiene vista_historia_clinica().
#   → La ruta GET /historial/paciente/<id> nunca se registraba en Flask.
#   → Al navegar a esa URL, Flask resolvía otro endpoint que devolvía JSON crudo.
#
# AHORA (correcto):
#   from modulo_historial.routes import historial_bp
#   → Importa el blueprint DEFINITIVO con:
#       • GET  /historial/paciente/<id>              → render_template (VISTA HTML)
#       • GET  /api/historial/paciente/<id>/info     → jsonify (API)
#       • GET  /api/historial/paciente/<id>/evoluciones → jsonify (API)
#       • POST /api/historial/guardar                → jsonify (API)
#       • POST /api/historial/finalizar              → jsonify (API)
# ─────────────────────────────────────────────────────────────────────────────
from modulo_historial.routes                        import historial_bp

# Los demás submódulos de historial siguen importándose igual
from modulo_historial.tratamiento                   import tratamiento_bp
from modulo_historial.tabla_diagnostico             import tabla_diag_bp
from modulo_historial.historial_diagnostico         import historial_diag_bp
from modulo_historial.tabla_puntuacion_especialista import puntuacion_bp

from modulo_usuarios.routes import usuarios_bp
from modulo_citas.routes    import citas_bp
from modulo_eps.routes      import eps_bp

from db import get_db_connection

# ─── Ruta absoluta a odent.db ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'odent.db')


def _app_conn():
    """Conexión directa con ruta absoluta garantizada."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stylo_dental_smtp")

# =============================================================================
# APLICACIÓN FLASK
# =============================================================================
app = Flask(__name__)
app.secret_key = "CAMBIA-ESTO-POR-UNA-CLAVE-LARGA-Y-ALEATORIA"
CORS(app, supports_credentials=True)

# =============================================================================
# REGISTRO DE BLUEPRINTS
# =============================================================================
app.register_blueprint(usuarios_bp,       url_prefix='/api')

# ── historial_bp se registra SIN url_prefix ──────────────────────────────────
# Sus rutas de VISTA  (/historial/paciente/<id>)       no llevan prefijo.
# Sus rutas de API    (/api/historial/paciente/<id>/…) llevan /api embebido
# en cada decorador @historial_bp.route, por lo que no necesitan url_prefix.
# Esto evita la colisión con citas_bp que sí usa url_prefix='/api'.
app.register_blueprint(historial_bp)

app.register_blueprint(tratamiento_bp,    url_prefix='/api')
app.register_blueprint(tabla_diag_bp,     url_prefix='/api')
app.register_blueprint(historial_diag_bp, url_prefix='/api')
app.register_blueprint(puntuacion_bp,     url_prefix='/api')
app.register_blueprint(citas_bp,          url_prefix='/api')
app.register_blueprint(eps_bp,            url_prefix='/api')


# =============================================================================
# CONFIGURACIÓN SMTP
# =============================================================================
SMTP_HOST         = "smtp.gmail.com"
SMTP_PORT         = 465
SMTP_USER         = "andresparragiovanny1926@gmail.com"
SMTP_APP_PASSWORD = "sccahjdytswqdnjw"
SMTP_FROM_NAME    = "Clínica Stylo Dental"
SMTP_FROM         = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
SMTP_TIMEOUT      = 20

# =============================================================================
# ALMACÉN DE CÓDIGOS TEMPORALES
# =============================================================================
_codigos_lock      = threading.Lock()
codigos_temporales = {}
CODIGO_EXPIRACION_S = 600

_smtp_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="smtp")


# =============================================================================
# PLANTILLAS HTML DE CORREO
# =============================================================================

def _html_verificacion(nombre: str, codigo: str) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:500px;margin:auto;
                border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#0369a1,#0ea5e9);
                  padding:28px 32px;text-align:center;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;">🦷 Stylo Dental</h1>
        <p style="color:#bae6fd;margin:6px 0 0;font-size:14px;">Verificación de cuenta</p>
      </div>
      <div style="padding:32px;background:#ffffff;">
        <p style="color:#334155;font-size:15px;margin-top:0;">
          Hola, <strong>{nombre}</strong>.<br>
          Usa el siguiente código. Expirará en <strong>10 minutos</strong>.
        </p>
        <div style="background:#f0f9ff;border:2px dashed #38bdf8;border-radius:10px;
                    text-align:center;padding:20px 16px;margin:28px 0;">
          <span style="font-family:'Courier New',monospace;font-size:40px;
                       font-weight:800;letter-spacing:12px;color:#0284c7;">{codigo}</span>
        </div>
        <p style="color:#64748b;font-size:13px;margin-bottom:0;">
          Si no solicitaste este código, puedes ignorar este mensaje.
        </p>
      </div>
      <div style="background:#f8fafc;padding:16px 32px;text-align:center;border-top:1px solid #e2e8f0;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">© 2025 Clínica Stylo Dental</p>
      </div>
    </div>
    """


def _html_recuperacion(codigo: str) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:500px;margin:auto;
                border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#7c3aed,#a78bfa);
                  padding:28px 32px;text-align:center;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;">🦷 Stylo Dental</h1>
        <p style="color:#ede9fe;margin:6px 0 0;font-size:14px;">Recuperación de contraseña</p>
      </div>
      <div style="padding:32px;background:#ffffff;">
        <p style="color:#334155;font-size:15px;margin-top:0;">
          Ingresa el siguiente código. Expirará en <strong>10 minutos</strong>.
        </p>
        <div style="background:#faf5ff;border:2px dashed #a78bfa;border-radius:10px;
                    text-align:center;padding:20px 16px;margin:28px 0;">
          <span style="font-family:'Courier New',monospace;font-size:40px;
                       font-weight:800;letter-spacing:12px;color:#7c3aed;">{codigo}</span>
        </div>
        <p style="color:#64748b;font-size:13px;margin-bottom:0;">
          Si no solicitaste esto, ignora este mensaje.
        </p>
      </div>
      <div style="background:#f8fafc;padding:16px 32px;text-align:center;border-top:1px solid #e2e8f0;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">© 2025 Clínica Stylo Dental</p>
      </div>
    </div>
    """


# =============================================================================
# FUNCIÓN CENTRALIZADA DE ENVÍO SMTP
# =============================================================================

def _enviar_correo_smtp(destinatario: str, asunto: str, cuerpo_html: str):
    try:
        import re as _re
        texto_plano = _re.sub(r'<[^>]+>', '', cuerpo_html)
        texto_plano = _re.sub(r'\s{2,}', ' ', texto_plano).strip()

        msg = MIMEMultipart('alternative')
        msg['From']              = SMTP_FROM
        msg['Reply-To']          = SMTP_FROM
        msg['To']                = destinatario
        msg['Subject']           = asunto
        msg['Date']              = formatdate(localtime=True)
        msg['Message-ID']        = make_msgid(domain="gmail.com")
        msg['Importance']        = 'high'
        msg['X-Priority']        = '1'
        msg['X-MSMail-Priority'] = 'High'
        msg['X-Mailer']          = 'StyloDental-Transactional/1.0'

        msg.attach(MIMEText(texto_plano, 'plain', 'utf-8'))
        msg.attach(MIMEText(cuerpo_html, 'html',  'utf-8'))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT, context=ctx) as srv:
            srv.ehlo("gmail.com")
            srv.login(SMTP_USER, SMTP_APP_PASSWORD)
            rechazados = srv.sendmail(SMTP_USER, destinatario, msg.as_string())
            if rechazados:
                return False, f"Dirección rechazada: {rechazados}"

        logger.info("[SMTP] ✓ Correo entregado a %s", destinatario)
        return True, None

    except smtplib.SMTPAuthenticationError as exc:
        return False, "Credenciales SMTP rechazadas."
    except (smtplib.SMTPConnectError, socket.timeout, socket.gaierror, ssl.SSLError) as exc:
        return False, "No se pudo conectar al servidor SMTP."
    except smtplib.SMTPRecipientsRefused as exc:
        return False, "El servidor rechazó la dirección del destinatario."
    except Exception as exc:
        logger.error("[SMTP] Error: %s\n%s", exc, traceback.format_exc())
        return False, f"Error inesperado: {exc}"


enviar_correo_smtp = _enviar_correo_smtp


# =============================================================================
# HELPERS INTERNOS
# =============================================================================

def _guardar_codigo(correo: str, codigo: str) -> None:
    with _codigos_lock:
        codigos_temporales[correo] = {
            "codigo": codigo,
            "expira": time.time() + CODIGO_EXPIRACION_S,
        }


def _validar_codigo(correo: str, ingresado: str) -> tuple:
    with _codigos_lock:
        registro = codigos_temporales.get(correo)
        if not registro:
            return False, "No hay código generado para este correo."
        if time.time() > registro["expira"]:
            codigos_temporales.pop(correo, None)
            return False, "El código ha expirado. Solicita uno nuevo."
        if ingresado != registro["codigo"]:
            return False, "Código incorrecto."
        codigos_temporales.pop(correo, None)
        return True, None


def _nuevo_codigo() -> str:
    return str(random.randint(100000, 999999))


# =============================================================================
# ENDPOINT AUXILIAR — Paciente por Usuario_ID
# =============================================================================

@app.route('/api/paciente/por-usuario/<int:usuario_id>', methods=['GET'])
def paciente_por_usuario(usuario_id):
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT Paciente_ID FROM paciente WHERE Usuario_ID = ?", (usuario_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "No existe paciente para ese usuario"}), 404
        return jsonify({"Paciente_ID": row["Paciente_ID"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if con: con.close()


# =============================================================================
# ENDPOINT — Perfil completo del paciente autenticado
# =============================================================================

@app.route('/api/paciente/perfil', methods=['GET'])
def perfil_paciente():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({"ok": False, "error": "Sesión no iniciada"}), 401

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT
                u.Usuario_ID, u.Nombres, u.Apellidos, u.NumeroDocumento,
                u.Correo, u.Telefono, u.FechaNacimiento,
                td.Nombre_Tipo_Documento  AS TipoDocumento,
                e.Nombre_EPS              AS EPS,
                a.Afiliacion_ID           AS NumeroAfiliado,
                a.Fecha_Afiliacion        AS EstadoAfiliacion,
                tae.Nombre_Tipo           AS TipoAfiliacion
            FROM usuarios u
            LEFT JOIN tipo_documento      td  ON u.TipoDoc_ID  = td.TipoDoc_ID
            LEFT JOIN afiliacion          a   ON a.Usuario_ID  = u.Usuario_ID
            LEFT JOIN eps                 e   ON a.EPS_ID      = e.EPS_ID
            LEFT JOIN tipo_afiliacion_eps tae ON a.TipoEPS_ID  = tae.TipoEPS_ID
            WHERE u.Usuario_ID = ?
        """, (usuario_id,))
        fila = cur.fetchone()
        if not fila:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404

        perfil = dict(fila)
        defaults = {
            "Nombres": "Paciente", "Apellidos": "", "NumeroDocumento": "No registrado",
            "Correo": "No registrado", "Telefono": "No registrado", "FechaNacimiento": "",
            "TipoDocumento": "No registrado", "EPS": "Sin afiliación",
            "NumeroAfiliado": "No registrado", "EstadoAfiliacion": "Sin fecha",
            "TipoAfiliacion": "No registrado",
        }
        for campo, defecto in defaults.items():
            if perfil.get(campo) in (None, ""):
                perfil[campo] = defecto

        perfil["NombreCompleto"] = f"{perfil['Nombres']} {perfil['Apellidos']}".strip()
        perfil["Iniciales"] = (
            perfil['Nombres'][:1] + (perfil['Apellidos'][:1] if perfil['Apellidos'] else "")
        ).upper() or "PA"

        return jsonify({"ok": True, "perfil": perfil}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()


# =============================================================================
# VISTAS HTML
# =============================================================================

@app.route('/')
@app.route('/login')
@app.route('/login.html')
def vista_login():
    return render_template('login.html')

@app.route('/vista/crear_usuario')
@app.route('/creacion.html')
def vista_creacion_usuario():
    return render_template('creacion.html')

@app.route('/administrador.html')
def vista_administrador():
    return render_template('administrador.html')

@app.route('/especialista')
@app.route('/especialista.html')
def vista_especialista():
    return render_template('especialista.html')

@app.route('/paciente.html')
def vista_paciente():
    return render_template('paciente.html')

@app.route('/agendar')
@app.route('/agendar.html')
def vista_agendar():
    return render_template('agendar.html')

@app.route('/historia_clinica.html')
def vista_historia_clinica_legacy():
    """Ruta legacy — sirve el template con parámetros vacíos para compatibilidad."""
    return render_template('historia_clinica.html', paciente_id=0, cita_id='')

@app.route('/ranking.html')
def vista_ranking():
    return render_template('ranking.html')

@app.route('/aseguramiento.html')
def vista_aseguramiento():
    return render_template('aseguramiento.html')


# =============================================================================
# API — ENVÍO DE CÓDIGO DE VERIFICACIÓN (registro)
# =============================================================================

@app.route('/api/enviar-codigo', methods=['POST'])
def enviar_codigo():
    datos  = request.get_json(silent=True) or {}
    correo = (datos.get('correo') or '').strip().lower()
    nombre = (datos.get('nombre') or 'Usuario').strip() or 'Usuario'

    if not correo:
        return jsonify({"ok": False, "error": "Correo requerido"}), 400

    codigo = _nuevo_codigo()
    _guardar_codigo(correo, codigo)

    ok, error = _enviar_correo_smtp(
        correo,
        "Tu código de verificación – Stylo Dental",
        _html_verificacion(nombre, codigo),
    )

    if not ok:
        with _codigos_lock:
            codigos_temporales.pop(correo, None)
        return jsonify({"ok": False, "error": error}), 500

    return jsonify({"ok": True}), 200


# =============================================================================
# API — VERIFICAR CÓDIGO DE REGISTRO
# =============================================================================

@app.route('/api/verificar-codigo', methods=['POST'])
def verificar_codigo():
    datos     = request.get_json(silent=True) or {}
    correo    = (datos.get('correo') or '').strip().lower()
    ingresado = str(datos.get('codigo') or '').strip()

    if not correo or not ingresado:
        return jsonify({"ok": False, "error": "Correo y código son requeridos"}), 400

    ok, error = _validar_codigo(correo, ingresado)
    if not ok:
        return jsonify({"ok": False, "error": error}), 400

    return jsonify({"ok": True}), 200


# =============================================================================
# API — SOLICITAR CÓDIGO DE RECUPERACIÓN
# =============================================================================

@app.route('/api/auth/solicitar-codigo', methods=['POST'])
def solicitar_codigo_recuperacion():
    datos  = request.get_json(silent=True) or {}
    correo = (datos.get('correo') or '').strip().lower()

    if not correo:
        return jsonify({"ok": False, "error": "Correo requerido"}), 400

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("SELECT 1 FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        if not cur.fetchone():
            return jsonify({"ok": False, "error": "No existe una cuenta con ese correo."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()

    codigo = _nuevo_codigo()
    _guardar_codigo(correo, codigo)

    ok, error = _enviar_correo_smtp(
        correo,
        "Código de recuperación de contraseña – Stylo Dental",
        _html_recuperacion(codigo),
    )

    if not ok:
        with _codigos_lock:
            codigos_temporales.pop(correo, None)
        return jsonify({"ok": False, "error": error}), 500

    return jsonify({"ok": True}), 200


# =============================================================================
# API — VERIFICAR CÓDIGO DE RECUPERACIÓN
# =============================================================================

@app.route('/api/auth/verificar-codigo', methods=['POST'])
def verificar_codigo_recuperacion():
    datos     = request.get_json(silent=True) or {}
    correo    = (datos.get('correo') or '').strip().lower()
    ingresado = str(datos.get('codigo') or '').strip()

    if not correo or not ingresado:
        return jsonify({"ok": False, "error": "Correo y código son requeridos."}), 400

    with _codigos_lock:
        registro = codigos_temporales.get(correo)
        if not registro:
            return jsonify({"ok": False, "error": "No hay código generado para este correo."}), 400
        if time.time() > registro["expira"]:
            codigos_temporales.pop(correo, None)
            return jsonify({"ok": False, "error": "El código ha expirado."}), 400
        if ingresado != registro["codigo"]:
            return jsonify({"ok": False, "error": "Código incorrecto."}), 400

    return jsonify({"ok": True}), 200


# =============================================================================
# API — CAMBIAR CONTRASEÑA (recuperación)
# =============================================================================

@app.route('/api/auth/cambiar-password', methods=['POST'])
def cambiar_password():
    from werkzeug.security import generate_password_hash
    import re

    datos            = request.get_json(silent=True) or {}
    correo           = (datos.get('correo') or '').strip().lower()
    codigo           = str(datos.get('codigo') or '').strip()
    nueva_contrasena = datos.get('nueva_contrasena') or ''

    if not correo or not nueva_contrasena:
        return jsonify({"ok": False, "error": "Correo y nueva contraseña son requeridos."}), 400

    errores = []
    if len(nueva_contrasena) < 8:                         errores.append("Mínimo 8 caracteres.")
    if not re.search(r'[A-Z]', nueva_contrasena):         errores.append("Al menos una mayúscula.")
    if not re.search(r'[a-z]', nueva_contrasena):         errores.append("Al menos una minúscula.")
    if not re.search(r'[0-9]', nueva_contrasena):         errores.append("Al menos un número.")
    if not re.search(r'[^A-Za-z0-9]', nueva_contrasena): errores.append("Al menos un carácter especial.")
    if errores:
        return jsonify({"ok": False, "error": " ".join(errores)}), 400

    if codigo:
        ok_cod, err_cod = _validar_codigo(correo, codigo)
        if not ok_cod:
            return jsonify({"ok": False, "error": err_cod}), 400
    else:
        with _codigos_lock:
            if correo not in codigos_temporales:
                return jsonify({"ok": False, "error": "Sesión de recuperación no válida o expirada."}), 400
        with _codigos_lock:
            codigos_temporales.pop(correo, None)

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("SELECT Usuario_ID FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        if not cur.fetchone():
            return jsonify({"ok": False, "error": "No existe una cuenta con ese correo."}), 404
        cur.execute(
            "UPDATE usuarios SET Contrasena = ? WHERE LOWER(Correo) = ?",
            (generate_password_hash(nueva_contrasena), correo)
        )
        con.commit()
        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "No se pudo actualizar la contraseña."}), 500
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()


# =============================================================================
# API — DIAGNÓSTICO SMTP
# =============================================================================

@app.route('/api/test-smtp', methods=['POST'])
def test_smtp():
    datos  = request.get_json(silent=True) or {}
    correo = (datos.get('correo') or '').strip().lower()

    if not correo:
        return jsonify({"ok": False, "error": "Correo requerido"}), 400

    ok, error = _enviar_correo_smtp(
        correo,
        "Prueba de diagnóstico SMTP – Stylo Dental",
        "<p style='font-family:sans-serif'>Configuración SMTP funciona correctamente. ✅</p>",
    )

    if not ok:
        return jsonify({"ok": False, "error": error}), 500
    return jsonify({"ok": True, "mensaje": "Correo de prueba enviado correctamente."}), 200


# =============================================================================
# RUTAS DEL MÓDULO DE ASEGURAMIENTO DE DATOS
# =============================================================================

@app.route('/api/usuario/<int:usuario_id>', methods=['GET'])
def aseg_get_usuario_por_id(usuario_id):
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
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
                u.Rol_ID
            FROM usuarios u
            LEFT JOIN tipo_documento td ON td.TipoDoc_ID = u.TipoDoc_ID
            WHERE u.Usuario_ID = ?
        """, (usuario_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
        return jsonify({"ok": True, "data": dict(row)}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/usuario/documento/<string:numero_documento>', methods=['GET'])
def aseg_get_usuario_por_documento(numero_documento):
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT
                u.Usuario_ID, u.Nombres, u.Apellidos,
                u.TipoDoc_ID, u.NumeroDocumento,
                u.Correo, u.Telefono, u.Rol_ID
            FROM usuarios u
            WHERE u.NumeroDocumento = ?
        """, (numero_documento.strip(),))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
        return jsonify({"ok": True, "data": dict(row)}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/usuario/<int:usuario_id>', methods=['PUT'])
def aseg_actualizar_usuario(usuario_id):
    datos = request.get_json(silent=True) or {}

    campos  = []
    valores = []

    mapeo = {
        "Nombres":         datos.get("Nombres"),
        "Apellidos":       datos.get("Apellidos"),
        "TipoDoc_ID":      datos.get("TipoDoc_ID"),
        "NumeroDocumento": datos.get("NumeroDocumento"),
        "Telefono":        datos.get("Telefono"),
        "Correo":          datos.get("Correo"),
        "Estado_ID":       datos.get("Estado_ID"),
    }

    for col, val in mapeo.items():
        if val is not None and str(val).strip() != "":
            campos.append(f"{col} = ?")
            valores.append(val)

    if not campos:
        return jsonify({"ok": False, "error": "No se recibieron campos para actualizar."}), 400

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()

        correo_nuevo = datos.get("Correo")
        if correo_nuevo:
            cur.execute(
                "SELECT Usuario_ID FROM usuarios WHERE LOWER(Correo) = LOWER(?) AND Usuario_ID != ?",
                (correo_nuevo.strip(), usuario_id)
            )
            if cur.fetchone():
                return jsonify({"ok": False, "error": "El correo ya está en uso."}), 409

        doc_nuevo = datos.get("NumeroDocumento")
        if doc_nuevo:
            cur.execute(
                "SELECT Usuario_ID FROM usuarios WHERE NumeroDocumento = ? AND Usuario_ID != ?",
                (doc_nuevo.strip(), usuario_id)
            )
            if cur.fetchone():
                return jsonify({"ok": False, "error": "El número de documento ya está en uso."}), 409

        valores.append(usuario_id)
        cur.execute(
            f"UPDATE usuarios SET {', '.join(campos)} WHERE Usuario_ID = ?",
            tuple(valores)
        )
        con.commit()

        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404

        return jsonify({"ok": True, "mensaje": "Datos actualizados."}), 200

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/afiliacion/por-usuario/<int:usuario_id>', methods=['GET'])
def aseg_get_afiliacion_por_usuario(usuario_id):
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT a.Afiliacion_ID, a.EPS_ID, a.TipoEPS_ID,
                   a.Fecha_Afiliacion, e.Regimen_ID
            FROM afiliacion a
            LEFT JOIN eps e ON e.EPS_ID = a.EPS_ID
            WHERE a.Usuario_ID = ?
            ORDER BY a.Afiliacion_ID DESC
            LIMIT 1
        """, (usuario_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Sin afiliación registrada."}), 404
        return jsonify({"ok": True, "data": dict(row)}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/especialista/por-usuario/<int:usuario_id>', methods=['GET'])
def aseg_get_especialista_por_usuario(usuario_id):
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT esp.Especialista_ID, esp.Tarjeta_Profesional, ee.Especialidad_ID
            FROM especialista esp
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = esp.Especialista_ID
            WHERE esp.Usuario_ID = ?
            ORDER BY ee.Especialidad_ID ASC
            LIMIT 1
        """, (usuario_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Sin datos de especialista."}), 404
        return jsonify({"ok": True, "data": dict(row)}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/especialista', methods=['POST'])
def aseg_crear_especialista():
    datos           = request.get_json(silent=True) or {}
    usuario_id      = datos.get("Usuario_ID")
    tarjeta         = (datos.get("Tarjeta_Profesional") or "").strip()
    especialidad_id = datos.get("Especialidad_ID")

    if not usuario_id:
        return jsonify({"ok": False, "error": "Usuario_ID es requerido."}), 400
    if not tarjeta:
        return jsonify({"ok": False, "error": "Tarjeta_Profesional es requerida."}), 400

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()

        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Usuario_ID = ?", (usuario_id,)
        )
        existente = cur.fetchone()

        if existente:
            esp_id = existente["Especialista_ID"]
            cur.execute(
                "UPDATE especialista SET Tarjeta_Profesional = ? WHERE Especialista_ID = ?",
                (tarjeta, esp_id)
            )
        else:
            cur.execute("SELECT 1 FROM especialista WHERE Tarjeta_Profesional = ?", (tarjeta,))
            if cur.fetchone():
                return jsonify({"ok": False, "error": "La tarjeta profesional ya está registrada."}), 409
            cur.execute(
                "INSERT INTO especialista (Usuario_ID, Tarjeta_Profesional) VALUES (?, ?)",
                (usuario_id, tarjeta)
            )
            esp_id = cur.lastrowid

        if especialidad_id:
            cur.execute(
                "SELECT 1 FROM especialista_especialidad WHERE Especialista_ID = ?", (esp_id,)
            )
            if cur.fetchone():
                cur.execute(
                    "UPDATE especialista_especialidad SET Especialidad_ID = ? WHERE Especialista_ID = ?",
                    (int(especialidad_id), esp_id)
                )
            else:
                cur.execute(
                    "INSERT INTO especialista_especialidad (Especialista_ID, Especialidad_ID) VALUES (?, ?)",
                    (esp_id, int(especialidad_id))
                )

        con.commit()
        return jsonify({"ok": True, "data": {"Especialista_ID": esp_id}}), 201

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    finally:
        if con: con.close()


@app.route('/api/especialista/<int:especialista_id>', methods=['PUT'])
def aseg_actualizar_especialista(especialista_id):
    datos           = request.get_json(silent=True) or {}
    tarjeta         = (datos.get("Tarjeta_Profesional") or "").strip()
    especialidad_id = datos.get("Especialidad_ID")

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()

        cur.execute(
            "SELECT Especialista_ID FROM especialista WHERE Especialista_ID = ?",
            (especialista_id,)
        )
        if not cur.fetchone():
            return jsonify({"ok": False, "error": "Especialista no encontrado."}), 404

        if tarjeta:
            cur.execute(
                "SELECT 1 FROM especialista WHERE Tarjeta_Profesional = ? AND Especialista_ID != ?",
                (tarjeta, especialista_id)
            )
            if cur.fetchone():
                return jsonify({"ok": False, "error": "La tarjeta profesional ya está en uso."}), 409
            cur.execute(
                "UPDATE especialista SET Tarjeta_Profesional = ? WHERE Especialista_ID = ?",
                (tarjeta, especialista_id)
            )

        if especialidad_id:
            cur.execute(
                "SELECT 1 FROM especialista_especialidad WHERE Especialista_ID = ?",
                (especialista_id,)
            )
            if cur.fetchone():
                cur.execute(
                    "UPDATE especialista_especialidad SET Especialidad_ID = ? WHERE Especialista_ID = ?",
                    (int(especialidad_id), especialista_id)
                )
            else:
                cur.execute(
                    "INSERT INTO especialista_especialidad (Especialista_ID, Especialidad_ID) VALUES (?, ?)",
                    (especialista_id, int(especialidad_id))
                )

        con.commit()
        return jsonify({"ok": True, "data": {"Especialista_ID": especialista_id}}), 200

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    finally:
        if con: con.close()


@app.route('/api/especialidades', methods=['GET'])
def aseg_get_especialidades():
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT Especialidad_ID, Nombre_Especialidad FROM especialidad ORDER BY Nombre_Especialidad"
        )
        filas = cur.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/tipo-eps', methods=['GET'])
def aseg_get_tipo_eps():
    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute(
            "SELECT TipoEPS_ID, Nombre_Tipo FROM tipo_afiliacion_eps ORDER BY TipoEPS_ID"
        )
        filas = cur.fetchall()
        return jsonify({"ok": True, "data": [dict(f) for f in filas]}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


@app.route('/api/aseguramiento', methods=['POST'])
def aseg_registrar_aseguramiento():
    datos       = request.get_json(silent=True) or {}
    usuario_id  = datos.get("Usuario_ID")
    accion_id   = datos.get("Accion_ID")
    from datetime import date as _date
    fecha       = datos.get("Fecha") or _date.today().isoformat()
    descripcion = (datos.get("Descripcion") or "Aseguramiento de datos").strip()

    if not usuario_id or not accion_id:
        return jsonify({"ok": False, "error": "Usuario_ID y Accion_ID son requeridos."}), 400

    con = None
    try:
        con = _app_conn()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, ?, ?, ?)
        """, (usuario_id, accion_id, fecha, descripcion))
        con.commit()
        return jsonify({"ok": True, "data": {"AseguramientoID": cur.lastrowid}}), 201
    except Exception as exc:
        logger.warning("[aseguramiento] No se pudo registrar: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if con: con.close()


# =============================================================================
# INICIO
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=3000)