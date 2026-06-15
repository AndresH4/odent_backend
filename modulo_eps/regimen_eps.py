# =============================================================================
# modulo_eps/regimen_eps.py
# CRUD para la tabla regimen_eps
# =============================================================================
 
from db import get_db_connection
 
 
def crear_regimen(nombre_regimen):
    """
    Inserta un nuevo régimen EPS (ej. Contributivo, Subsidiado).
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO regimen_eps (Nombre_Regimen) VALUES (?)",
            (nombre_regimen,)
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
 
 
def obtener_regimenes():
    """
    Retorna todos los regímenes EPS registrados.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM regimen_eps ORDER BY Nombre_Regimen ASC")
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
 
 
def obtener_regimen_por_id(regimen_id):
    """
    Retorna un régimen EPS específico por su ID.
    Devuelve None si no existe.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT * FROM regimen_eps WHERE ID_Regimen_EPS = ?",
            (regimen_id,)
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
 
 
def actualizar_regimen(regimen_id, nombre_regimen):
    """
    Actualiza el nombre de un régimen EPS existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE regimen_eps SET Nombre_Regimen = ? WHERE ID_Regimen_EPS = ?",
            (nombre_regimen, regimen_id)
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
 
 
def eliminar_regimen(regimen_id):
    """
    Elimina un régimen EPS por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM regimen_eps WHERE ID_Regimen_EPS = ?",
            (regimen_id,)
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