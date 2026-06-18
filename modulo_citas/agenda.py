from db import get_db_connection
from sqlite3 import Error

def _get_conn():
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ─── CREATE ───────────────────────────────────────────────────────────────────

def create_agenda(especialista_id: int, fecha: str, hora_inicio: str, hora_fin: str, estado_id: int) -> dict:
    """
    Crea un registro en agenda.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor = conn.execute("""
            INSERT INTO agenda (
                Especialista_ID,
                Fecha,
                Hora_Inicio,
                Hora_Fin,
                Estado_ID
            )
            VALUES (?, ?, ?, ?, ?)
        """, (especialista_id, fecha, hora_inicio, hora_fin, estado_id))

        agenda_id = cursor.lastrowid

        conn.commit()
        return {"ok": True, "agenda_id": agenda_id}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# ─── READ ALL ─────────────────────────────────────────────────────────────────

def read_all_agendas() -> list[dict]:
    """
    Lista todas las agendas con información del especialista y estado.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                a.Agenda_ID,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,

                e.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos AS Especialista,

                ea.Nombre_Estado AS Estado

            FROM agenda a
            JOIN especialistas e ON a.Especialista_ID = e.Especialista_ID
            JOIN usuario u      ON e.Usuario_ID = u.Usuario_ID
            JOIN estado_agenda ea ON a.Estado_ID = ea.Estado_ID

            ORDER BY a.Fecha DESC, a.Hora_Inicio ASC
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[read_all_agendas] Error: {e}")
        return []

    finally:
        conn.close()


# ─── READ BY ID ───────────────────────────────────────────────────────────────

def read_agenda_by_id(agenda_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                a.Agenda_ID,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,

                e.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos AS Especialista,

                ea.Nombre_Estado AS Estado

            FROM agenda a
            JOIN especialistas e ON a.Especialista_ID = e.Especialista_ID
            JOIN usuarios u      ON e.Usuario_ID = u.Usuario_ID
            JOIN estado_agenda ea ON a.Estado_ID = ea.Estado_ID

            WHERE a.Agenda_ID = ?
        """, (agenda_id,)).fetchone()

        return dict(row) if row else None

    except Error as e:
        print(f"[read_agenda_by_id] Error: {e}")
        return None

    finally:
        conn.close()


# ─── UPDATE ───────────────────────────────────────────────────────────────────

def update_agenda(agenda_id: int, fecha: str, hora_inicio: str, hora_fin: str, estado_id: int) -> dict:
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor = conn.execute("""
            UPDATE agenda
            SET Fecha = ?,
                Hora_Inicio = ?,
                Hora_Fin = ?,
                Estado_ID = ?
            WHERE Agenda_ID = ?
        """, (fecha, hora_inicio, hora_fin, estado_id, agenda_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return {"ok": False, "error": f"No existe la agenda {agenda_id}"}

        conn.commit()
        return {"ok": True, "mensaje": "Agenda actualizada correctamente"}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# ─── DELETE ───────────────────────────────────────────────────────────────────

def delete_agenda(agenda_id: int) -> dict:
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        existe = conn.execute("""
            SELECT Agenda_ID FROM agenda WHERE Agenda_ID = ?
        """, (agenda_id,)).fetchone()

        if not existe:
            conn.rollback()
            return {"ok": False, "error": f"No existe la agenda {agenda_id}"}

        conn.execute("""
            DELETE FROM agenda WHERE Agenda_ID = ?
        """, (agenda_id,))

        conn.commit()
        return {"ok": True, "mensaje": "Agenda eliminada correctamente"}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()