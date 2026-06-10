import sqlite3
def eps():
    return {"mensaje": "eps"}

def conectar():
    conn = sqlite3.connect('odent.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =====================================================================
# OPERACIONES CRUD
# =====================================================================


# CREATE (Insertar un nuevo registro)
def crear_eps(nombre, tipoeps_id, regimen_eps_id):
    try:
        conn = conectar()
        cursor = conn.cursor()
        query = """INSERT INTO eps (nombre, tipoeps_id, regimen_eps_id) 
                   VALUES (?, ?, ?)"""
        cursor.execute(query, (nombre, tipoeps_id, regimen_eps_id))
        conn.commit()
        print(f"¡EPS '{nombre}' creada con éxito! ID asignado: {cursor.lastrowid}")
    except sqlite3.IntegrityError as e:
        print(
            f"Error de integridad (verifica que los IDs de tipo y régimen existan): {e}"
        )
    finally:
        conn.close()


# READ (Leer/Consultar registros)
def obtener_todas_las_eps():
    """Devuelve todas las EPS registradas."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eps")
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def obtener_eps_por_id(eps_id):
    """Busca y devuelve una EPS específica por su ID."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eps WHERE id = ?", (eps_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado


# UPDATE (Actualizar un registro existente)
def actualizar_eps(eps_id, nuevo_nombre, nuevo_tipo_id, nuevo_regimen_id):
    """Actualiza los datos de una EPS existente mediante su ID."""
    try:
        conn = conectar()
        cursor = conn.cursor()
        query = """UPDATE eps 
                   SET nombre = ?, tipoeps_id = ?, regimen_eps_id = ? 
                   WHERE id = ?"""
        cursor.execute(
            query, (nuevo_nombre, nuevo_tipo_id, nuevo_regimen_id, eps_id)
        )
        conn.commit()

        if cursor.rowcount > 0:
            print(f"¡EPS con ID {eps_id} actualizada correctamente!")
        else:
            print(f"No se encontró ninguna EPS con el ID {eps_id}.")
    except sqlite3.IntegrityError as e:
        print(f"Error al actualizar (violación de llave foránea): {e}")
    finally:
        conn.close()

# Eliminar 
def eliminar_eps(eps_id):
    """Elimina una EPS de la base de datos por su ID."""
    conn = conectar()
    cursor = conn.cursor()
    query = "DELETE FROM eps WHERE id = ?"
    cursor.execute(query, (eps_id,))
    conn.commit()

    if cursor.rowcount > 0:
        print(f"¡EPS con ID {eps_id} eliminada correctamente!")
    else:
        print(f"No se encontró ninguna EPS con el ID {eps_id}.")
    conn.close()
