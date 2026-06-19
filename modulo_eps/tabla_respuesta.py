# =============================================================================
# modulo_eps/tabla_respuesta.py
# CRUD para la tabla respuesta_ranking.
# Los ESPECIALISTAS son los calificados; los PACIENTES son los calificantes.
#
# Esquema real (init_db.py):
#   respuesta_ranking (
#     Respuesta_ID INTEGER PK,
#     Cita_ID      INT NOT NULL → cita(Cita_ID),
#     Preguntas_ID INT NOT NULL → preguntas_ranking(Preguntas_ID),
#     Respuesta    INT NOT NULL   ← valor numérico 1-5
#   )
#
# INTEGRACIÓN:
#   - POST /api/respuesta es manejado por modulo_citas/routes.py (citas_bp)
#     que recibe Cita_ID explícito desde paciente.js._enviarRanking() e
#     inserta directamente en respuesta_ranking con SQL nativo.
#   - Este módulo expone funciones Python para consultas administrativas
#     usadas por modulo_eps/routes.py (eps_bp):
#       GET /api/respuesta                              → obtener_respuestas()
#       GET /api/respuesta/<id>                         → obtener_respuesta_por_id()
#       GET /api/reporte/respuestas-paciente/<id>       → obtener_respuestas_por_paciente()
#       GET /api/reporte/ranking-especialistas          → obtener_ranking_especialistas()
#
# Cadena de JOINs para llegar al especialista calificado:
#   respuesta_ranking
#     → cita          (Cita_ID)
#     → agenda        (Agenda_ID)          ← agenda pertenece al especialista
#     → especialista  (Especialista_ID)
#     → usuarios      (Usuario_ID)          ← nombre del especialista
#     → especialista_especialidad           ← primera especialidad asignada
#     → especialidad  (Especialidad_ID)
#
# Cadena para el paciente calificante:
#   cita → paciente → usuarios
# =============================================================================

from db import get_db_connection


