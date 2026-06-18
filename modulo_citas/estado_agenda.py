from db import get_db_connection
from sqlite3 import Error

def _get_conn():
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================
# CREATE
# =========================
def create_estado_agenda(nombre_estado):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            INSERT INTO estado_agenda (Nombre_Estado)
            VALUES (?)
        """, (nombre_estado,))
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
def read_all_estados_agenda():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT 
                Estado_ID,
                Nombre_Estado
            FROM estado_agenda
            ORDER BY Estado_ID
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def read_estado_agenda_by_id(estado_id):
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT 
                Estado_ID,
                Nombre_Estado
            FROM estado_agenda
            WHERE Estado_ID = ?
        """, (estado_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# =========================
# UPDATE
# =========================
def update_estado_agenda(estado_id, nombre_estado=None):
    conn = _get_conn()
    try:
        actual = conn.execute("""
            SELECT * FROM estado_agenda WHERE Estado_ID = ?
        """, (estado_id,)).fetchone()

        if not actual:
            return {"ok": False, "error": "Estado no encontrado"}

        nombre_estado = nombre_estado if nombre_estado is not None else actual["Nombre_Estado"]

        conn.execute("""
            UPDATE estado_agenda
            SET Nombre_Estado = ?
            WHERE Estado_ID = ?
        """, (nombre_estado, estado_id))

        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

# =========================
# DELETE
# =========================
def delete_estado_agenda(estado_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM estado_agenda
            WHERE Estado_ID = ?
        """, (estado_id,))
        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()