# =============================================================================
# modulo_eps/tabla_respuesta.py
# CRUD para la tabla tabla_respuesta — JOINs con tabla_pregunta y paciente
# =============================================================================
 
from db import get_db_connection
 
 
def crear_respuesta(pregunta_id, paciente_id, texto_respuesta):
    """
    Registra la respuesta de un paciente a una pregunta del formulario.
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO tabla_respuesta (ID_Pregunta, ID_Paciente, Texto_Respuesta)
            VALUES (?, ?, ?)
            """,
            (pregunta_id, paciente_id, texto_respuesta)
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
 
 
def obtener_respuestas():
    """
    Retorna todas las respuestas enriquecidas con:
      - Texto de la pregunta (JOIN con tabla_pregunta)
      - Nombre completo del paciente (JOIN con paciente y usuarios)
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                r.ID_Respuesta,
                r.Texto_Respuesta,
                r.ID_Pregunta,
                p.Texto_Pregunta,
                p.Orden           AS Orden_Pregunta,
                r.ID_Paciente,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Paciente
            FROM tabla_respuesta r
            INNER JOIN tabla_pregunta p ON r.ID_Pregunta = p.ID_Pregunta
            INNER JOIN paciente       pa ON r.ID_Paciente = pa.ID_Paciente
            INNER JOIN usuarios       u  ON pa.ID_Usuario = u.ID_Usuario
            ORDER BY r.ID_Paciente ASC, p.Orden ASC
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
 
 
def obtener_respuesta_por_id(respuesta_id):
    """
    Retorna una respuesta específica por su ID, con los JOINs enriquecidos.
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
                r.ID_Respuesta,
                r.Texto_Respuesta,
                r.ID_Pregunta,
                p.Texto_Pregunta,
                p.Orden           AS Orden_Pregunta,
                r.ID_Paciente,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Paciente
            FROM tabla_respuesta r
            INNER JOIN tabla_pregunta p ON r.ID_Pregunta  = p.ID_Pregunta
            INNER JOIN paciente       pa ON r.ID_Paciente = pa.ID_Paciente
            INNER JOIN usuarios       u  ON pa.ID_Usuario = u.ID_Usuario
            WHERE r.ID_Respuesta = ?
            """,
            (respuesta_id,)
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
 
 
def obtener_respuestas_por_paciente(paciente_id):
    """
    Reporte consolidado: retorna todas las preguntas con sus respuestas
    para un paciente específico, ordenadas por el campo Orden de la pregunta.
    Incluye el nombre completo del paciente en cada fila.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                r.ID_Respuesta,
                r.ID_Paciente,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Paciente,
                p.ID_Pregunta,
                p.Texto_Pregunta,
                p.Orden                          AS Orden_Pregunta,
                r.Texto_Respuesta
            FROM tabla_respuesta r
            INNER JOIN tabla_pregunta p ON r.ID_Pregunta  = p.ID_Pregunta
            INNER JOIN paciente       pa ON r.ID_Paciente = pa.ID_Paciente
            INNER JOIN usuarios       u  ON pa.ID_Usuario = u.ID_Usuario
            WHERE r.ID_Paciente = ?
            ORDER BY p.Orden ASC, p.ID_Pregunta ASC
            """,
            (paciente_id,)
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
 
 
def actualizar_respuesta(respuesta_id, texto_respuesta):
    """
    Actualiza el texto de una respuesta existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE tabla_respuesta
            SET Texto_Respuesta = ?
            WHERE ID_Respuesta = ?
            """,
            (texto_respuesta, respuesta_id)
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
 
 
def eliminar_respuesta(respuesta_id):
    """
    Elimina una respuesta por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM tabla_respuesta WHERE ID_Respuesta = ?",
            (respuesta_id,)
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