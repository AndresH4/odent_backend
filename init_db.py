# =============================================================================
# init_db.py — UNIFICADO
#
# Combina los dos scripts de inicialización sin eliminar nada:
#
#   • config_ranking conserva Horas_Envio + Estado_Envio (archivo 2)
#     Y añade la columna Estado (1=Activo, 2=Inactivo) del archivo 1.
#     La migración Estado_Envio → Estado se realiza de forma segura.
#
#   • puntuacion_especialista añade Calificacion_Promedio REAL (archivo 1).
#
#   • diagnostico recibe la columna Codigo (migración: Codigo_CIE10 → Codigo
#     si existía con ese nombre) y se recarga con el catálogo oficial CIE-10
#     de 26 diagnósticos (archivo 2). El historial_diagnostico se repuebla
#     respetando los nuevos IDs.
#
#   • Helpers _add_column_if_missing y _rename_column_if_exists presentes.
#   • Índices idx_agenda_unica_activa e idx_diagnostico_codigo.
#   • INSERT OR IGNORE en todos los catálogos y relaciones: nunca destruye datos.
#   • Sin DROP TABLE en ningún caso.
#
# SEGURO PARA BD EXISTENTE:
#   - CREATE TABLE IF NOT EXISTS  → no destruye tablas existentes.
#   - INSERT OR IGNORE             → evita duplicados.
#   - ALTER TABLE dinámico         → añade columnas faltantes sin recrear tablas.
#   - CREATE INDEX IF NOT EXISTS   → no falla si el índice ya existe.
# =============================================================================

import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE MIGRACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _add_column_if_missing(cursor, table: str, column: str, col_def: str):
    """Ejecuta ALTER TABLE … ADD COLUMN solo si la columna no existe ya."""
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    if column not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        print(f"  ✚ columna '{column}' añadida a '{table}'")


def _rename_column_if_exists(cursor, connection, table: str, old_col: str, new_col: str):
    """
    Renombra una columna usando ALTER TABLE … RENAME COLUMN (SQLite >= 3.25).
    Si la columna destino ya existe, no hace nada.
    Si la columna origen no existe, no hace nada.
    """
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    if new_col in cols:
        print(f"  ✔ columna '{new_col}' ya existe en '{table}', no se renombra")
        return
    if old_col not in cols:
        print(f"  ✔ columna '{old_col}' no existe en '{table}', nada que renombrar")
        return
    cursor.execute(f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}")
    connection.commit()
    print(f"  ✚ columna '{old_col}' renombrada a '{new_col}' en '{table}'")


# ─────────────────────────────────────────────────────────────────────────────
# DDL: tablas base (todas con IF NOT EXISTS)
#
# config_ranking mantiene Horas_Envio + Estado_Envio (archivo 2) porque son
# datos existentes. La columna Estado (archivo 1) se añade dinámicamente en
# la sección de migraciones para no romper BDs que ya tienen la tabla.
# ─────────────────────────────────────────────────────────────────────────────

