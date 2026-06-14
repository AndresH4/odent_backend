# =============================================================================
# modulo_eps/paciente.py
# CRUD para la tabla paciente — JOINs con usuarios, afiliacion y eps
# =============================================================================
 
from db import get_db_connection
 
 
def registrar_paciente(usuario_id, fecha_nacimiento=None, genero=None,
                       grupo_sanguineo=None, alergias=None,
                       antecedentes=None, observaciones=None):
    """
    Registra un nuevo paciente vinculado a un usuario existente.
    Retorna el ID del registro creado.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO paciente
                (ID_Usuario, Fecha_Nacimiento, Genero, Grupo_Sanguineo,
                 Alergias, Antecedentes, Observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (usuario_id, fecha_nacimiento, genero, grupo_sanguineo,
             alergias, antecedentes, observaciones)
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
 
 
def obtener_pacientes():
    """
    Retorna todos los pacientes enriquecidos con:
      - Nombre completo y correo del usuario asociado
      - Nombre de la EPS y estado de afiliación (via LEFT JOIN para pacientes
        que aún no tienen afiliación registrada)
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                p.ID_Paciente,
                p.ID_Usuario,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo,
                u.Correo,
                u.Telefono                       AS Telefono_Usuario,
                p.Fecha_Nacimiento,
                p.Genero,
                p.Grupo_Sanguineo,
                p.Alergias,
                p.Antecedentes,
                p.Observaciones,
                a.ID_Afiliacion,
                a.Estado                         AS Estado_Afiliacion,
                a.Numero_Afiliado,
                e.Nombre_EPS
            FROM paciente p
            INNER JOIN usuarios  u ON p.ID_Usuario   = u.ID_Usuario
            LEFT  JOIN afiliacion a ON a.ID_Usuario   = p.ID_Usuario
            LEFT  JOIN eps        e ON a.ID_EPS        = e.ID_EPS
            ORDER BY u.Apellidos ASC, u.Nombres ASC
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
 
 
def obtener_paciente_por_id(paciente_id):
    """
    Retorna un paciente específico por su ID de paciente,
    con los mismos JOINs que obtener_pacientes.
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
                p.ID_Paciente,
                p.ID_Usuario,
                u.Nombres || ' ' || u.Apellidos AS Nombre_Completo,
                u.Correo,
                u.Telefono                       AS Telefono_Usuario,
                p.Fecha_Nacimiento,
                p.Genero,
                p.Grupo_Sanguineo,
                p.Alergias,
                p.Antecedentes,
                p.Observaciones,
                a.ID_Afiliacion,
                a.Estado                         AS Estado_Afiliacion,
                a.Numero_Afiliado,
                e.Nombre_EPS
            FROM paciente p
            INNER JOIN usuarios  u ON p.ID_Usuario   = u.ID_Usuario
            LEFT  JOIN afiliacion a ON a.ID_Usuario   = p.ID_Usuario
            LEFT  JOIN eps        e ON a.ID_EPS        = e.ID_EPS
            WHERE p.ID_Paciente = ?
            """,
            (paciente_id,)
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
 
 
def actualizar_paciente(paciente_id, fecha_nacimiento=None, genero=None,
                        grupo_sanguineo=None, alergias=None,
                        antecedentes=None, observaciones=None):
    """
    Actualiza los datos clínicos/demográficos de un paciente existente.
    Retorna True si se modificó al menos un registro, False si no se encontró.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE paciente
            SET Fecha_Nacimiento = ?,
                Genero            = ?,
                Grupo_Sanguineo   = ?,
                Alergias          = ?,
                Antecedentes      = ?,
                Observaciones     = ?
            WHERE ID_Paciente = ?
            """,
            (fecha_nacimiento, genero, grupo_sanguineo,
             alergias, antecedentes, observaciones, paciente_id)
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
 
 
def eliminar_paciente(paciente_id):
    """
    Elimina un paciente por su ID.
    Retorna True si se eliminó, False si no existía.
    """
    conexion = None
    cursor = None
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM paciente WHERE ID_Paciente = ?",
            (paciente_id,)
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