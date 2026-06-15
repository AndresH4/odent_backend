# =============================================================================
# modulo_eps/eps.py
# CRUD para la tabla eps
# =============================================================================
 
from db import get_db_connection
 
 
def crear_eps(nombre_eps, tipo_eps_id, nit=None, telefono=None, direccion=None):
    """
    Inserta una nueva EPS en la tabla eps.
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO eps (Nombre_EPS, ID_Tipo_EPS, NIT, Telefono, Direccion)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombre_eps, tipo_eps_id, nit, telefono, direccion)
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
 
 
def obtener_eps():
    """
    Retorna todas las EPS registradas con el nombre de su tipo de EPS.
    Se hace INNER JOIN con tipo_eps para enriquecer la respuesta.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                e.ID_EPS,
                e.Nombre_EPS,
                e.NIT,
                e.Telefono,
                e.Direccion,
                e.ID_Tipo_EPS,
                t.Nombre_Tipo AS Nombre_Tipo_EPS
            FROM eps e
            INNER JOIN tipo_eps t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            ORDER BY e.Nombre_EPS ASC
            """
        )
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
 
 
def obtener_eps_por_id(eps_id):
    """
    Retorna una EPS específica por su ID, incluyendo el nombre de su tipo.
    Devuelve None si no existe.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                e.ID_EPS,
                e.Nombre_EPS,
                e.NIT,
                e.Telefono,
                e.Direccion,
                e.ID_Tipo_EPS,
                t.Nombre_Tipo AS Nombre_Tipo_EPS
            FROM eps e
            INNER JOIN tipo_eps t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            WHERE e.ID_EPS = ?
            """,
            (eps_id,)
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
 
 
def actualizar_eps(eps_id, nombre_eps, tipo_eps_id, nit=None, telefono=None, direccion=None):
    """
    Actualiza los datos de una EPS existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE eps
            SET Nombre_EPS = ?,
                ID_Tipo_EPS = ?,
                NIT = ?,
                Telefono = ?,
                Direccion = ?
            WHERE ID_EPS = ?
            """,
            (nombre_eps, tipo_eps_id, nit, telefono, direccion, eps_id)
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
 
 
def eliminar_eps(eps_id):
    """
    Elimina una EPS por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM eps WHERE ID_EPS = ?",
            (eps_id,)
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
            
def obtener_eps_por_tipo(tipo_eps_id):
    """
    Retorna todas las EPS cuyo ID_Tipo_EPS coincide con el parámetro.
    Se usa para filtrar el selector de EPS en el formulario de aseguramiento
    cuando el usuario elige un Tipo de EPS concreto.
 
    Retorna una lista de dicts con las mismas columnas que obtener_eps().
    Retorna lista vacía [] si no hay EPS para ese tipo (no lanza error).
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                e.ID_EPS,
                e.Nombre_EPS,
                e.NIT,
                e.Telefono,
                e.Direccion,
                e.ID_Tipo_EPS,
                t.Nombre_Tipo AS Nombre_Tipo_EPS
            FROM   eps      e
            INNER JOIN tipo_eps t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            WHERE  e.ID_Tipo_EPS = ?
            ORDER  BY e.Nombre_EPS ASC
            """,
            (tipo_eps_id,)
        )
        columnas = [desc[0] for desc in cursor.description]
        filas    = cursor.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()