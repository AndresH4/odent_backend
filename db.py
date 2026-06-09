import sqlite3

def get_connection():
    conn = sqlite3.connect("odent.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ======================================================
    # 🟢 TABLAS 1-8 → MODULO USUARIOS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rol (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS genero (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipo_de_documento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        email TEXT,
        password TEXT,
        rol_id INTEGER,
        estado_usuario_id INTEGER,
        genero_id INTEGER,
        tipo_de_documento_id INTEGER,
        FOREIGN KEY (rol_id) REFERENCES rol(id),
        FOREIGN KEY (estado_usuario_id) REFERENCES estado_usuario(id),
        FOREIGN KEY (genero_id) REFERENCES genero(id),
        FOREIGN KEY (tipo_de_documento_id) REFERENCES tipo_de_documento(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS administrador (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aseguramiento_de_datos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        fecha TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accion_aseg_datos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aseguramiento_id INTEGER,
        accion TEXT,
        FOREIGN KEY (aseguramiento_id) REFERENCES aseguramiento_de_datos(id)
    )
    """)

    # ======================================================
    # 🟡 TABLAS 9-15 → EPS / PACIENTE / PREGUNTAS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipoeps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regimen_eps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        tipoeps_id INTEGER,
        regimen_eps_id INTEGER,
        FOREIGN KEY (tipoeps_id) REFERENCES tipoeps(id),
        FOREIGN KEY (regimen_eps_id) REFERENCES regimen_eps(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS afiliacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        eps_id INTEGER,
        fecha TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuario(id),
        FOREIGN KEY (eps_id) REFERENCES eps(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paciente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_pregunta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texto TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_respuesta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta_id INTEGER,
        texto TEXT,
        FOREIGN KEY (pregunta_id) REFERENCES tabla_pregunta(id)
    )
    """)

    # ======================================================
    # 🔵 TABLAS 16-23 → ESPECIALISTAS / CITAS
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialistas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialidad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialista_especialidad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        especialidad_id INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(id),
        FOREIGN KEY (especialidad_id) REFERENCES especialidad(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_agenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        fecha TEXT,
        estado_agenda_id INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(id),
        FOREIGN KEY (estado_agenda_id) REFERENCES estado_agenda(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cita (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        especialista_id INTEGER,
        fecha TEXT,
        estado TEXT,
        FOREIGN KEY (paciente_id) REFERENCES paciente(id),
        FOREIGN KEY (especialista_id) REFERENCES especialistas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado_multa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS multa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        monto REAL,
        estado_multa_id INTEGER,
        FOREIGN KEY (paciente_id) REFERENCES paciente(id),
        FOREIGN KEY (estado_multa_id) REFERENCES estado_multa(id)
    )
    """)

    # ======================================================
    # 🟣 TABLAS 24-28 → HISTORIAL CLÍNICO
    # ======================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_clinico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        descripcion TEXT,
        FOREIGN KEY (paciente_id) REFERENCES paciente(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_diagnostico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_diagnostico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        historial_id INTEGER,
        diagnostico_id INTEGER,
        FOREIGN KEY (historial_id) REFERENCES historial_clinico(id),
        FOREIGN KEY (diagnostico_id) REFERENCES tabla_diagnostico(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tratamiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        historial_id INTEGER,
        descripcion TEXT,
        FOREIGN KEY (historial_id) REFERENCES historial_clinico(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tabla_puntuacion_especialista (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        especialista_id INTEGER,
        puntuacion INTEGER,
        FOREIGN KEY (especialista_id) REFERENCES especialistas(id)
    )
    """)

    # ======================================================
    conn.commit()
    conn.close() 