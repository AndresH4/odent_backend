from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3  # Necesario para sqlite3.Row en la ruta /roles existente
 
# Conexión compartida (ya existente, NO se modifica)
from db import get_db_connection
 
# ─── NUEVO: Blueprint modularizado del módulo de usuarios ─────────────────────
# Incluye: rol, genero, tipo_documento, estado_usuario, usuario (login/CRUD),
# administrador, accion_aseguramiento, aseguramiento_datos (auditoría)
from modulo_usuarios.routes import usuarios_bp
 
app = Flask(__name__)
 
# Habilitamos CORS para que el frontend (HTML/JS) pueda hacer peticiones sin ser bloqueado
CORS(app)
 
# ─── NUEVO: Registro del blueprint ─────────────────────────────────────────────
# Todas las rutas de modulo_usuarios quedan disponibles bajo el prefijo /api
# Ejemplos: POST /api/auth/login, GET /api/usuarios, GET /api/roles,
#           GET /api/auditoria, PUT /api/usuarios/<id>/estado, etc.
app.register_blueprint(usuarios_bp, url_prefix='/api')
 
 
# =============================================================================
# RUTAS DE EJEMPLO EXISTENTES (citas) — se mantienen para no romper agendar.html
# =============================================================================
# NOTA: La ruta GET /api/usuarios que tenías aquí se ELIMINÓ porque colisionaba
# con la del blueprint (modulo_usuarios/routes.py). La nueva versión en
# GET /api/usuarios ya incluye JOIN con Rol, Estado, Genero y TipoDocumento,
# así que es un reemplazo directo y mejorado — no necesitas cambiar nada
# en el frontend que ya consuma GET /api/usuarios.
 
@app.route('/api/cita/crear', methods=['POST'])
def crear_cita():
    """Ejemplo de ruta POST: Recibe información del Frontend y la guarda.
    NOTA: Esta ruta se migrará a modulo_citas/routes.py cuando exista ese
    módulo. Por ahora se mantiene activa para no romper agendar.html."""
    datos = request.get_json()
 
    paciente_id = datos.get('Paciente_ID')
    agenda_id = datos.get('Agenda_ID')
    motivo = datos.get('Motivo_Consulta')
 
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
 
        cursor.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (paciente_id, agenda_id, motivo)
        )
 
        conexion.commit()
        return jsonify({"status": "Cita registrada con éxito"}), 201
 
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# FLUJO DE CREACIÓN DE USUARIO (creacion.html) — INTACTO, YA FUNCIONA
# =============================================================================
 
@app.route('/vista/crear_usuario')
def vista_creacion_usuario():
    """Ruta encargada de mostrar la interfaz gráfica de registro"""
    return render_template('creacion.html')
 
 
@app.route('/roles', methods=['GET'])
def get_roles_creacion():
    """Suministra la lista de roles directamente de la base de datos al select de la interfaz"""
    conexion = None
    try:
        conexion = get_db_connection()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
 
        cursor.execute("SELECT ROL_ID, DESCRIPCION AS Nombre_Rol FROM rol")
 
        filas = cursor.fetchall()
        lista_roles = [dict(fila) for fila in filas]
        return jsonify(lista_roles), 200
    except Exception as e:
        print(f"\n❌ ERROR REAL EN /roles: {str(e)}\n")
        return jsonify({"error": str(e)}), 500
    finally:
        if conexion:
            conexion.close()
 
 
@app.route('/usuarios', methods=['POST'])
def add_usuario_creacion():
    """Recibe los datos estructurados desde creacion.js y los inserta en la base de datos"""
    datos = request.get_json()
    conexion = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
 
        cursor.execute(
            """INSERT INTO usuarios (Nombres, Apellidos, NumeroDocumento, Telefono, Correo, Contrasena, Rol_ID, Genero_ID, TipoDoc_ID, Estado_ID, FechaNacimiento)
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
        return jsonify({"ok": True, "status": "Usuario creado con éxito en SQLite"}), 201
 
    except Exception as e:
        print(f"\n❌ ERROR AL CREAR USUARIO: {str(e)}\n")
        return jsonify({"ok": False, "error": str(e)}), 400
 
    finally:
        if conexion:
            conexion.close()
 
 
# =============================================================================
# NUEVO: RUTAS DE VISTAS — sirven cada página HTML del frontend
# =============================================================================
# Si alguna de estas rutas ya existe en otra parte de tu proyecto, elimina
# el duplicado para evitar el mismo tipo de colisión que arreglamos arriba.
 
@app.route('/')
@app.route('/login')
@app.route('/login.html')
def vista_login():
    return render_template('login.html')
 
 
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
 
 
# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)