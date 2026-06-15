# =============================================================================
# modulo_eps/tipo_eps.py
# CRUD para la tabla tipo_eps
# =============================================================================
 
from db import get_db_connection
 
 
def crear_tipo_eps(nombre_tipo):
    """
    Inserta un nuevo tipo de EPS en la tabla tipo_eps.
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO tipo_eps (Nombre_Tipo) VALUES (?)",
            (nombre_tipo,)
        )
        conexion.commit()
        return cursor.lastrowid
    except Exception as e:
        if conexion:
            conexion.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
 
 
def obtener_tipos_eps():
    """
    Retorna todos los tipos de EPS registrados.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM tipo_eps ORDER BY Nombre_Tipo ASC")
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
 
 
def obtener_tipo_eps_por_id(tipo_eps_id):
    """
    Retorna un tipo de EPS específico por su ID.
    Devuelve None si no existe.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT * FROM tipo_eps WHERE ID_Tipo_EPS = ?",
            (tipo_eps_id,)
        )
        columnas = [desc[0] for desc in cursor.description]
        fila = cursor.fetchone()
        if fila is None:
            return None
        return dict(zip(columnas, fila))
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
 
 
def actualizar_tipo_eps(tipo_eps_id, nombre_tipo):
    """
    Actualiza el nombre de un tipo de EPS existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE tipo_eps SET Nombre_Tipo = ? WHERE ID_Tipo_EPS = ?",
            (nombre_tipo, tipo_eps_id)
        )
        conexion.commit()
        return cursor.rowcount > 0
    except Exception as e:
        if conexion:
            conexion.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
 
 
def eliminar_tipo_eps(tipo_eps_id):
    """
    Elimina un tipo de EPS por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM tipo_eps WHERE ID_Tipo_EPS = ?",
            (tipo_eps_id,)
        )
        conexion.commit()
        return cursor.rowcount > 0
    except Exception as e:
        if conexion:
            conexion.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
 