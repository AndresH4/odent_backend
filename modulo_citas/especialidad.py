import sqlite3
from sqlite3 import Error

DB_NAME = "odent.db"

def _get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================
# CREATE
# =========================
def create_especialidad(nombre_especialidad):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            INSERT INTO especialidad (Nombre_Especialidad)
            VALUES (?)
        """, (nombre_especialidad,))
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
def read_all_especialidades():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                Especialidad_ID,
                Nombre_Especialidad
            FROM especialidad
            ORDER BY Especialidad_ID
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def read_especialidad_by_id(especialidad_id):
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT 
                Especialidad_ID,
                Nombre_Especialidad
            FROM especialidad
            WHERE Especialidad_ID = ?
        """, (especialidad_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# =========================
# UPDATE
# =========================
def update_especialidad(especialidad_id, nombre_especialidad=None):
    conn = _get_conn()
    try:
        actual = conn.execute("""
            SELECT * FROM especialidad WHERE Especialidad_ID = ?
        """, (especialidad_id,)).fetchone()

        if not actual:
            return {"ok": False, "error": "Especialidad no encontrada"}

        nombre_especialidad = (
            nombre_especialidad 
            if nombre_especialidad is not None 
            else actual["Nombre_Especialidad"]
        )

        conn.execute("""
            UPDATE especialidad
            SET Nombre_Especialidad = ?
            WHERE Especialidad_ID = ?
        """, (nombre_especialidad, especialidad_id))

        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# =========================
# DELETE
# =========================
def delete_especialidad(especialidad_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM especialidad
            WHERE Especialidad_ID = ?
        """, (especialidad_id,))
        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()