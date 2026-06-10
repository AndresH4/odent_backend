
import mysql.connector

def get_connection():

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='odent'
    )

    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ======================================================
    # 🟢 TABLAS 1-8 → MODULO USUARIOS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rol (
        rol_id INTEGER PRIMARY KEY AUTOINCREMENT,
        descripcion TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_usuario (
        estado_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_estado TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS genero (
        genero_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_genero TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipo_de_documento (
        tipo_documento_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_documento TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuario (
        usuario_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombres TEXT,
        apellidos TEXT,
        tipo_de_documento_id INTEGER,
        numero_documento TEXT,
        contraseña TEXT,
        fecha_nacimiento DATE,
        genero_id INTEGER,
        correo TEXT,
        telefono TEXT,
        estado_usuario_id INTEGER,
        rol_id INTEGER,
        FOREIGN KEY (rol_id) REFERENCES rol(rol_id),
        FOREIGN KEY (estado_usuario_id) REFERENCES estado_usuario(estado_id),
        FOREIGN KEY (genero_id) REFERENCES genero(genero_id),
        FOREIGN KEY (tipo_de_documento_id) REFERENCES tipo_de_documento(tipo_documento_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS administrador (
        administrador_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aseguramiento_de_datos (
        aseguramiento_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        fecha TEXT,
        accion_id INTEGER,
        descripcion TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id),
        FOREIGN KEY (accion_id) REFERENCES accion_aseg_datos(accion_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accion_aseg_datos (
        accion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_accion TEXT,
        FOREIGN KEY (aseguramiento_id) REFERENCES aseguramiento_de_datos(aseguramiento_id)
    )
    """)

    # ======================================================
    # 🟡 TABLAS 9-15 → EPS / PACIENTE / PREGUNTAS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipoeps (
        tipoeps_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_tipoeps TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regimen_eps (
        regimen_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_regimen TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eps (
        eps_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        tipoeps_id INTEGER,
        regimen_eps_id INTEGER,
        FOREIGN KEY (tipoeps_id) REFERENCES tipoeps(tipoeps_id),
        FOREIGN KEY (regimen_eps_id) REFERENCES regimen_eps(regimen_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS afiliacion (
        afiliacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        eps_id INTEGER,
        fecha TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id),
        FOREIGN KEY (eps_id) REFERENCES eps(eps_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paciente (
        paciente_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_pregunta (
        pregunta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        texto TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_respuesta (
        respuesta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta_id INTEGER,
        texto TEXT,
        FOREIGN KEY (pregunta_id) REFERENCES tabla_pregunta(pregunta_id)
    )
    """)

    # ======================================================
    # 🔵 TABLAS 16-23 → ESPECIALISTAS / CITAS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialistas (
        especialista_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialidad (
        especialidad_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialista_especialidad (
        especialista_especialidad_id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        especialidad_id INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(especialista_id),
        FOREIGN KEY (especialidad_id) REFERENCES especialidad(especialidad_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_agenda (
        estado_agenda_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agenda (
        agenda_id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        fecha TEXT,
        estado_agenda_id INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(especialista_id),
        FOREIGN KEY (estado_agenda_id) REFERENCES estado_agenda(estado_agenda_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cita (
        cita_id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        especialista_id INTEGER,
        fecha TEXT,
        estado TEXT,
        FOREIGN KEY (paciente_id) REFERENCES paciente(paciente_id),
        FOREIGN KEY (especialista_id) REFERENCES especialistas(especialista_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_multa (
        estado_multa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS multa (
        multa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        monto REAL,
        estado_multa_id INTEGER,
        FOREIGN KEY (paciente_id) REFERENCES paciente(paciente_id),
        FOREIGN KEY (estado_multa_id) REFERENCES estado_multa(estado_multa_id)
    )
    """)

    # ======================================================
    # 🟣 TABLAS 24-28 → HISTORIAL CLÍNICO
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_clinico (
        historial_id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        descripcion TEXT,
        FOREIGN KEY (paciente_id) REFERENCES paciente(paciente_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_diagnostico (
        diagnostico_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_diagnostico (
        historial_diagnostico_id INTEGER PRIMARY KEY AUTOINCREMENT,
        historial_id INTEGER,
        diagnostico_id INTEGER,
        FOREIGN KEY (historial_id) REFERENCES historial_clinico(historial_id),
        FOREIGN KEY (diagnostico_id) REFERENCES tabla_diagnostico(diagnostico_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tratamiento (
        tratamiento_id INTEGER PRIMARY KEY AUTOINCREMENT,
        historial_id INTEGER,
        descripcion TEXT,
        FOREIGN KEY (historial_id) REFERENCES historial_clinico(historial_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_puntuacion_especialista (
        tabla_puntuacion_especialista_id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        puntuacion INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(especialista_id)
    )
    """)

    # ======================================================
    conn.commit()
    conn.close() 