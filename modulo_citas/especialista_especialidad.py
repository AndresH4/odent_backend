from db import get_db_connection
from sqlite3 import Error

def _get_conn():
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================
# CREATE
# =========================
def create_especialista_especialidad(especialista_id, especialidad_id):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            INSERT INTO especialista_especialidad (
                Especialista_ID,
                Especialidad_ID
            )
            VALUES (?, ?)
        """, (especialista_id, especialidad_id))
        conn.commit()
        return {"ok": True}
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# =========================
# READ
# =========================
def read_all_especialista_especialidad():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                ee.Especialista_ID,
                ee.Especialidad_ID,
                e.Usuario_ID,
                u.Nombres || ' ' || u.Apellidos AS Especialista,
                es.Nombre_Especialidad
            FROM especialista_especialidad ee
            JOIN especialistas e ON ee.Especialista_ID = e.Especialista_ID
            JOIN usuario u       ON e.Usuario_ID = u.Usuario_ID
            JOIN especialidad es ON ee.Especialidad_ID = es.Especialidad_ID
            ORDER BY Especialista, es.Nombre_Especialidad
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def read_by_especialista(especialista_id):
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                ee.Especialista_ID,
                ee.Especialidad_ID,
                es.Nombre_Especialidad
            FROM especialista_especialidad ee
            JOIN especialidad es ON ee.Especialidad_ID = es.Especialidad_ID
            WHERE ee.Especialista_ID = ?
        """, (especialista_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# =========================
# DELETE
# =========================
def delete_especialista_especialidad(especialista_id, especialidad_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM especialista_especialidad
            WHERE Especialista_ID = ? AND Especialidad_ID = ?
        """, (especialista_id, especialidad_id))
        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()