# ---------------------------------------------------------------------------
# CREAR RESPUESTA
# Usado solo como fallback desde modulo_eps/routes.py (gestión administrativa).
# El flujo principal usa modulo_citas/routes.py con Cita_ID explícito.
# ---------------------------------------------------------------------------
def crear_respuesta(pregunta_id, paciente_id, texto_respuesta):
    """
    Registra la respuesta de un paciente a una pregunta.
    Busca la Cita_ID más reciente del paciente para relacionar la respuesta.
    """
    try:
        valor_int = int(texto_respuesta)
    except (ValueError, TypeError):
        raise ValueError(
            f"Texto_Respuesta debe ser un número entero, recibido: {texto_respuesta!r}"
        )

    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()

        cursor.execute(
            """
            SELECT c.Cita_ID
            FROM cita c
            WHERE c.Paciente_ID = ?
            ORDER BY c.Cita_ID DESC
            LIMIT 1
            """,
            (paciente_id,)
        )
        fila_cita = cursor.fetchone()
        if fila_cita is None:
            raise ValueError(
                f"No se encontró ninguna cita para el paciente ID {paciente_id}"
            )

        cita_id = fila_cita[0]

        cursor.execute(
            """
            INSERT INTO respuesta_ranking (Cita_ID, Preguntas_ID, Respuesta)
            VALUES (?, ?, ?)
            """,
            (cita_id, pregunta_id, valor_int)
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


# ---------------------------------------------------------------------------
# OBTENER TODAS LAS RESPUESTAS (con JOINs enriquecidos)
# ---------------------------------------------------------------------------
def obtener_respuestas():
    """
    Retorna todas las respuestas con datos del especialista calificado
    y del paciente calificante.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                rr.Respuesta_ID,
                CAST(rr.Respuesta AS TEXT)              AS Texto_Respuesta,
                rr.Preguntas_ID                         AS ID_Pregunta,
                pr.Texto_Pregunta,
                rr.Preguntas_ID                         AS Orden_Pregunta,
                e.Especialista_ID                       AS ID_Especialista,
                ue.Nombres || ' ' || ue.Apellidos       AS Nombre_Especialista,
                p.Paciente_ID                           AS ID_Paciente,
                up.Nombres || ' ' || up.Apellidos       AS Nombre_Paciente
            FROM respuesta_ranking  rr
            INNER JOIN preguntas_ranking  pr ON rr.Preguntas_ID  = pr.Preguntas_ID
            INNER JOIN cita               c  ON rr.Cita_ID       = c.Cita_ID
            INNER JOIN agenda             ag ON c.Agenda_ID      = ag.Agenda_ID
            INNER JOIN especialista       e  ON ag.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios           ue ON e.Usuario_ID     = ue.Usuario_ID
            INNER JOIN paciente           p  ON c.Paciente_ID   = p.Paciente_ID
            INNER JOIN usuarios           up ON p.Usuario_ID    = up.Usuario_ID
            ORDER BY e.Especialista_ID ASC, rr.Preguntas_ID ASC
            """
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


# ---------------------------------------------------------------------------
# OBTENER RESPUESTA POR ID
# ---------------------------------------------------------------------------
def obtener_respuesta_por_id(respuesta_id):
    """
    Retorna una respuesta específica por su Respuesta_ID con JOINs completos.
    Devuelve None si no existe.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                rr.Respuesta_ID,
                CAST(rr.Respuesta AS TEXT)              AS Texto_Respuesta,
                rr.Preguntas_ID                         AS ID_Pregunta,
                pr.Texto_Pregunta,
                rr.Preguntas_ID                         AS Orden_Pregunta,
                e.Especialista_ID                       AS ID_Especialista,
                ue.Nombres || ' ' || ue.Apellidos       AS Nombre_Especialista,
                p.Paciente_ID                           AS ID_Paciente,
                up.Nombres || ' ' || up.Apellidos       AS Nombre_Paciente
            FROM respuesta_ranking  rr
            INNER JOIN preguntas_ranking  pr ON rr.Preguntas_ID    = pr.Preguntas_ID
            INNER JOIN cita               c  ON rr.Cita_ID         = c.Cita_ID
            INNER JOIN agenda             ag ON c.Agenda_ID        = ag.Agenda_ID
            INNER JOIN especialista       e  ON ag.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios           ue ON e.Usuario_ID       = ue.Usuario_ID
            INNER JOIN paciente           p  ON c.Paciente_ID      = p.Paciente_ID
            INNER JOIN usuarios           up ON p.Usuario_ID       = up.Usuario_ID
            WHERE rr.Respuesta_ID = ?
            """,
            (respuesta_id,)
        )
        columnas = [desc[0] for desc in cursor.description]
        fila     = cursor.fetchone()
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


