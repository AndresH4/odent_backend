from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from db import get_db_connection
from modulo_usuarios.routes import usuarios_bp

app = Flask(__name__)
CORS(app)

# usuarios_bp expone /api/usuarios, /api/roles y la nueva /api/auth/login
# (usada por login.js para autenticar)
app.register_blueprint(usuarios_bp, url_prefix='/api')

# =============================================================================
# CONFIGURACIÓN SMTP — cambia estos valores por los de tu cuenta
# =============================================================================
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "penaloza.lorenviviana@gmail.com"       # <-- tu correo Gmail
SMTP_PASSWORD = "dexn ttlk grto siwp"     # <-- contraseña de aplicación Gmail
SMTP_FROM     = "Clínica <penaloza.lorenviviana@gmail.com>"

# Almacén temporal de códigos  { correo: codigo }
codigos_temporales = {}


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
    datos = request.get_json()
    correo  = datos.get('correo', '').strip().lower()
    nombre  = datos.get('nombre', 'Usuario')

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
        msg['Subject'] = "Tu código de verificación"
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
# API — VERIFICACIÓN DEL CÓDIGO INGRESADO POR EL USUARIO
# =============================================================================

@app.route('/api/verificar-codigo', methods=['POST'])
def verificar_codigo():
    datos   = request.get_json()
    correo  = datos.get('correo', '').strip().lower()
    ingresado = str(datos.get('codigo', '')).strip()

    esperado = codigos_temporales.get(correo)

    if not esperado:
        return jsonify({"ok": False, "error": "No hay código generado para este correo"}), 400

    if ingresado == esperado:
        del codigos_temporales[correo]
        return jsonify({"ok": True}), 200
    else:
        return jsonify({"ok": False, "error": "Código incorrecto"}), 400


# =============================================================================
# API — CITAS (agendar.html)
# =============================================================================

@app.route('/api/cita/crear', methods=['POST'])
def crear_cita():
    datos = request.get_json()
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (datos.get('Paciente_ID'), datos.get('Agenda_ID'), datos.get('Motivo_Consulta'))
        )
        conexion.commit()
        return jsonify({"status": "Cita registrada con éxito"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()


# =============================================================================
# INICIO
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True)