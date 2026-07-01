# =============================================================================
# modulo_eps/tabla_pregunta.py
# CRUD para la tabla preguntas_ranking
#
# Esquema actualizado (init_db.py):
#   preguntas_ranking (
#     Preguntas_ID   INTEGER PK,
#     Texto_Pregunta VARCHAR(150) NOT NULL,
#     Activa         INTEGER NOT NULL DEFAULT 1   ← 1=activa, 0=inactiva
#   )
#
# REQ 7: Cualquier operación CRUD realizada por el administrador actualiza
# instantáneamente la BD. El paciente siempre consulta solo las preguntas
# Activa=1 a través del endpoint GET /api/pregunta?activas=true.
#
# FIX eliminación: antes el DELETE se interrumpía por violación de
# integridad referencial (la pregunta tenía respuestas asociadas en
# respuesta_ranking). Ahora eliminar_pregunta() borra primero las
# respuestas dependientes dentro de la misma transacción, y solo
# confirma éxito si la fila de preguntas_ranking fue realmente
# eliminada (rowcount > 0).
# =============================================================================

from db import get_db_connection


def crear_pregunta(texto_pregunta, orden=None, activa=1):
    """
    Registra una nueva pregunta en preguntas_ranking con su estado Activa.
    El parámetro `orden` se acepta por compatibilidad pero no se persiste
    (la tabla ordena por Preguntas_ID).
    Retorna el ID del registro creado (Preguntas_ID).
    """
    activa_val = 1 if activa else 0

    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "INSERT INTO preguntas_ranking (Texto_Pregunta, Activa) VALUES (?, ?)",
            (texto_pregunta, activa_val)
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
    Retorna preguntas de preguntas_ranking.
    Si solo_activas=True devuelve únicamente las que tienen Activa=1,
    lo que garantiza que la encuesta del paciente refleje en tiempo real
    cualquier cambio CRUD del administrador (REQ 7).

    Serializa cada fila con las claves que espera routes.py y ranking.js:
      ID_Pregunta, Texto_Pregunta, Orden, Activa
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()

        if solo_activas:
            cursor.execute(
                """SELECT Preguntas_ID, Texto_Pregunta, Activa
                   FROM preguntas_ranking
                   WHERE Activa = 1
                   ORDER BY Preguntas_ID ASC"""
            )
        else:
            cursor.execute(
                """SELECT Preguntas_ID, Texto_Pregunta, Activa
                   FROM preguntas_ranking
                   ORDER BY Preguntas_ID ASC"""
            )

        filas = cursor.fetchall()
        return [
            {
                "ID_Pregunta":    fila[0],
                "Texto_Pregunta": fila[1],
                "Orden":          idx + 1,
                "Activa":         fila[2],
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
            "SELECT Preguntas_ID, Texto_Pregunta, Activa FROM preguntas_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )
        fila = cursor.fetchone()
        if fila is None:
            return None
        return {
            "ID_Pregunta":    fila[0],
            "Texto_Pregunta": fila[1],
            "Orden":          None,
            "Activa":         fila[2],
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
    Actualiza Texto_Pregunta y el estado Activa de una pregunta existente.
    Permite al administrador activar/desactivar preguntas (REQ 7).
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    activa_val = 1 if activa else 0

    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "UPDATE preguntas_ranking SET Texto_Pregunta = ?, Activa = ? WHERE Preguntas_ID = ?",
            (texto_pregunta, activa_val, pregunta_id)
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


def togglear_activa(pregunta_id):
    """
    Invierte el estado Activa de una pregunta (1→0 o 0→1).
    Retorna el nuevo valor de Activa, o None si la pregunta no existe.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "SELECT Activa FROM preguntas_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )
        fila = cursor.fetchone()
        if fila is None:
            return None
        nuevo_estado = 0 if fila[0] == 1 else 1
        cursor.execute(
            "UPDATE preguntas_ranking SET Activa = ? WHERE Preguntas_ID = ?",
            (nuevo_estado, pregunta_id)
        )
        conexion.commit()
        return nuevo_estado
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
    Elimina una pregunta por su Preguntas_ID de forma atómica.

    FIX: antes el DELETE fallaba/quedaba interrumpido porque la pregunta
    tenía respuestas asociadas en respuesta_ranking (violación de FK /
    integridad). Ahora, dentro de una sola transacción:
      1) Verifica que la pregunta exista.
      2) Borra primero las respuestas dependientes en respuesta_ranking.
      3) Borra la pregunta en preguntas_ranking.
      4) Solo confirma (commit) si la fila de preguntas_ranking fue
         realmente eliminada (rowcount > 0); de lo contrario hace rollback.

    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()

        # Asegurar que las FK no bloqueen el borrado en cascada manual
        try:
            cursor.execute("PRAGMA foreign_keys = OFF")
        except Exception:
            pass

        cursor.execute("BEGIN TRANSACTION")

        cursor.execute(
            "SELECT Preguntas_ID FROM preguntas_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )
        if cursor.fetchone() is None:
            conexion.rollback()
            return False

        # Eliminar dependencias antes de eliminar la pregunta
        cursor.execute(
            "DELETE FROM respuesta_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )

        cursor.execute(
            "DELETE FROM preguntas_ranking WHERE Preguntas_ID = ?",
            (pregunta_id,)
        )
        filas_afectadas = cursor.rowcount

        if filas_afectadas == 0:
            conexion.rollback()
            return False

        conexion.commit()
        return True
    except Exception as e:
        if conexion:
            conexion.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()