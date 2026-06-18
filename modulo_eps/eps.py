# =============================================================================
# modulo_eps/eps.py
# =============================================================================

from db import get_db_connection


def crear_eps(nombre_eps, tipo_eps_id, nit=None, telefono=None, direccion=None):
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
                t.Nombre_Tipo AS Nombre_Tipo_EPS,
                e.Regimen_ID,
                r.Descripcion AS Nombre_Regimen
            FROM eps e
            INNER JOIN tipo_eps   t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            LEFT  JOIN regimen_eps r ON e.Regimen_ID  = r.Regimen_ID
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
                t.Nombre_Tipo AS Nombre_Tipo_EPS,
                e.Regimen_ID,
                r.Descripcion AS Nombre_Regimen
            FROM eps e
            INNER JOIN tipo_eps   t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            LEFT  JOIN regimen_eps r ON e.Regimen_ID  = r.Regimen_ID
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


def obtener_eps_por_regimen(regimen_id):
    """
    Retorna las EPS cuyo Regimen_ID coincide.
    Usado para el cascading dropdown Régimen → EPS.
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
                t.Nombre_Tipo AS Nombre_Tipo_EPS,
                e.Regimen_ID,
                r.Descripcion AS Nombre_Regimen
            FROM eps e
            INNER JOIN tipo_eps   t ON e.ID_Tipo_EPS = t.ID_Tipo_EPS
            LEFT  JOIN regimen_eps r ON e.Regimen_ID  = r.Regimen_ID
            WHERE e.Regimen_ID = ?
            ORDER BY e.Nombre_EPS ASC
            """,
            (regimen_id,)
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


def actualizar_eps(eps_id, nombre_eps, tipo_eps_id, nit=None, telefono=None, direccion=None):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE eps
            SET Nombre_EPS  = ?,
                ID_Tipo_EPS = ?,
                NIT         = ?,
                Telefono    = ?,
                Direccion   = ?
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
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM eps WHERE ID_EPS = ?", (eps_id,))
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