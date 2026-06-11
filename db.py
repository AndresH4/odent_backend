import sqlite3

# Definimos el nombre del archivo de la base de datos que creó init_db.py
DB_FILE = 'odent.db'

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
    
    return conexion