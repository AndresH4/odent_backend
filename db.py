# db.py
import sqlite3
import random

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


def get_db_connection():
    """
    Abre una conexión con la base de datos SQLite y la configura.
    Esta función será llamada por app.py cada vez que necesite consultar datos.
    """
    # 1. Nos conectamos al archivo físico
    conexion = sqlite3.connect(DB_FILE)
    
    # 2. Le decimos a SQLite que nos devuelva los resultados como "diccionarios"
    # Esto es crucial para que luego Flask pueda convertirlos a JSON fácilmente
    conexion.row_factory = sqlite3.Row
    
    # 3. ACTIVAR LLAVES FORÁNEAS (¡Muy importante en SQLite!)
    # Si no activas esto, SQLite te dejará crear una cita para un Paciente_ID que no existe.
    conexion.execute("PRAGMA foreign_keys = ON;")

    # 4. Garantizar columna de código de verificación (6 dígitos) en citas
    _asegurar_columna_codigo_cita(conexion)
    
    return conexion