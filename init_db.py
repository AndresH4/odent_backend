"""
init_db.py — Stylo Dental
==========================
Script de inicialización de la base de datos SQLite.

SEGURO PARA BD EXISTENTE:
  - CREATE TABLE IF NOT EXISTS  → nunca destruye datos existentes.
  - INSERT OR IGNORE             → evita duplicados en catálogos.
  - ALTER TABLE dinámico         → añade columnas faltantes sin recrear tablas.
  - CREATE INDEX IF NOT EXISTS   → añade restricciones nuevas sin recrear tablas.
  - Sin DROP TABLE en ningún caso.
"""

import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDAD: añadir columna si no existe
# ─────────────────────────────────────────────────────────────────────────────

def _add_column_if_missing(cursor, table: str, column: str, col_def: str):
    """Ejecuta ALTER TABLE … ADD COLUMN solo si la columna no existe ya."""
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    if column not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        print(f"  ✚ columna '{column}' añadida a '{table}'")


# ─────────────────────────────────────────────────────────────────────────────
# DDL: tablas base (todas con IF NOT EXISTS)
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

-- Tabla actualizada: tipo_afiliacion_eps (reemplaza tipo_eps en la nueva versión)
CREATE TABLE IF NOT EXISTS tipo_afiliacion_eps (
  TipoEPS_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Tipo VARCHAR(50) NOT NULL
);

-- Alias legacy por si alguna parte del código aún referencia tipo_eps
-- Se crea igual para compatibilidad, pero la FK en afiliacion apunta a tipo_afiliacion_eps
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
  -- columna 'Activa' se añade dinámicamente más abajo si falta
);

