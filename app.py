"""
app.py — Stylo Dental
Punto de entrada de Flask. Registra todos los blueprints y sirve las vistas HTML.
"""
 
from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
 
# Blueprints del historial
from modulo_historial.historial_clinico import historial_bp
from modulo_historial.tratamiento import tratamiento_bp
from modulo_historial.tabla_diagnostico import tabla_diag_bp
from modulo_historial.historial_diagnostico import historial_diag_bp
from modulo_historial.tabla_puntuacion_especialista import puntuacion_bp

# Blueprints de usuarios
from modulo_usuarios.routes import usuarios_bp
 
# Blueprint de citas
from modulo_citas.routes import citas_bp
 
# Blueprint de EPS (aseguramiento, afiliación, paciente)
from modulo_eps.routes import eps_bp
 
from db import get_db_connection
 
app = Flask(__name__)

# Necesaria para firmar la cookie de sesión (session).
# TODO: en producción, cargar esto desde una variable de entorno.
app.secret_key = "CAMBIA-ESTO-POR-UNA-CLAVE-LARGA-Y-ALEATORIA"

# supports_credentials=True permite que el navegador envíe/reciba la
# cookie de sesión en las peticiones fetch.
CORS(app, supports_credentials=True)
 
# =============================================================================
# REGISTRO DE BLUEPRINTS
# =============================================================================
 
app.register_blueprint(usuarios_bp,       url_prefix='/api')
app.register_blueprint(historial_bp,      url_prefix='/api')
app.register_blueprint(tratamiento_bp,    url_prefix='/api')
app.register_blueprint(tabla_diag_bp,     url_prefix='/api')
app.register_blueprint(historial_diag_bp, url_prefix='/api')
app.register_blueprint(puntuacion_bp,     url_prefix='/api')
app.register_blueprint(citas_bp,          url_prefix='/api')
app.register_blueprint(eps_bp,            url_prefix='/api')
 
 
# =============================================================================
# ENDPOINT AUXILIAR — Obtener Paciente_ID por Usuario_ID
# =============================================================================
 
@app.route('/api/paciente/por-usuario/<int:usuario_id>', methods=['GET'])
def paciente_por_usuario(usuario_id):
    con = None
    try:
        con = get_db_connection()
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
# El Usuario_ID se lee de la sesión activa de Flask (no del cliente).
# =============================================================================

