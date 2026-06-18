from db import get_db_connection
from sqlite3 import Error

def _get_conn():
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================
# CREATE
# =========================
def create_especialista(usuario_id, tarjeta_profesional):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            INSERT INTO especialistas (
                Usuario_ID,
                Tarjeta_Profesional
            )
            VALUES (?, ?)
        """, (usuario_id, tarjeta_profesional))

        especialista_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.commit()
        return {"ok": True, "especialista_id": especialista_id}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# =========================
# READ ALL
# =========================
def read_all_especialistas():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                e.Especialista_ID,
                e.Usuario_ID,
                e.Tarjeta_Profesional,
                u.Nombres,
                u.Apellidos,
                u.Correo
            FROM especialistas e
            JOIN usuario u ON e.Usuario_ID = u.Usuario_ID
            ORDER BY u.Apellidos, u.Nombres
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[read_all_especialistas] Error: {e}")
        return []

    finally:
        conn.close()


# =========================
# READ BY ID
# =========================
def read_especialista_by_id(especialista_id):
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                e.Especialista_ID,
                e.Usuario_ID,
                e.Tarjeta_Profesional,
                u.Nombres,
                u.Apellidos,
                u.Correo
            FROM especialistas e
            JOIN usuario u ON e.Usuario_ID = u.Usuario_ID
            WHERE e.Especialista_ID = ?
        """, (especialista_id,)).fetchone()

        return dict(row) if row else None

    except Error as e:
        print(f"[read_especialista_by_id] Error: {e}")
        return None

    finally:
        conn.close()


# =========================
# UPDATE
# =========================
def update_especialista(especialista_id, usuario_id=None, tarjeta_profesional=None):
    conn = _get_conn()
    try:
        actual = conn.execute("""
            SELECT * FROM especialistas
            WHERE Especialista_ID = ?
        """, (especialista_id,)).fetchone()

        if not actual:
            return {"ok": False, "error": "Especialista no encontrado"}

        usuario_id = usuario_id if usuario_id is not None else actual["Usuario_ID"]
        tarjeta_profesional = (
            tarjeta_profesional
            if tarjeta_profesional is not None
            else actual["Tarjeta_Profesional"]
        )

        conn.execute("""
            UPDATE especialistas
            SET Usuario_ID = ?,
                Tarjeta_Profesional = ?
            WHERE Especialista_ID = ?
        """, (usuario_id, tarjeta_profesional, especialista_id))

        conn.commit()
        return {"ok": True}

    except Error as e:
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# =========================
# DELETE
# =========================
def delete_especialista(especialista_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM especialistas
            WHERE Especialista_ID = ?
        """, (especialista_id,))

        conn.commit()
        return {"ok": True}

    except Error as e:
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()