CREATE TABLE IF NOT EXISTS accion_aseguramiento (
  Accion_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Accion VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnostico (
  Diagnostico_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
  Nombre_Diagnostico VARCHAR(100) NOT NULL
);

-- ── CONFIGURACIÓN GLOBAL DE RANKING ─────────────────────────────────────────
-- Una sola fila (Config_ID = 1) almacena los parámetros que el administrador
-- gestiona desde la vista de Configuración de Encuesta:
--   Horas_Envio  : retraso en horas desde la finalización de la consulta
--   Estado_Envio : 1 = ACTIVO (se envían correos), 0 = INACTIVO (kill-switch)
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
  -- TipoEPS_ID referencia tipo_afiliacion_eps en la nueva versión;
  -- se omite FK explícita aquí para compatibilidad con ambas tablas.
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
  -- Encuesta_Enviada: 0=no enviada, 1=enviada
  -- Se añade dinámicamente si la tabla ya existe sin esta columna.
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

CREATE TABLE IF NOT EXISTS puntuacion_especialista (
  Puntuacion_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
  Especialista_ID INT NOT NULL,
  Respuesta_ID    INT NOT NULL,
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
# DDL: índices (todos con IF NOT EXISTS, no destructivos)
# ─────────────────────────────────────────────────────────────────────────────

# REQ 4 — VALIDACIÓN ESTRICTA DE DISPONIBILIDADES DUPLICADAS.
# Índice UNIQUE parcial: un mismo especialista no puede tener dos filas en
# 'agenda' con la misma Fecha + Hora_Inicio mientras el bloque esté activo
# (EstadoAgenda_ID 1=Disponible o 2=Ocupado). Slots Cancelados (3) o
# Cumplidos (4) no participan en la restricción, de modo que el historial
# nunca se ve afectado y un horario liberado puede reutilizarse sin choques.
# Esto es la defensa de última línea a nivel de BD; el backend en
# modulo_citas/routes.py ya valida esto explícitamente antes de insertar,
# pero el índice evita condiciones de carrera entre solicitudes concurrentes.
SQL_INDICES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_agenda_unica_activa
ON agenda (Especialista_ID, Fecha, Hora_Inicio)
WHERE EstadoAgenda_ID IN (1, 2);
"""

# ─────────────────────────────────────────────────────────────────────────────
# DML: catálogos con INSERT OR IGNORE (nunca duplica)
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
  (1, 'Endodoncia'),
  (2, 'Odontopediatria'),
  (3, 'Odontologia General'),
  (4, 'Cirugia Oral'),
  (5, 'Ortodoncia'),
  (6, 'Control brackets');

INSERT OR IGNORE INTO regimen_eps (Regimen_ID, Descripcion) VALUES
  (1, 'Contributivo'), (2, 'Subsidiado');

-- tipo_afiliacion_eps (nueva tabla)
INSERT OR IGNORE INTO tipo_afiliacion_eps (TipoEPS_ID, Nombre_Tipo) VALUES
  (1, 'Cotizante'), (2, 'Beneficiario');

-- tipo_eps (tabla legacy — mismos datos para compatibilidad)
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

-- 1=Disponible, 2=Ocupado, 3=Cancelado, 4=Cumplida
INSERT OR IGNORE INTO estado_agenda (EstadoAgenda_ID, Nombre_Estado) VALUES
  (1, 'Disponible'), (2, 'Ocupado'), (3, 'Cancelado'), (4, 'Cumplida');

INSERT OR IGNORE INTO accion_aseguramiento (Accion_ID, Nombre_Accion) VALUES
  (1, 'Asegurar'), (2, 'Actualizar'), (3, 'Eliminar');

INSERT OR IGNORE INTO estado_multa (EstadoMulta_ID, Nombre_Estado) VALUES
  (1, 'Pendiente'), (2, 'Pagada');

INSERT OR IGNORE INTO preguntas_ranking (Preguntas_ID, Texto_Pregunta) VALUES
  (1, '¿El odontologo fue amable durante la consulta?'),
  (2, '¿Te explico claramente el diagnostico?');

INSERT OR IGNORE INTO diagnostico (Diagnostico_ID, Nombre_Diagnostico) VALUES
  (1,  'Caries Dental Profunda'),
  (2,  'Gingivitis Cronica'),
  (3,  'Periodontitis Avanzada'),
  (4,  'Absceso Periapical'),
  (5,  'Tercer Molar Impactado'),
  (6,  'Pulpite Irreversible'),
  (7,  'Maloclusion Clase II'),
  (8,  'Bruxismo Severo'),
  (9,  'Evolucion de Tratamiento General'),
  (10, 'Consulta de Control Preventivo');

-- Fila única de configuración de ranking (solo si no existe)
INSERT OR IGNORE INTO config_ranking (Config_ID, Horas_Envio, Estado_Envio)
  VALUES (1, 2, 1);
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

INSERT OR IGNORE INTO puntuacion_especialista (Puntuacion_ID, Especialista_ID, Respuesta_ID) VALUES
  (1,1,1),(2,2,2);

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

INSERT OR IGNORE INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES
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

        # ── 2. ALTER TABLE: añadir columnas nuevas dinámicamente ──────────────
        print("Verificando columnas adicionales...")

        # preguntas_ranking.Activa (nueva versión)
        _add_column_if_missing(
            cursor, 'preguntas_ranking', 'Activa',
            'INTEGER NOT NULL DEFAULT 1'
        )

        # cita.Encuesta_Enviada (nueva versión)
        _add_column_if_missing(
            cursor, 'cita', 'Encuesta_Enviada',
            'INTEGER NOT NULL DEFAULT 0'
        )

        connection.commit()

        # ── 3. Actualizar Activa=1 en preguntas ya existentes (migración) ─────
        cursor.execute(
            "UPDATE preguntas_ranking SET Activa = 1 WHERE Activa IS NULL"
        )
        connection.commit()

        # ── 4. Crear índices (IF NOT EXISTS) ───────────────────────────────────
        # REQ 4: si la BD ya tenía filas duplicadas activas antes de este
        # cambio, CREATE UNIQUE INDEX fallará con "UNIQUE constraint failed".
        # En ese caso se informa por consola sin abortar el resto del script,
        # para que el operador pueda limpiar manualmente esas filas legacy.
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

        # ── 6. Insertar usuarios con contraseñas hasheadas ────────────────────
        print("Insertando usuarios con contraseñas hasheadas (solo nuevos)...")
        for u in USUARIOS_DATA:
            (nombres, apellidos, tipo_doc, documento, contrasena_plana,
             fecha_nac, genero_id, correo, telefono, estado_id, rol_id) = u

            # Verificar si ya existe el usuario (por documento)
            cursor.execute(
                "SELECT Usuario_ID FROM usuarios WHERE NumeroDocumento = ?",
                (documento,)
            )
            if cursor.fetchone():
                continue  # ya existe, no duplicar

            contrasena_hash = generate_password_hash(contrasena_plana, method='scrypt')
            cursor.execute(
                """INSERT INTO usuarios
                   (Nombres, Apellidos, TipoDoc_ID, NumeroDocumento, Contrasena,
                    FechaNacimiento, Genero_ID, Correo, Telefono, Estado_ID, Rol_ID)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombres, apellidos, tipo_doc, documento, contrasena_hash,
                 fecha_nac, genero_id, correo, telefono, estado_id, rol_id)
            )

        connection.commit()

        # ── 7. Insertar relaciones y datos dependientes ───────────────────────
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