SQL_TABLAS = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tipo_documento (
  TipoDoc_ID             INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Tipo_Documento  VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS genero (
  Genero_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  NombreGenero VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS estado_usuario (
  Estado_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Estado VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS rol (
  Rol_ID      INTEGER PRIMARY KEY AUTOINCREMENT,
  Descripcion VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS especialidad (
  Especialidad_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Especialidad VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS regimen_eps (
  Regimen_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
  Descripcion VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS tipo_afiliacion_eps (
  TipoEPS_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Tipo VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS tipo_eps (
  TipoEPS_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Tipo VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS estado_agenda (
  EstadoAgenda_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Estado   VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS estado_multa (
  EstadoMulta_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Estado  VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS preguntas_ranking (
  Preguntas_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
  Texto_Pregunta VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS accion_aseguramiento (
  Accion_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Accion VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnostico (
  Diagnostico_ID     INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Diagnostico VARCHAR(100) NOT NULL
  -- columna 'Codigo' se añade/renombra dinámicamente más abajo
);

-- config_ranking: conserva Horas_Envio + Estado_Envio.
-- La columna Estado (1=Activo, 2=Inactivo) se añade dinámicamente.
CREATE TABLE IF NOT EXISTS config_ranking (
  Config_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Horas_Envio  INTEGER NOT NULL DEFAULT 2,
  Estado_Envio INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS eps (
  EPS_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_EPS   VARCHAR(50) NOT NULL,
  Telefono_EPS VARCHAR(15) NOT NULL,
  Regimen_ID   INT NOT NULL,
  FOREIGN KEY (Regimen_ID) REFERENCES regimen_eps(Regimen_ID)
);

CREATE TABLE IF NOT EXISTS usuarios (
  Usuario_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombres          VARCHAR(50)  NOT NULL,
  Apellidos        VARCHAR(50)  NOT NULL,
  TipoDoc_ID       INT NOT NULL,
  NumeroDocumento  VARCHAR(15)  NOT NULL,
  Contrasena       VARCHAR(255) NOT NULL,
  FechaNacimiento  DATE NOT NULL,
  Genero_ID        INT NOT NULL,
  Correo           VARCHAR(100) NOT NULL,
  Telefono         VARCHAR(15)  NOT NULL,
  Estado_ID        INT NOT NULL,
  Rol_ID           INT NOT NULL,
  FOREIGN KEY (TipoDoc_ID)  REFERENCES tipo_documento(TipoDoc_ID),
  FOREIGN KEY (Genero_ID)   REFERENCES genero(Genero_ID),
  FOREIGN KEY (Estado_ID)   REFERENCES estado_usuario(Estado_ID),
  FOREIGN KEY (Rol_ID)      REFERENCES rol(Rol_ID)
);

CREATE TABLE IF NOT EXISTS administrador (
  Administrador_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Usuario_ID       INT NOT NULL,
  FOREIGN KEY (Usuario_ID) REFERENCES usuarios(Usuario_ID)
);

CREATE TABLE IF NOT EXISTS paciente (
  Paciente_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Usuario_ID  INT NOT NULL,
  FOREIGN KEY (Usuario_ID) REFERENCES usuarios(Usuario_ID)
);

CREATE TABLE IF NOT EXISTS especialista (
  Especialista_ID     INTEGER PRIMARY KEY AUTOINCREMENT,
  Usuario_ID          INT NOT NULL,
  Tarjeta_Profesional VARCHAR(20) NOT NULL,
  FOREIGN KEY (Usuario_ID) REFERENCES usuarios(Usuario_ID)
);

CREATE TABLE IF NOT EXISTS especialista_especialidad (
  Especialista_ID INT NOT NULL,
  Especialidad_ID INT NOT NULL,
  PRIMARY KEY (Especialista_ID, Especialidad_ID),
  FOREIGN KEY (Especialista_ID) REFERENCES especialista(Especialista_ID),
  FOREIGN KEY (Especialidad_ID) REFERENCES especialidad(Especialidad_ID)
);

CREATE TABLE IF NOT EXISTS afiliacion (
  Afiliacion_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Usuario_ID       INT NOT NULL,
  EPS_ID           INT NOT NULL,
  TipoEPS_ID       INT NOT NULL,
  Fecha_Afiliacion DATE NOT NULL,
  FOREIGN KEY (Usuario_ID) REFERENCES usuarios(Usuario_ID),
  FOREIGN KEY (EPS_ID)     REFERENCES eps(EPS_ID)
);

CREATE TABLE IF NOT EXISTS aseguramiento_datos (
  AseguramientoDatos_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Usuario_ID            INT NOT NULL,
  Accion_ID             INT NOT NULL,
  Fecha                 DATE NOT NULL,
  Descripcion           TEXT NOT NULL,
  FOREIGN KEY (Usuario_ID) REFERENCES usuarios(Usuario_ID),
  FOREIGN KEY (Accion_ID)  REFERENCES accion_aseguramiento(Accion_ID)
);

CREATE TABLE IF NOT EXISTS agenda (
  Agenda_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
  Especialista_ID INT NOT NULL,
  Fecha           DATE NOT NULL,
  Hora_Inicio     TIME NOT NULL,
  Hora_Final      TIME NOT NULL,
  EstadoAgenda_ID INT NOT NULL,
  FOREIGN KEY (Especialista_ID) REFERENCES especialista(Especialista_ID),
  FOREIGN KEY (EstadoAgenda_ID) REFERENCES estado_agenda(EstadoAgenda_ID)
);

CREATE TABLE IF NOT EXISTS cita (
  Cita_ID         INTEGER PRIMARY KEY AUTOINCREMENT,
  Paciente_ID     INT NOT NULL,
  Agenda_ID       INT NOT NULL,
  Motivo_Consulta VARCHAR(50) NOT NULL,
  FOREIGN KEY (Paciente_ID) REFERENCES paciente(Paciente_ID),
  FOREIGN KEY (Agenda_ID)   REFERENCES agenda(Agenda_ID)
);

CREATE TABLE IF NOT EXISTS multa (
  Multa_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
  Cita_ID        INT NOT NULL,
  EstadoMulta_ID INT NOT NULL,
  FOREIGN KEY (Cita_ID)        REFERENCES cita(Cita_ID),
  FOREIGN KEY (EstadoMulta_ID) REFERENCES estado_multa(EstadoMulta_ID)
);

CREATE TABLE IF NOT EXISTS respuesta_ranking (
  Respuesta_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Cita_ID      INT NOT NULL,
  Preguntas_ID INT NOT NULL,
  Respuesta    INT NOT NULL,
  FOREIGN KEY (Cita_ID)      REFERENCES cita(Cita_ID),
  FOREIGN KEY (Preguntas_ID) REFERENCES preguntas_ranking(Preguntas_ID)
);

-- puntuacion_especialista: incluye Calificacion_Promedio REAL (archivo 1).
-- Se añade dinámicamente para BDs existentes que aún no la tengan.
CREATE TABLE IF NOT EXISTS puntuacion_especialista (
  Puntuacion_ID        INTEGER PRIMARY KEY AUTOINCREMENT,
  Especialista_ID      INT NOT NULL,
  Respuesta_ID         INT NOT NULL,
  Calificacion_Promedio REAL,
  FOREIGN KEY (Especialista_ID) REFERENCES especialista(Especialista_ID),
  FOREIGN KEY (Respuesta_ID)    REFERENCES respuesta_ranking(Respuesta_ID)
);

CREATE TABLE IF NOT EXISTS historial_clinico (
  Historial_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Cita_ID      INT NOT NULL,
  FOREIGN KEY (Cita_ID) REFERENCES cita(Cita_ID)
);

CREATE TABLE IF NOT EXISTS historial_diagnostico (
  Historial_ID   INT NOT NULL,
  Diagnostico_ID INT NOT NULL,
  PRIMARY KEY (Historial_ID, Diagnostico_ID),
  FOREIGN KEY (Historial_ID)   REFERENCES historial_clinico(Historial_ID),
  FOREIGN KEY (Diagnostico_ID) REFERENCES diagnostico(Diagnostico_ID)
);

CREATE TABLE IF NOT EXISTS tratamiento (
  Tratamiento_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Historial_ID   INT NOT NULL,
  Descripcion    VARCHAR(255) NOT NULL,
  FOREIGN KEY (Historial_ID) REFERENCES historial_clinico(Historial_ID)
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# DDL: índices
# ─────────────────────────────────────────────────────────────────────────────

SQL_INDICES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_agenda_unica_activa
ON agenda (Especialista_ID, Fecha, Hora_Inicio)
WHERE EstadoAgenda_ID IN (1, 2);
"""

SQL_INDICE_DIAGNOSTICO = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_diagnostico_codigo
ON diagnostico (Codigo)
WHERE Codigo IS NOT NULL;
"""

# ─────────────────────────────────────────────────────────────────────────────
# DML: catálogos con INSERT OR IGNORE
# ─────────────────────────────────────────────────────────────────────────────

SQL_CATALOGOS = """
INSERT OR IGNORE INTO tipo_documento (TipoDoc_ID, Nombre_Tipo_Documento) VALUES
  (1, 'Cedula de ciudadania'),
  (2, 'Cedula de Extranjeria'),
  (3, 'Tarjeta de identidad'),
  (4, 'Registro civil'),
  (5, 'Pasaporte'),
  (6, 'Permiso Especial de Permanencia'),
  (7, 'Documento de Identificacion Extranjero'),
  (8, 'Permiso por proteccion temporal');

INSERT OR IGNORE INTO genero (Genero_ID, NombreGenero) VALUES
  (1, 'Femenino'), (2, 'Masculino');

INSERT OR IGNORE INTO estado_usuario (Estado_ID, Nombre_Estado) VALUES
  (1, 'Activo'), (2, 'Inactivo');

INSERT OR IGNORE INTO rol (Rol_ID, Descripcion) VALUES
  (1, 'Administrador'), (2, 'Especialista'), (3, 'Paciente');

INSERT OR IGNORE INTO especialidad (Especialidad_ID, Nombre_Especialidad) VALUES
  (1, 'Ortodoncia'),
  (2, 'Endodoncia'),
  (3, 'Periodoncia'),
  (4, 'Rehabilitación Oral'),
  (5, 'Cirugía Oral'),
  (6, 'Odontopediatría'),
  (7, 'Estética Dental'),
  (8, 'Implantes Dentales');

INSERT OR IGNORE INTO regimen_eps (Regimen_ID, Descripcion) VALUES
  (1, 'Contributivo'), (2, 'Subsidiado');

INSERT OR IGNORE INTO tipo_afiliacion_eps (TipoEPS_ID, Nombre_Tipo) VALUES
  (1, 'Cotizante'), (2, 'Beneficiario');

INSERT OR IGNORE INTO tipo_eps (TipoEPS_ID, Nombre_Tipo) VALUES
  (1, 'Cotizante'), (2, 'Beneficiario');

INSERT OR IGNORE INTO eps (EPS_ID, Nombre_EPS, Telefono_EPS, Regimen_ID) VALUES
  (1, 'Compensar',    '601 4441234', 1),
  (2, 'Salud Total',  '601 4055440', 1),
  (3, 'NuevaEPS',     '601 3077022', 1),
  (4, 'Famisanar',    '301 3078069', 1),
  (5, 'Sanitas',      '601 3759000', 1),
  (6, 'CapitalSalud', '601 7427257', 2),
  (7, 'Sura',         '601 4897941', 1);

INSERT OR IGNORE INTO estado_agenda (EstadoAgenda_ID, Nombre_Estado) VALUES
  (1, 'Disponible'), (2, 'Ocupado'), (3, 'Cancelado'), (4, 'Cumplida');

INSERT OR IGNORE INTO accion_aseguramiento (Accion_ID, Nombre_Accion) VALUES
  (1, 'Asegurar'), (2, 'Actualizar'), (3, 'Eliminar');

INSERT OR IGNORE INTO estado_multa (EstadoMulta_ID, Nombre_Estado) VALUES
  (1, 'Pendiente'), (2, 'Pagada');

INSERT OR IGNORE INTO preguntas_ranking (Preguntas_ID, Texto_Pregunta) VALUES
  (1, '¿El odontologo fue amable durante la consulta?'),
  (2, '¿Te explico claramente el diagnostico?');

-- config_ranking: fila única con todos los campos (Horas_Envio, Estado_Envio, Estado).
-- Estado se añade dinámicamente; este INSERT cubre Horas_Envio y Estado_Envio.
INSERT OR IGNORE INTO config_ranking (Config_ID, Horas_Envio, Estado_Envio)
  VALUES (1, 2, 1);
"""

# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO OFICIAL CIE-10 ODONTOLÓGICO — 26 diagnósticos canónicos
# Formato SIN punto decimal en todos los códigos.
# ─────────────────────────────────────────────────────────────────────────────

CATALOGO_CIE10_ODONTOLOGICO = [
    ("Z012", "EXAMEN ODONTOLOGICO"),
    ("K020", "CARIES LIMITADA AL ESMALTE"),
    ("K021", "CARIES DE LA DENTINA"),
    ("K022", "CARIES DEL CEMENTO"),
    ("K023", "CARIES DENTARIA DETENIDA"),
    ("K029", "CARIES DENTAL, NO ESPECIFICADA"),
    ("K040", "PULPITIS"),
    ("K041", "NECROSIS DE LA PULPA"),
    ("K044", "PERIODONTITIS APICAL AGUDA ORIGINADA EN LA PULPA"),
    ("K045", "PERIODONTITIS APICAL CRONICA"),
    ("K046", "ABSCESO PERIAPICAL CON FISTULA"),
    ("K047", "ABSCESO PERIAPICAL SIN FISTULA"),
    ("K050", "GINGIVITIS AGUDA"),
    ("K051", "GINGIVITIS CRONICA"),
    ("K052", "PERIODONTITIS AGUDA"),
    ("K053", "PERIODONTITIS CRONICA"),
    ("K060", "RETRACCION GINGIVAL"),
    ("K010", "DIENTES INCLUIDOS"),
    ("K011", "DIENTES IMPACTADOS"),
    ("K083", "RAIZ DENTAL RETENIDA"),
    ("K103", "ALVEOLITIS DEL MAXILAR"),
    ("K120", "ESTOMATITIS AFTOSA RECURRENTE"),
    ("S025", "FRACTURA DE LOS DIENTES"),
    ("S032", "LUXACION DE DIENTE"),
    ("Z463", "PRUEBA Y AJUSTE DE PROTESIS DENTAL"),
    ("Z464", "PRUEBA Y AJUSTE DE DISPOSITIVO ORTODONCICO"),
]

# ─────────────────────────────────────────────────────────────────────────────
# DML: especialidades nuevas (idempotente)
# ─────────────────────────────────────────────────────────────────────────────

SQL_ESPECIALIDADES_NUEVAS = """
INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Ortodoncia' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Ortodoncia');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Endodoncia' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Endodoncia');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Periodoncia' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Periodoncia');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Rehabilitacion Oral' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Rehabilitación Oral');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Cirujia Oral' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Cirugía Oral');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Odontopediatria' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Odontopediatría');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Estetica Dental' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Estética Dental');

INSERT INTO especialidad (Nombre_Especialidad)
SELECT 'Implantes Dentales' WHERE NOT EXISTS (SELECT 1 FROM especialidad WHERE Nombre_Especialidad = 'Implantes Dentales');
"""

# ─────────────────────────────────────────────────────────────────────────────
# Datos de usuarios (seed)
# ─────────────────────────────────────────────────────────────────────────────

USUARIOS_DATA = [
    ('Andres Felipe',    'Hernandez Rodriguez',  1, '1028465975', 'Andresh04_',         '1996-08-24', 2, 'andresfhernandez4@gmail.com', '3136684258', 1, 1),
    ('Iris Dayana',      'Joya Estupian',         1, '1054888650', 'Irisjoya12*',         '2002-03-12', 1, 'iris.dayana@gmail.com',        '3056894808', 1, 2),
    ('Isabella Maria',   'Cabal Rodriguez',       1, '1020834210', 'Isacabal9.',          '2000-11-03', 1, 'isacabalr09@gmail.com',        '3108849033', 1, 3),
    ('Maicol Stiven',    'Poveda Cuellar',         1, '1230764856', 'Maicolpoveda..40',    '2001-07-23', 2, 'maicollsfanfan@gmail.com',     '3124569845', 1, 3),
    ('Lorena Valentina', 'Penaloza Gomez',         1, '1023987345', 'Lorevpenaloza__30',   '2006-04-15', 1, 'lore_valentina30@gmail.com',   '3219964823', 1, 3),
    ('Kevin Andres',     'Ocampo Vasquez',         1, '1000684012', 'Kandresovasquez*07',  '2002-01-11', 2, 'kevandres04@gmail.com',        '3132438921', 1, 3),
    ('Juliana',          'Olarte Gomez',           1, '1095425107', 'Juli_olarte28',       '1998-12-30', 1, 'julianaolarte@gmail.com',      '3255699949', 1, 2),
    ('Paula Alejandra',  'Hernandez Parra',        3, '11696298',   'Paulahern.*56',       '1991-06-05', 1, 'paulahernandez@gmail.com',     '3124567890', 1, 2),
    ('Dayana Alexandra', 'Agudelo Medina',         3, '7264893',    'Alexandraagu44*',     '2005-09-18', 1, 'dayanaa_agudelo@gmail.com',    '3108982640', 1, 3),
    ('Gabriela Lishet',  'Pozo Ortiz',             1, '1023666105', 'gabY2910.',           '2004-06-22', 1, 'gabrilpozo_16@gmail.com',      '3213244214', 1, 3),
    ('Clara Maria',      'Castillo marquez',       1, '1018885632', 'Claramn_09',          '2001-02-09', 1, 'claracastillo01@gmail.com',    '3227845689', 1, 2),
    ('Jorge Andres',     'Perez Joya',             3, '1022455699', 'Jorgitop.30',         '2000-10-30', 2, 'jorgeperez02@gmail.com',       '3244455578', 1, 2),
    ('Lucia Maria',      'Colmenares Martinez',    1, '1099958546', 'Luciacolmenares_28',  '2007-04-28', 1, 'luciolmenares@gmail.com',      '3125689708', 1, 2),
    ('Alisson Sofia',    'Gonzales Rivera',        2, '1024762387', 'Alissongonzales12%',  '2012-09-12', 1, 'Alissonsfiagonr@gmail.com',    '3208731292', 1, 3),
    ('Martin Alejandro', 'Ordonez Parra',          1, '1004466755', 'Martinp04_',          '2006-10-04', 2, 'martin26op@gmail.com',         '3116489554', 1, 3),
    ('Katy Andrea',      'Lagos Manrique',         1, '1113976297', 'katyLagos_02',        '2000-07-02', 1, 'katylagos@gmail.com',          '3244744875', 1, 2),
    ('Carlos Felipe',    'Castellano Maldonado',   1, '1132527487', 'carlosCC_09.',        '2004-01-09', 2, 'maldonado.carlos@gmail.com',   '3225476125', 1, 2),
    ('Jurleidis Maria',  'Gonzales Prieto',        3, '1151078677', 'jMuly.08',            '1997-12-08', 1, 'jurleidisprieto@gmail.com',    '3200054876', 1, 2),
    ('Angela',           'Arias Canon',            2, '1230678310', 'Angelaa99.',          '2014-11-09', 1, 'angelarias4@gmail.com',        '3142186778', 1, 3),
    ('Natalia Isabella', 'Parra Perez',            1, '1188181058', 'Nataliaparra_31',     '2004-10-31', 1, 'nataliaparra@gmail.com',       '3006546925', 1, 2),
    ('Sara Maria',       'Garcia Reina',           1, '1432982314', 'Saaragarcia*06',      '2006-12-06', 1, 'saramgar28@gmail.com',         '3208871462', 1, 3),
    ('Juan Jose',        'Perez Garcia',           1, '1429637536', 'Juann**28',           '2001-01-28', 2, 'juanperez@gmail.com',          '3113145821', 1, 3),
    ('Maria Fernanda',   'Lopez Torres',           1, '1023674009', 'MariaFernanda05.',    '2005-05-05', 1, 'lopezfernanda@gmail.com',      '3209425824', 1, 3),
    ('Carlos Felipe',    'Ruiz Lima',              1, '1019762538', 'Carlosruiz0880',      '1995-08-24', 2, 'carlosruiz@gmail.com',         '3102857413', 1, 3),
    ('Ana Maria',        'Belen Rojas',            1, '1006667274', 'Anaa*.27',            '2001-05-27', 1, 'anamaria88@gmail.com',         '3220145856', 1, 3),
    ('Luis Fernando',    'Castro Ortiz',           1, '1208554755', 'Luiscas&20',          '2003-04-20', 2, 'luisxcastro@gmail.com',        '3117547674', 1, 3),
    ('Elena Sofia',      'Mendez Paz',             1, '1109986749', 'ElenaM._11',          '2007-01-11', 1, 'elenamendez@gmail.com',        '3205892244', 1, 3),
    ('Jorge Enrique',    'Villa Sol',              1, '1006456477', 'Jorge_e09',           '1998-02-09', 2, 'jorgevilla@gmail.com',         '3136485315', 1, 3),
    ('Paula Sofia',      'Luna Mar',               1, '1024440980', 'Paulaluna*06',        '2007-10-06', 1, 'paulitalinda@gmail.com',       '3123251678', 1, 3),
    ('Roberto Andres',   'Diaz Mena',              1, '1002366327', 'Robertodd.03',        '2004-05-03', 2, 'robertod@gmail.com',           '3152468228', 1, 3),
    ('Lucia Alejandra',  'Vega Solis',             1, '1109263541', 'Luciavega24*',        '2007-08-24', 1, 'luciavega@gmail.com',          '3195543648', 1, 3),
]

SQL_RELACIONES = """
INSERT OR IGNORE INTO administrador (Administrador_ID, Usuario_ID) VALUES (1, 1);

INSERT OR IGNORE INTO paciente (Paciente_ID, Usuario_ID) VALUES
  (1,3),(2,4),(3,5),(4,6),(5,9),(6,10),(7,14),(8,15),(9,19),
  (10,21),(11,22),(12,23),(13,24),(14,25),(15,26),(16,27),(17,28),(18,29),(19,30),(20,31);

INSERT OR IGNORE INTO especialista (Especialista_ID, Usuario_ID, Tarjeta_Profesional) VALUES
  (1,11,'5927164694'),(2,12,'4296334121'),(3,13,'4120360398'),(4,2,'7216022024'),(5,7,'9090557364'),
  (6,16,'5231071029'),(7,17,'6405121623'),(8,18,'9009615096'),(9,8,'1007054724'),(10,20,'3365822043');

INSERT OR IGNORE INTO especialista_especialidad (Especialista_ID, Especialidad_ID) VALUES
  (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,1),(8,2),(9,3),(10,4);

INSERT OR IGNORE INTO afiliacion (Afiliacion_ID, Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion) VALUES
  (1,1,1,1,'2025-05-15'),(2,2,7,1,'2023-08-06'),(3,3,6,1,'2025-09-09'),
  (4,4,2,1,'2021-02-28'),(5,5,2,1,'2023-07-21'),(6,6,1,1,'2022-09-22'),
  (7,7,4,1,'2026-01-31'),(8,8,2,1,'2026-02-12'),(9,9,3,1,'2023-05-18'),
  (10,10,5,1,'2025-03-12'),(11,11,4,1,'2025-05-21'),(12,12,6,1,'2016-08-14'),
  (13,13,1,1,'2015-06-15'),(14,14,2,1,'2016-04-12'),(15,15,7,1,'2025-02-15'),
  (16,16,3,1,'2017-06-30'),(17,17,4,1,'2023-07-21'),(18,18,5,1,'2022-09-22'),
  (19,19,1,1,'2026-01-31'),(20,20,1,1,'2026-02-12'),(21,21,4,1,'2023-05-18'),
  (22,22,6,1,'2025-03-12'),(23,23,2,1,'2025-05-21'),(24,24,7,1,'2016-08-14'),
  (25,25,1,1,'2015-06-15'),(26,26,6,1,'2020-08-24'),(27,27,1,1,'2024-03-15'),
  (28,28,6,1,'2020-04-12'),(29,29,4,1,'2025-08-24'),(30,30,5,1,'2025-09-04'),
  (31,31,2,1,'2026-02-22');

INSERT OR IGNORE INTO agenda (Agenda_ID, Especialista_ID, Fecha, Hora_Inicio, Hora_Final, EstadoAgenda_ID) VALUES
  (1,1,'2026-03-09','09:00:00','09:30:00',1),(2,2,'2026-03-15','14:00:00','14:30:00',2),
  (3,3,'2026-03-21','10:00:00','10:30:00',3),(4,4,'2026-03-21','14:00:00','15:00:00',2),
  (5,5,'2026-03-23','13:00:00','13:30:00',2),(6,6,'2026-03-26','16:00:00','17:30:00',2),
  (7,7,'2026-03-27','08:00:00','08:30:00',2),(8,8,'2026-03-27','13:00:00','13:40:00',1),
  (9,9,'2026-03-27','14:00:00','14:30:00',2),(10,10,'2026-03-28','14:00:00','15:00:00',2);

INSERT OR IGNORE INTO cita (Cita_ID, Paciente_ID, Agenda_ID, Motivo_Consulta, Encuesta_Enviada) VALUES
  (1,1,1,'Dolor Dental',0),(2,2,2,'Revision',0),(3,3,3,'Limpieza',0),
  (4,4,4,'Ortodoncia',0),(5,5,5,'Ortodoncia',0),(6,6,6,'Cirujia',0),
  (7,7,7,'Tratamiento',0),(8,8,8,'Ortodoncia',0),(9,9,9,'Limpieza',0),
  (10,10,10,'Control Ortodoncia',0);

INSERT OR IGNORE INTO multa (Multa_ID, Cita_ID, EstadoMulta_ID) VALUES
  (1,1,2),(2,2,1),(3,3,2),(4,4,2),(5,5,1),(6,6,1),(7,7,2),(8,8,2),(9,9,2),(10,10,1);

INSERT OR IGNORE INTO respuesta_ranking (Respuesta_ID, Cita_ID, Preguntas_ID, Respuesta) VALUES
  (1,1,1,5),(2,2,2,5);

-- puntuacion_especialista: incluye Calificacion_Promedio (del archivo 1).
INSERT OR IGNORE INTO puntuacion_especialista (Puntuacion_ID, Especialista_ID, Respuesta_ID, Calificacion_Promedio) VALUES
  (1,1,1,5.0),(2,2,2,5.0);

INSERT OR IGNORE INTO aseguramiento_datos (AseguramientoDatos_ID, Usuario_ID, Accion_ID, Fecha, Descripcion) VALUES
  (1,1,1,'2025-10-22','Datos asegurados'),(2,2,1,'2025-10-23','Datos asegurados'),
  (3,3,1,'2025-10-24','Datos asegurados'),(4,4,1,'2025-10-25','Datos asegurados'),
  (5,5,1,'2025-10-26','Datos asegurados'),(6,6,1,'2025-10-27','Datos asegurados'),
  (7,7,1,'2025-10-28','Datos asegurados'),(8,8,1,'2025-10-29','Datos asegurados'),
  (9,9,1,'2025-10-30','Datos asegurados'),(10,10,1,'2025-10-31','Datos asegurados'),
  (11,11,1,'2025-11-01','Datos asegurados'),(12,12,1,'2025-11-02','Datos asegurados'),
  (13,13,1,'2025-11-03','Datos asegurados'),(14,14,1,'2025-11-04','Datos asegurados'),
  (15,15,1,'2025-11-05','Datos asegurados'),(16,16,1,'2025-11-06','Datos asegurados'),
  (17,17,1,'2025-11-07','Datos asegurados'),(18,18,1,'2025-11-08','Datos asegurados'),
  (19,19,1,'2025-11-09','Datos asegurados'),(20,20,1,'2025-11-10','Datos asegurados'),
  (21,21,1,'2025-11-11','Datos asegurados'),(22,22,1,'2025-11-12','Datos asegurados'),
  (23,25,1,'2025-11-13','Datos asegurados'),(24,26,1,'2025-11-14','Datos asegurados'),
  (25,28,1,'2025-11-15','Datos asegurados'),(26,29,1,'2025-11-16','Datos asegurados'),
  (27,30,1,'2025-11-17','Datos asegurados'),(28,31,1,'2025-11-18','Datos asegurados');

INSERT OR IGNORE INTO historial_clinico (Historial_ID, Cita_ID) VALUES
  (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10);

INSERT OR IGNORE INTO tratamiento (Tratamiento_ID, Historial_ID, Descripcion) VALUES
  (1,1,'Profilaxis y aplicacion de fluor'),
  (2,2,'Resina simple en pieza 36'),
  (3,3,'Endodoncia Multirradicular'),
  (4,4,'Exodoncia de cordales (3.8,4.8)'),
  (5,5,'Blanqueamiento dental LED'),
  (6,6,'Colocacion de Brakets'),
  (7,7,'Corona de porcelana sobre implante'),
  (8,8,'Raspaje y alisado radicular'),
  (9,9,'Pulpotomia pediatrica'),
  (10,10,'Instalacion de protesis parcial');
"""


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def create_database_and_tables():
    db_name = "odent.db"
    connection = None
    try:
        print(f"Conectando a '{db_name}'...")
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()

        # ── 1. Crear tablas (IF NOT EXISTS) ───────────────────────────────────
        print("Creando tablas (si no existen)...")
        cursor.executescript(SQL_TABLAS)

        # ── 2. ALTER TABLE: añadir / renombrar columnas dinámicamente ─────────
        print("Verificando columnas adicionales...")

        # preguntas_ranking.Activa
        _add_column_if_missing(
            cursor, 'preguntas_ranking', 'Activa',
            'INTEGER NOT NULL DEFAULT 1'
        )

        # cita.Encuesta_Enviada
        _add_column_if_missing(
            cursor, 'cita', 'Encuesta_Enviada',
            'INTEGER NOT NULL DEFAULT 0'
        )

        # ── config_ranking: añadir columna Estado (REQ 2 / archivo 1) ─────────
        # Horas_Envio y Estado_Envio ya existen en la tabla base; Estado es nueva.
        _add_column_if_missing(
            cursor, 'config_ranking', 'Estado',
            'INTEGER NOT NULL DEFAULT 1'
        )
        # Migración Estado_Envio → Estado para BDs existentes:
        # Estado_Envio=1 (activo) → Estado=1; Estado_Envio=0 (inactivo) → Estado=2.
        cursor.execute("PRAGMA table_info(config_ranking)")
        cfg_cols = [row[1] for row in cursor.fetchall()]
        if 'Estado_Envio' in cfg_cols:
            cursor.execute("""
                UPDATE config_ranking
                SET Estado = CASE WHEN Estado_Envio = 0 THEN 2 ELSE 1 END
                WHERE Estado IS NULL OR Estado NOT IN (1, 2)
            """)
            print("  ✚ Estado_Envio migrado a Estado en config_ranking")
        connection.commit()

        # ── diagnostico: renombrar Codigo_CIE10 → Codigo si aún existe ────────
        _rename_column_if_exists(cursor, connection, 'diagnostico', 'Codigo_CIE10', 'Codigo')
        # Si la columna no existía con ningún nombre, crearla como 'Codigo'
        _add_column_if_missing(
            cursor, 'diagnostico', 'Codigo',
            'VARCHAR(10)'
        )

        # ── puntuacion_especialista: Calificacion_Promedio (REQ 3 / archivo 1) ─
        _add_column_if_missing(
            cursor, 'puntuacion_especialista', 'Calificacion_Promedio',
            'REAL'
        )

        connection.commit()

        # ── 3. Migración: Activa=1 en preguntas ya existentes ─────────────────
        cursor.execute(
            "UPDATE preguntas_ranking SET Activa = 1 WHERE Activa IS NULL"
        )
        connection.commit()

        # ── 4. Crear índice sobre agenda (IF NOT EXISTS) ───────────────────────
        print("Verificando índices adicionales...")
        try:
            cursor.executescript(SQL_INDICES)
            connection.commit()
            print("  ✚ índice único 'idx_agenda_unica_activa' verificado en 'agenda'")
        except sqlite3.IntegrityError as idx_err:
            print(
                "  ⚠ No se pudo crear 'idx_agenda_unica_activa': existen filas "
                f"duplicadas activas en 'agenda'. Detalle: {idx_err}"
            )

        # ── 5. Insertar catálogos (INSERT OR IGNORE) ──────────────────────────
        print("Insertando datos de catálogos...")
        cursor.executescript(SQL_CATALOGOS)
        connection.commit()

        # ── 5.1 Especialidades nuevas ─────────────────────────────────────────
        print("Verificando especialidades adicionales...")
        cursor.executescript(SQL_ESPECIALIDADES_NUEVAS)
        connection.commit()

        # ── 6. RESET + RECARGA DE diagnostico con catálogo CIE-10 ────────────
        # Se desactivan temporalmente las FK para borrar las tablas dependientes,
        # se vacía diagnostico y se recarga con los 26 diagnósticos oficiales.
        # historial_diagnostico se repuebla con los nuevos IDs canónicos.
        print("Vaciando tabla 'diagnostico' y tablas dependientes...")
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("DELETE FROM historial_diagnostico")
        cursor.execute("DELETE FROM diagnostico")
        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'diagnostico'"
        )
        cursor.execute("PRAGMA foreign_keys = ON")
        connection.commit()

        print("Insertando catálogo oficial CIE-10 Odontológico (26 diagnósticos)...")
        for codigo, nombre in CATALOGO_CIE10_ODONTOLOGICO:
            cursor.execute(
                "INSERT INTO diagnostico (Codigo, Nombre_Diagnostico) VALUES (?, ?)",
                (codigo, nombre)
            )
        connection.commit()

        # Índice único sobre Codigo ahora que la tabla está limpia
        try:
            cursor.executescript(SQL_INDICE_DIAGNOSTICO)
            connection.commit()
            print("  ✚ índice único 'idx_diagnostico_codigo' verificado en 'diagnostico'")
        except sqlite3.IntegrityError as idx_err:
            print(
                "  ⚠ No se pudo crear 'idx_diagnostico_codigo': "
                f"códigos duplicados detectados. Detalle: {idx_err}"
            )

        # Repoblar historial_diagnostico con los nuevos IDs canónicos (primeros 10)
        print("Reinsertando historial_diagnostico con IDs del catálogo oficial...")
        cursor.execute(
            "SELECT Diagnostico_ID FROM diagnostico ORDER BY Diagnostico_ID LIMIT 10"
        )
        nuevos_ids = [row[0] for row in cursor.fetchall()]
        for historial_id, diagnostico_id in enumerate(nuevos_ids, start=1):
            cursor.execute(
                "INSERT OR IGNORE INTO historial_diagnostico "
                "(Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diagnostico_id)
            )
        connection.commit()

        # ── 7. Insertar usuarios con contraseñas hasheadas ────────────────────
        print("Insertando usuarios con contraseñas hasheadas (solo nuevos)...")
        for u in USUARIOS_DATA:
            (nombres, apellidos, tipo_doc, documento, contrasena_plana,
             fecha_nac, genero_id, correo, telefono, estado_id, rol_id) = u

            cursor.execute(
                "SELECT Usuario_ID FROM usuarios WHERE NumeroDocumento = ?",
                (documento,)
            )
            if cursor.fetchone():
                continue

            contrasena_hash = generate_password_hash(
                contrasena_plana, method='scrypt'
            )
            cursor.execute(
                """INSERT INTO usuarios
                   (Nombres, Apellidos, TipoDoc_ID, NumeroDocumento, Contrasena,
                    FechaNacimiento, Genero_ID, Correo, Telefono, Estado_ID, Rol_ID)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombres, apellidos, tipo_doc, documento, contrasena_hash,
                 fecha_nac, genero_id, correo, telefono, estado_id, rol_id)
            )

        connection.commit()

        # ── 8. Insertar relaciones y datos dependientes ───────────────────────
        print("Insertando relaciones (INSERT OR IGNORE)...")
        cursor.executescript(SQL_RELACIONES)
        connection.commit()

        print(f"\n✔ Base de datos '{db_name}' inicializada/actualizada con éxito.")

    except Error as e:
        print(f"❌ Error durante la inicialización: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
            print("Conexión con SQLite cerrada de forma segura.")


if __name__ == "__main__":
    create_database_and_tables()