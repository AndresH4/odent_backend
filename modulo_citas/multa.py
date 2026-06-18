from db import get_db_connection
from sqlite3 import Error

def _get_conn():
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# =========================
# CREATE
# =========================
def create_multa(cita_id, estado_multa_id):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")

        conn.execute("""
            INSERT INTO multa (
                Cita_ID,
                Estado_Multa_ID
            )
            VALUES (?, ?)
        """, (cita_id, estado_multa_id))

        multa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.commit()
        return {"ok": True, "multa_id": multa_id}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# =========================
# READ ALL (JOIN COMPLETO)
# =========================
def read_all_multas():
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                m.Multa_ID,

                c.Cita_ID,
                c.Motivo_Consulta,

                p.Paciente_ID,
                u.Nombres || ' ' || u.Apellidos AS Paciente,

                m.Estado_Multa_ID,
                em.Nombre_Estado AS Estado_Multa

            FROM multa m
            JOIN cita c ON m.Cita_ID = c.Cita_ID
            JOIN paciente p ON c.Paciente_ID = p.Paciente_ID
            JOIN usuario u ON p.Usuario_ID = u.Usuario_ID
            JOIN estado_multa em ON m.Estado_Multa_ID = em.Estado_Multa_ID

            ORDER BY m.Multa_ID
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[read_all_multas] Error: {e}")
        return []

    finally:
        conn.close()


# =========================
# READ BY ID (JOIN COMPLETO)
# =========================
def read_multa_by_id(multa_id):
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                m.Multa_ID,

                c.Cita_ID,
                c.Motivo_Consulta,

                p.Paciente_ID,
                u.Nombres || ' ' || u.Apellidos AS Paciente,

                m.Estado_Multa_ID,
                em.Nombre_Estado AS Estado_Multa

            FROM multa m
            JOIN cita c ON m.Cita_ID = c.Cita_ID
            JOIN paciente p ON c.Paciente_ID = p.Paciente_ID
            JOIN usuario u ON p.Usuario_ID = u.Usuario_ID
            JOIN estado_multa em ON m.Estado_Multa_ID = em.Estado_Multa_ID

            WHERE m.Multa_ID = ?
        """, (multa_id,)).fetchone()

        return dict(row) if row else None

    except Error as e:
        print(f"[read_multa_by_id] Error: {e}")
        return None

    finally:
        conn.close()


# =========================
# UPDATE
# =========================
def update_multa(multa_id, cita_id=None, estado_multa_id=None):
    conn = _get_conn()
    try:
        actual = conn.execute("""
            SELECT * FROM multa WHERE Multa_ID = ?
        """, (multa_id,)).fetchone()

        if not actual:
            return {"ok": False, "error": "Multa no encontrada"}

        cita_id = cita_id if cita_id is not None else actual["Cita_ID"]
        estado_multa_id = estado_multa_id if estado_multa_id is not None else actual["Estado_Multa_ID"]

        conn.execute("""
            UPDATE multa
            SET Cita_ID = ?,
                Estado_Multa_ID = ?
            WHERE Multa_ID = ?
        """, (cita_id, estado_multa_id, multa_id))

        conn.commit()
        return {"ok": True}

    except Error as e:
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# =========================
# DELETE
# =========================
def delete_multa(multa_id):
    conn = _get_conn()
    try:
        conn.execute("""
            DELETE FROM multa
            WHERE Multa_ID = ?
        """, (multa_id,))

        conn.commit()
        return {"ok": True}

    except Error as e:
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()