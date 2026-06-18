# =============================================================================
# modulo_eps/tabla_pregunta.py
# CRUD para la tabla preguntas_ranking
# Esquema real (init_db.py):
#   preguntas_ranking (Preguntas_ID INTEGER PK, Texto_Pregunta VARCHAR(150))
# =============================================================================

from db import get_db_connection


def crear_pregunta(texto_pregunta, orden=None, activa=1):
    """
    Registra una nueva pregunta en preguntas_ranking.
    Los parámetros `orden` y `activa` se aceptan por compatibilidad con
    routes.py pero no se persisten (la tabla real no tiene esas columnas).
    Retorna el ID del registro creado (Preguntas_ID).
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "INSERT INTO preguntas_ranking (Texto_Pregunta) VALUES (?)",
            (texto_pregunta,)
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
    Retorna todas las preguntas de preguntas_ranking.
    El parámetro `solo_activas` se acepta por compatibilidad pero no filtra.
    Serializa cada fila como dict con las claves que espera routes.py:
      ID_Pregunta, Texto_Pregunta, Orden, Activa
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Preguntas_ID, Texto_Pregunta FROM preguntas_ranking ORDER BY Preguntas_ID ASC"
        )
        filas = cursor.fetchall()
        return [
            {
                "ID_Pregunta":    fila[0],
                "Texto_Pregunta": fila[1],
                "Orden":          idx + 1,
                "Activa":         1
            }
            for idx, fila in enumerate(filas)
        ]
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


def obtener_pregunta_por_id(pregunta_id):
    """
    Retorna una pregunta específica por su Preguntas_ID.
    Devuelve None si no existe.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Preguntas_ID, Texto_Pregunta FROM preguntas_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )
        fila = cursor.fetchone()
        if fila is None:
            return None
        return {
            "ID_Pregunta":    fila[0],
            "Texto_Pregunta": fila[1],
            "Orden":          None,
            "Activa":         1
        }
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


def actualizar_pregunta(pregunta_id, texto_pregunta, orden=None, activa=1):
    """
    Actualiza el Texto_Pregunta de una pregunta existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "UPDATE preguntas_ranking SET Texto_Pregunta = ? WHERE Preguntas_ID = ?",
            (texto_pregunta, pregunta_id)
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
    Elimina una pregunta por su Preguntas_ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "DELETE FROM preguntas_ranking WHERE Preguntas_ID = ?",
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