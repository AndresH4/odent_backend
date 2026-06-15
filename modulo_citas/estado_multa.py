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
def create_estado_multa(nombre_estado):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            INSERT INTO estado_multa (Nombre_Estado)
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
def read_all_estados_multa():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                Estado_Multa_ID,
                Nombre_Estado
            FROM estado_multa
            ORDER BY Estado_Multa_ID
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def read_estado_multa_by_id(estado_multa_id):
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                Estado_Multa_ID,
                Nombre_Estado
            FROM estado_multa
            WHERE Estado_Multa_ID = ?
        """, (estado_multa_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# =========================
# UPDATE
# =========================
def update_estado_multa(estado_multa_id, nombre_estado=None):
    conn = _get_conn()
    try:
        actual = conn.execute("""
            SELECT * FROM estado_multa
            WHERE Estado_Multa_ID = ?
        """, (estado_multa_id,)).fetchone()

        if not actual:
            return {"ok": False, "error": "Estado de multa no encontrado"}

        nombre_estado = (
            nombre_estado
            if nombre_estado is not None
            else actual["Nombre_Estado"]
        )

        conn.execute("""
            UPDATE estado_multa
            SET Nombre_Estado = ?
            WHERE Estado_Multa_ID = ?
        """, (nombre_estado, estado_multa_id))

        conn.commit()
        return {"ok": True}

    except Error as e:
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# =========================
# DELETE
# =========================
def delete_estado_multa(estado_multa_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM estado_multa
            WHERE Estado_Multa_ID = ?
        """, (estado_multa_id,))
        conn.commit()
        return {"ok": True}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()