# ---------------------------------------------------------------------------
# RANKING CONSOLIDADO POR ESPECIALISTA
# ---------------------------------------------------------------------------
def obtener_ranking_especialistas():
    """
    Retorna el ranking de especialistas ordenado por promedio descendente.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                e.Especialista_ID                           AS ID_Especialista,
                ue.Nombres || ' ' || ue.Apellidos           AS Nombre_Especialista,
                COALESCE(esp.Nombre_Especialidad, '—')      AS Especialidad,
                ROUND(AVG(CAST(rr.Respuesta AS REAL)), 2)   AS Promedio,
                COUNT(rr.Respuesta_ID)                      AS Total_Evaluaciones
            FROM respuesta_ranking  rr
            INNER JOIN cita               c  ON rr.Cita_ID         = c.Cita_ID
            INNER JOIN agenda             ag ON c.Agenda_ID        = ag.Agenda_ID
            INNER JOIN especialista       e  ON ag.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios           ue ON e.Usuario_ID       = ue.Usuario_ID
            LEFT JOIN (
                SELECT ee.Especialista_ID, MIN(esp2.Nombre_Especialidad) AS Nombre_Especialidad
                FROM especialista_especialidad ee
                INNER JOIN especialidad esp2 ON ee.Especialidad_ID = esp2.Especialidad_ID
                GROUP BY ee.Especialista_ID
            ) esp ON e.Especialista_ID = esp.Especialista_ID
            GROUP BY e.Especialista_ID, ue.Nombres, ue.Apellidos, esp.Nombre_Especialidad
            ORDER BY Promedio DESC, Total_Evaluaciones DESC
            """
        )
        columnas = [desc[0] for desc in cursor.description]
        filas    = cursor.fetchall()
        resultado = []
        for fila in filas:
            row = dict(zip(columnas, fila))
            row['Promedio']           = float(row['Promedio']) if row['Promedio'] is not None else 0.0
            row['Total_Evaluaciones'] = int(row['Total_Evaluaciones'])
            resultado.append(row)
        return resultado
    except Exception as e:
        raise e
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ---------------------------------------------------------------------------
# RESPUESTAS POR PACIENTE (reporte de formulario completo)
# Consumido por especialista.js.cargarRespuestasFormulario()
# via GET /api/reporte/respuestas-paciente/<paciente_id>
# ---------------------------------------------------------------------------
def obtener_respuestas_por_paciente(paciente_id):
    """
    Reporte consolidado: preguntas + respuestas de un paciente específico,
    incluyendo el nombre del especialista que atendió cada cita.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            """
            SELECT
                rr.Respuesta_ID,
                p.Paciente_ID                           AS ID_Paciente,
                up.Nombres || ' ' || up.Apellidos       AS Nombre_Paciente,
                pr.Preguntas_ID                         AS ID_Pregunta,
                pr.Texto_Pregunta,
                rr.Preguntas_ID                         AS Orden_Pregunta,
                CAST(rr.Respuesta AS TEXT)              AS Texto_Respuesta,
                e.Especialista_ID                       AS ID_Especialista,
                ue.Nombres || ' ' || ue.Apellidos       AS Nombre_Especialista
            FROM respuesta_ranking  rr
            INNER JOIN preguntas_ranking  pr ON rr.Preguntas_ID    = pr.Preguntas_ID
            INNER JOIN cita               c  ON rr.Cita_ID         = c.Cita_ID
            INNER JOIN agenda             ag ON c.Agenda_ID        = ag.Agenda_ID
            INNER JOIN especialista       e  ON ag.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios           ue ON e.Usuario_ID       = ue.Usuario_ID
            INNER JOIN paciente           p  ON c.Paciente_ID      = p.Paciente_ID
            INNER JOIN usuarios           up ON p.Usuario_ID       = up.Usuario_ID
            WHERE p.Paciente_ID = ?
            ORDER BY rr.Preguntas_ID ASC
            """,
            (paciente_id,)
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


# ---------------------------------------------------------------------------
# ACTUALIZAR RESPUESTA
# ---------------------------------------------------------------------------
def actualizar_respuesta(respuesta_id, texto_respuesta):
    """
    Actualiza el valor de una respuesta existente.
    """
    try:
        valor_int = int(texto_respuesta)
    except (ValueError, TypeError):
        raise ValueError(
            f"Texto_Respuesta debe ser un número entero, recibido: {texto_respuesta!r}"
        )

    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "UPDATE respuesta_ranking SET Respuesta = ? WHERE Respuesta_ID = ?",
            (valor_int, respuesta_id)
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
# ELIMINAR RESPUESTA
# ---------------------------------------------------------------------------
def eliminar_respuesta(respuesta_id):
    """
    Elimina una respuesta por su Respuesta_ID.
    """
    conexion = None
    cursor   = None
    try:
        conexion = get_db_connection()
        cursor   = conexion.cursor()
        cursor.execute(
            "DELETE FROM respuesta_ranking WHERE Respuesta_ID = ?",
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