# =============================================================================
# modulo_eps/afiliacion.py
# Adaptado al esquema real: afiliacion(Afiliacion_ID, Usuario_ID, EPS_ID,
#                                       TipoEPS_ID, Fecha_Afiliacion)
# TipoEPS_ID → FK a tipo_eps (Cotizante / Beneficiario)
# =============================================================================

from db import get_db_connection


def crear_afiliacion(usuario_id, eps_id, tipo_eps_id, fecha_afiliacion,
                     numero_afiliado=None, estado=None):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO afiliacion
                (Usuario_ID, EPS_ID, TipoEPS_ID, Fecha_Afiliacion)
            VALUES (?, ?, ?, ?)
            """,
            (usuario_id, eps_id, tipo_eps_id, fecha_afiliacion)
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
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                a.Afiliacion_ID,
                a.Fecha_Afiliacion,
                a.Usuario_ID,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo_Usuario,
                u.Correo                         AS Correo_Usuario,
                a.EPS_ID,
                e.Nombre_EPS,
                e.Regimen_ID,
                r.Descripcion                    AS Nombre_Regimen,
                a.TipoEPS_ID,
                t.Nombre_Tipo                    AS Tipo_EPS
            FROM afiliacion a
            INNER JOIN usuarios   u ON a.Usuario_ID  = u.Usuario_ID
            INNER JOIN eps        e ON a.EPS_ID       = e.EPS_ID
            LEFT  JOIN regimen_eps r ON e.Regimen_ID  = r.Regimen_ID
            INNER JOIN tipo_eps   t ON a.TipoEPS_ID  = t.TipoEPS_ID
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
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                a.Afiliacion_ID,
                a.Fecha_Afiliacion,
                a.Usuario_ID,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo_Usuario,
                u.Correo                         AS Correo_Usuario,
                a.EPS_ID,
                e.Nombre_EPS,
                e.Regimen_ID,
                r.Descripcion                    AS Nombre_Regimen,
                a.TipoEPS_ID,
                t.Nombre_Tipo                    AS Tipo_EPS
            FROM afiliacion a
            INNER JOIN usuarios   u ON a.Usuario_ID  = u.Usuario_ID
            INNER JOIN eps        e ON a.EPS_ID       = e.EPS_ID
            LEFT  JOIN regimen_eps r ON e.Regimen_ID  = r.Regimen_ID
            INNER JOIN tipo_eps   t ON a.TipoEPS_ID  = t.TipoEPS_ID
            WHERE a.Afiliacion_ID = ?
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


def actualizar_afiliacion(afiliacion_id, eps_id, tipo_eps_id,
                          fecha_afiliacion, numero_afiliado=None, estado=None):
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE afiliacion
            SET EPS_ID           = ?,
                TipoEPS_ID       = ?,
                Fecha_Afiliacion = ?
            WHERE Afiliacion_ID = ?
            """,
            (eps_id, tipo_eps_id, fecha_afiliacion, afiliacion_id)
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
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM afiliacion WHERE Afiliacion_ID = ?",
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


def reporte_afiliados_por_eps():
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                e.EPS_ID,
                e.Nombre_EPS,
                COUNT(a.Afiliacion_ID) AS Total_Afiliados
            FROM eps e
            LEFT JOIN afiliacion a ON e.EPS_ID = a.EPS_ID
            GROUP BY e.EPS_ID, e.Nombre_EPS
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