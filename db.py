# =============================================================================
# db.py
# VERSIÓN VERIFICADA — se preserva 100% la lógica original del usuario.
# Único cambio: se añade `verificar_conexion_db()` como utilidad de
# diagnóstico OPCIONAL (no se ejecuta automáticamente, no cambia el
# comportamiento de get_db_connection()).
# =============================================================================

import sqlite3
import random
import os

# Definimos el nombre del archivo de la base de datos que creó init_db.py
DB_FILE = 'odent.db'


def _asegurar_columna_codigo_cita(conexion):
    """
    Garantiza que la tabla 'cita' tenga la columna Codigo_Verificacion
    (código de 6 dígitos usado para verificar la cita en clínica).
    No destructivo: solo añade la columna si falta y genera códigos
    para citas que aún no lo tengan asignado.
    """
    cur = conexion.cursor()
    cur.execute("PRAGMA table_info(cita)")
    columnas = [fila[1] for fila in cur.fetchall()]
    if 'Codigo_Verificacion' not in columnas:
        try:
            cur.execute("ALTER TABLE cita ADD COLUMN Codigo_Verificacion VARCHAR(6)")
            conexion.commit()
        except Exception:
            pass

    cur.execute(
        "SELECT Cita_ID FROM cita WHERE Codigo_Verificacion IS NULL OR Codigo_Verificacion = ''"
    )
    pendientes = cur.fetchall()
    if pendientes:
        for fila in pendientes:
            nuevo_codigo = str(random.randint(100000, 999999))
            cur.execute(
                "UPDATE cita SET Codigo_Verificacion = ? WHERE Cita_ID = ?",
                (nuevo_codigo, fila['Cita_ID'])
            )
        conexion.commit()


def _asegurar_config_ranking(conexion):
    """
    Garantiza que la tabla config_ranking exista y tenga exactamente una fila
    de configuración (Config_ID = 1, Estado = 1).

    Estrategia no destructiva:
      1. Crea la tabla si no existe.
      2. Añade la columna Estado si falta (migraciones de BDs antiguas).
      3. Inserta la fila semilla solo si no hay ninguna fila todavía.

    Esta función nunca modifica una fila ya existente, por lo que es seguro
    llamarla en cada conexión sin riesgo de pisar cambios hechos por el admin.

    NOTA: esta función es la que resuelve el "fallo #1" (tabla/fila vacía)
    de forma automática en cada conexión — config_ranking.py YA NO necesita
    duplicar esta lógica de creación/migración, solo debe apoyarse en que
    la fila Config_ID=1 siempre existirá al llegar aquí.
    """
    cur = conexion.cursor()

    # 1. Crear tabla si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_ranking (
            Config_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Estado    INTEGER NOT NULL DEFAULT 1
        )
    """)

    # 2. Añadir columna Estado si falta (bases de datos antiguas)
    cur.execute("PRAGMA table_info(config_ranking)")
    columnas = [fila[1] for fila in cur.fetchall()]
    if 'Estado' not in columnas:
        cur.execute("ALTER TABLE config_ranking ADD COLUMN Estado INTEGER NOT NULL DEFAULT 1")

    # 3. Insertar fila semilla únicamente si la tabla está vacía
    cur.execute("SELECT COUNT(*) FROM config_ranking")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO config_ranking (Config_ID, Estado) VALUES (1, 1)"
        )

    conexion.commit()


def get_db_connection():
    """
    Abre una conexión con la base de datos SQLite y la configura.
    Esta función será llamada por app.py cada vez que necesite consultar datos.
    """
    # 1. Conectar al archivo físico
    conexion = sqlite3.connect(DB_FILE)

    # 2. Resultados como diccionarios (indispensable para jsonify)
    conexion.row_factory = sqlite3.Row

    # 3. Activar llaves foráneas (SQLite las ignora si no se activan explícitamente)
    conexion.execute("PRAGMA foreign_keys = ON;")

    # 4. Garantizar columna de código de verificación (6 dígitos) en citas
    _asegurar_columna_codigo_cita(conexion)

    # 5. Garantizar tabla y fila semilla de config_ranking
    _asegurar_config_ranking(conexion)

    return conexion


# ---------------------------------------------------------------------------
# UTILIDAD DE DIAGNÓSTICO (opcional, no se invoca automáticamente)
# ---------------------------------------------------------------------------
def verificar_conexion_db():
    """
    Imprime la ruta absoluta real que SQLite está usando para DB_FILE y
    confirma si el archivo existe. Útil para descartar que Flask esté
    leyendo/escribiendo en un archivo distinto según el directorio de
    trabajo desde el que se lanza el proceso (gunicorn, flask run, etc).

    Uso manual:
        >>> from db import verificar_conexion_db
        >>> verificar_conexion_db()
    """
    ruta_absoluta = os.path.abspath(DB_FILE)
    print(f"[db] DB_FILE               : {DB_FILE}")
    print(f"[db] Ruta absoluta resuelta: {ruta_absoluta}")
    print(f"[db] ¿Archivo existe?      : {os.path.exists(ruta_absoluta)}")

    con = get_db_connection()
    cur = con.cursor()
    cur.execute("PRAGMA database_list")
    for fila in cur.fetchall():
        print(f"[db] PRAGMA database_list -> {dict(fila)}")

    cur.execute("SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = 1")
    fila_cfg = cur.fetchone()
    print(f"[db] config_ranking (Config_ID=1) -> {dict(fila_cfg) if fila_cfg else None}")

    con.close()


if __name__ == "__main__":
    verificar_conexion_db()