@app.route('/api/paciente/perfil', methods=['GET'])
def perfil_paciente():
    usuario_id = session.get('usuario_id')

    if not usuario_id:
        return jsonify({"ok": False, "error": "Sesión no iniciada"}), 401

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        # CORRECCIÓN: afiliacion no tiene Numero_Afiliado ni Estado;
        # se usan los campos reales: Afiliacion_ID y Fecha_Afiliacion.
        cur.execute(
            """
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.FechaNacimiento,
                td.Nombre_Tipo_Documento  AS TipoDocumento,
                e.Nombre_EPS              AS EPS,
                a.Afiliacion_ID           AS NumeroAfiliado,
                a.Fecha_Afiliacion        AS EstadoAfiliacion,
                tae.Nombre_Tipo           AS TipoAfiliacion
            FROM usuarios u
            LEFT JOIN tipo_documento     td  ON u.TipoDoc_ID  = td.TipoDoc_ID
            LEFT JOIN afiliacion         a   ON a.Usuario_ID  = u.Usuario_ID
            LEFT JOIN eps                e   ON a.EPS_ID      = e.EPS_ID
            LEFT JOIN tipo_afiliacion_eps tae ON a.TipoEPS_ID = tae.TipoEPS_ID
            WHERE u.Usuario_ID = ?
            """,
            (usuario_id,)
        )
        fila = cur.fetchone()

        if not fila:
            return jsonify({"ok": False, "error": "Paciente no encontrado"}), 404

        perfil = dict(fila)

        valores_por_defecto = {
            "Nombres":          "Paciente",
            "Apellidos":        "",
            "NumeroDocumento":  "No registrado",
            "Correo":           "No registrado",
            "Telefono":         "No registrado",
            "FechaNacimiento":  "",
            "TipoDocumento":    "No registrado",
            "EPS":              "Sin afiliación",
            "NumeroAfiliado":   "No registrado",
            "EstadoAfiliacion": "Sin fecha",
            "TipoAfiliacion":   "No registrado",
        }
        for campo, defecto in valores_por_defecto.items():
            if perfil.get(campo) in (None, ""):
                perfil[campo] = defecto

        nombre_completo = f"{perfil['Nombres']} {perfil['Apellidos']}".strip()
        iniciales = (
            perfil['Nombres'][:1] + (perfil['Apellidos'][:1] if perfil['Apellidos'] else "")
        ).upper() or "PA"

        perfil["NombreCompleto"] = nombre_completo
        perfil["Iniciales"]      = iniciales

        return jsonify({"ok": True, "perfil": perfil}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con:
            con.close()


# =============================================================================
# CONFIGURACIÓN SMTP
# =============================================================================
 
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "andresparragiovanny1926@gmail.com"
SMTP_PASSWORD = "scca hjdy tswq dnjw"
SMTP_FROM     = "Clínica <andresparragiovanny1926@gmail.com>"
 
codigos_temporales = {}   # { correo: codigo }
 
 
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
def vista_historia_clinica():
    return render_template('historia_clinica.html')
 
@app.route('/ranking.html')
def vista_ranking():
    return render_template('ranking.html')
 
@app.route('/aseguramiento.html')
def vista_aseguramiento():
    return render_template('aseguramiento.html')
 
 
# =============================================================================
# API — ENVÍO DE CÓDIGO DE VERIFICACIÓN AL CORREO
# =============================================================================
 
@app.route('/api/enviar-codigo', methods=['POST'])
def enviar_codigo():
    datos  = request.get_json()
    correo = datos.get('correo', '').strip().lower()
    nombre = datos.get('nombre', 'Usuario')
 
    if not correo:
        return jsonify({"ok": False, "error": "Correo requerido"}), 400
 
    codigo = str(random.randint(100000, 999999))
    codigos_temporales[correo] = codigo
 
    cuerpo_html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:480px;margin:auto;
                border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#0369a1,#0ea5e9);
                    padding:24px;text-align:center;">
            <h2 style="color:white;margin:0;font-size:20px;">Verificación de cuenta</h2>
        </div>
        <div style="padding:28px 32px;">
            <p style="color:#475569;font-size:15px;margin-top:0;">
                Hola, <strong>{nombre}</strong>. Usa el siguiente código para
                completar tu registro. Expira en <strong>10 minutos</strong>.
            </p>
            <div style="background:#f0f9ff;border:2px dashed #7dd3fc;border-radius:10px;
                        text-align:center;padding:18px;margin:24px 0;
                        font-size:34px;font-weight:800;letter-spacing:10px;
                        color:#0284c7;font-family:'Courier New',monospace;">
                {codigo}
            </div>
            <p style="color:#94a3b8;font-size:12px;text-align:center;margin-bottom:0;">
                Si no solicitaste este código, ignora este mensaje.
            </p>
        </div>
    </div>
    """
 
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Tu código de verificación - Stylo Dental"
        msg['From']    = SMTP_FROM
        msg['To']      = correo
        msg.attach(MIMEText(cuerpo_html, 'html'))
 
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.sendmail(SMTP_USER, correo, msg.as_string())
 
        return jsonify({"ok": True}), 200
 
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
 
 
# =============================================================================
# API — VERIFICACIÓN DEL CÓDIGO
# =============================================================================
 
@app.route('/api/verificar-codigo', methods=['POST'])
def verificar_codigo():
    datos     = request.get_json()
    correo    = datos.get('correo', '').strip().lower()
    ingresado = str(datos.get('codigo', '')).strip()
    esperado  = codigos_temporales.get(correo)
 
    if not esperado:
        return jsonify({"ok": False, "error": "No hay código generado para este correo"}), 400
    if ingresado == esperado:
        del codigos_temporales[correo]
        return jsonify({"ok": True}), 200
    return jsonify({"ok": False, "error": "Código incorrecto"}), 400


# =============================================================================
# API — SOLICITAR CÓDIGO RECUPERACIÓN DE CONTRASEÑA
# =============================================================================

@app.route('/api/auth/solicitar-codigo', methods=['POST'])
def solicitar_codigo_recuperacion():
    datos  = request.get_json(silent=True) or {}
    correo = (datos.get('correo') or '').strip().lower()

    if not correo:
        return jsonify({"ok": False, "error": "Correo requerido"}), 400

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT 1 FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        if not cur.fetchone():
            return jsonify({"ok": False, "error": "No existe una cuenta con ese correo."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()

    codigo = str(random.randint(100000, 999999))
    codigos_temporales[correo] = codigo

    cuerpo_html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:480px;margin:auto;
                border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#0369a1,#0ea5e9);
                    padding:24px;text-align:center;">
            <h2 style="color:white;margin:0;font-size:20px;">Recuperación de contraseña</h2>
        </div>
        <div style="padding:28px 32px;">
            <p style="color:#475569;font-size:15px;margin-top:0;">
                Usa el siguiente código para restablecer tu contraseña.
                Expira en <strong>10 minutos</strong>.
            </p>
            <div style="background:#f0f9ff;border:2px dashed #7dd3fc;border-radius:10px;
                        text-align:center;padding:18px;margin:24px 0;
                        font-size:34px;font-weight:800;letter-spacing:10px;
                        color:#0284c7;font-family:'Courier New',monospace;">
                {codigo}
            </div>
            <p style="color:#94a3b8;font-size:12px;text-align:center;margin-bottom:0;">
                Si no solicitaste este código, ignora este mensaje.
            </p>
        </div>
    </div>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Código de recuperación - Stylo Dental"
        msg['From']    = SMTP_FROM
        msg['To']      = correo
        msg.attach(MIMEText(cuerpo_html, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.sendmail(SMTP_USER, correo, msg.as_string())

        return jsonify({"ok": True}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================================
# API — VERIFICAR CÓDIGO RECUPERACIÓN DE CONTRASEÑA
# =============================================================================

@app.route('/api/auth/verificar-codigo', methods=['POST'])
def verificar_codigo_recuperacion():
    datos     = request.get_json(silent=True) or {}
    correo    = (datos.get('correo') or '').strip().lower()
    ingresado = str(datos.get('codigo') or '').strip()
    esperado  = codigos_temporales.get(correo)

    if not esperado:
        return jsonify({"ok": False, "error": "No hay código generado para este correo."}), 400
    if ingresado != esperado:
        return jsonify({"ok": False, "error": "Código incorrecto."}), 400

    # No se elimina aquí; se elimina al cambiar la contraseña
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
    nueva_contrasena = datos.get('nueva_contrasena') or ''

    if not correo or not nueva_contrasena:
        return jsonify({"ok": False, "error": "Correo y nueva contraseña son requeridos."}), 400

    errores_politica = []
    if len(nueva_contrasena) < 8:
        errores_politica.append("Mínimo 8 caracteres.")
    if not re.search(r'[A-Z]', nueva_contrasena):
        errores_politica.append("Al menos una letra mayúscula.")
    if not re.search(r'[a-z]', nueva_contrasena):
        errores_politica.append("Al menos una letra minúscula.")
    if not re.search(r'[0-9]', nueva_contrasena):
        errores_politica.append("Al menos un número.")
    if not re.search(r'[^A-Za-z0-9]', nueva_contrasena):
        errores_politica.append("Al menos un carácter especial.")
    if errores_politica:
        return jsonify({"ok": False, "error": " ".join(errores_politica)}), 400

    if correo not in codigos_temporales:
        return jsonify({"ok": False, "error": "Sesión de recuperación no válida o expirada."}), 400

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT Usuario_ID FROM usuarios WHERE LOWER(Correo) = ?", (correo,))
        fila = cur.fetchone()
        if not fila:
            return jsonify({"ok": False, "error": "No existe una cuenta con ese correo."}), 404

        hash_nueva = generate_password_hash(nueva_contrasena)

        cur.execute(
            "UPDATE usuarios SET Contrasena = ? WHERE LOWER(Correo) = ?",
            (hash_nueva, correo)
        )
        con.commit()

        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "No se pudo actualizar la contraseña."}), 500

        codigos_temporales.pop(correo, None)

        return jsonify({"ok": True}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if con: con.close()
 
 
# =============================================================================
# INICIO
# =============================================================================
 
if __name__ == '__main__':
    app.run(debug=True, port=3000)