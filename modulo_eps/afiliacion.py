# =============================================================================
# modulo_eps/afiliacion.py
# CRUD para la tabla afiliacion — incluye JOINs con usuarios, eps y tipo_eps
# =============================================================================
 
from db import get_db_connection
 
 
def crear_afiliacion(usuario_id, eps_id, regimen_eps_id, fecha_afiliacion,
                     numero_afiliado=None, estado=None):
    """
    Registra una nueva afiliación de un usuario a una EPS.
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO afiliacion
                (ID_Usuario, ID_EPS, ID_Regimen_EPS, Fecha_Afiliacion,
                 Numero_Afiliado, Estado)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (usuario_id, eps_id, regimen_eps_id, fecha_afiliacion,
             numero_afiliado, estado)
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
 
 
def obtener_afiliaciones():
    """
    Retorna todas las afiliaciones enriquecidas con:
      - Nombre completo del usuario (Nombres || ' ' || Apellidos)
      - Nombre de la EPS
      - Tipo de EPS
      - Nombre del régimen
    Usa INNER JOIN con usuarios, eps, tipo_eps y regimen_eps.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                a.ID_Afiliacion,
                a.Numero_Afiliado,
                a.Fecha_Afiliacion,
                a.Estado,
                a.ID_Usuario,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo_Usuario,
                u.Correo                         AS Correo_Usuario,
                a.ID_EPS,
                e.Nombre_EPS,
                e.ID_Tipo_EPS,
                t.Nombre_Tipo                    AS Tipo_EPS,
                a.ID_Regimen_EPS,
                r.Nombre_Regimen                 AS Regimen
            FROM afiliacion a
            INNER JOIN usuarios   u ON a.ID_Usuario     = u.ID_Usuario
            INNER JOIN eps        e ON a.ID_EPS          = e.ID_EPS
            INNER JOIN tipo_eps   t ON e.ID_Tipo_EPS     = t.ID_Tipo_EPS
            INNER JOIN regimen_eps r ON a.ID_Regimen_EPS = r.ID_Regimen_EPS
            ORDER BY a.Fecha_Afiliacion DESC
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
 
 
def obtener_afiliacion_por_id(afiliacion_id):
    """
    Retorna una afiliación específica por su ID, enriquecida con JOINs.
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
                a.ID_Afiliacion,
                a.Numero_Afiliado,
                a.Fecha_Afiliacion,
                a.Estado,
                a.ID_Usuario,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo_Usuario,
                u.Correo                         AS Correo_Usuario,
                a.ID_EPS,
                e.Nombre_EPS,
                e.ID_Tipo_EPS,
                t.Nombre_Tipo                    AS Tipo_EPS,
                a.ID_Regimen_EPS,
                r.Nombre_Regimen                 AS Regimen
            FROM afiliacion a
            INNER JOIN usuarios    u ON a.ID_Usuario     = u.ID_Usuario
            INNER JOIN eps         e ON a.ID_EPS          = e.ID_EPS
            INNER JOIN tipo_eps    t ON e.ID_Tipo_EPS     = t.ID_Tipo_EPS
            INNER JOIN regimen_eps r ON a.ID_Regimen_EPS = r.ID_Regimen_EPS
            WHERE a.ID_Afiliacion = ?
            """,
            (afiliacion_id,)
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
 
 
def actualizar_afiliacion(afiliacion_id, eps_id, regimen_eps_id,
                          fecha_afiliacion, numero_afiliado=None, estado=None):
    """
    Actualiza los campos de una afiliación existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE afiliacion
            SET ID_EPS          = ?,
                ID_Regimen_EPS  = ?,
                Fecha_Afiliacion = ?,
                Numero_Afiliado  = ?,
                Estado           = ?
            WHERE ID_Afiliacion = ?
            """,
            (eps_id, regimen_eps_id, fecha_afiliacion,
             numero_afiliado, estado, afiliacion_id)
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
 
 
def eliminar_afiliacion(afiliacion_id):
    """
    Elimina una afiliación por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM afiliacion WHERE ID_Afiliacion = ?",
            (afiliacion_id,)
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
 
 
# ---------------------------------------------------------------------------
# Consulta de reporte: conteo de afiliados por EPS
# ---------------------------------------------------------------------------
 
def reporte_afiliados_por_eps():
    """
    Retorna un conteo de afiliaciones agrupado por EPS.
    Cada fila incluye el nombre de la EPS y el total de afiliados.
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
                COUNT(a.ID_Afiliacion) AS Total_Afiliados
            FROM eps e
            LEFT JOIN afiliacion a ON e.ID_EPS = a.ID_EPS
            GROUP BY e.ID_EPS, e.Nombre_EPS
            ORDER BY Total_Afiliados DESC
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