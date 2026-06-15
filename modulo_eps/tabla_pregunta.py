# =============================================================================
# modulo_eps/tabla_pregunta.py
# CRUD para la tabla tabla_pregunta
# =============================================================================
 
from db import get_db_connection
 
 
def crear_pregunta(texto_pregunta, orden=None, activa=1):
    """
    Registra una nueva pregunta del formulario de aseguramiento/historia.
    Parámetros:
      - texto_pregunta : Texto completo de la pregunta.
      - orden          : Posición de la pregunta dentro del formulario (opcional).
      - activa         : 1 = activa, 0 = inactiva (por defecto 1).
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO tabla_pregunta (Texto_Pregunta, Orden, Activa)
            VALUES (?, ?, ?)
            """,
            (texto_pregunta, orden, activa)
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
 
 
def obtener_preguntas(solo_activas=False):
    """
    Retorna todas las preguntas ordenadas por su campo Orden.
    Si solo_activas=True, filtra únicamente las que estén activas (Activa = 1).
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        if solo_activas:
            cursor.execute(
                """
                SELECT * FROM tabla_pregunta
                WHERE Activa = 1
                ORDER BY Orden ASC, ID_Pregunta ASC
                """
            )
        else:
            cursor.execute(
                "SELECT * FROM tabla_pregunta ORDER BY Orden ASC, ID_Pregunta ASC"
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
 
 
def obtener_pregunta_por_id(pregunta_id):
    """
    Retorna una pregunta específica por su ID.
    Devuelve None si no existe.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT * FROM tabla_pregunta WHERE ID_Pregunta = ?",
            (pregunta_id,)
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
 
 
def actualizar_pregunta(pregunta_id, texto_pregunta, orden=None, activa=1):
    """
    Actualiza el texto, orden y estado de activación de una pregunta.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE tabla_pregunta
            SET Texto_Pregunta = ?,
                Orden          = ?,
                Activa         = ?
            WHERE ID_Pregunta = ?
            """,
            (texto_pregunta, orden, activa, pregunta_id)
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
 
 
def eliminar_pregunta(pregunta_id):
    """
    Elimina una pregunta por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM tabla_pregunta WHERE ID_Pregunta = ?",
            (pregunta_id,)
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
 