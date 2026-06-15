import sqlite3
from sqlite3 import Error

DB_NAME = "odent.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ─── CREATE ───────────────────────────────────────────────────────────────────

def create_cita(paciente_id: int, agenda_id: int, motivo_consulta: str) -> dict:
    """
    CREA una cita médica.

    Retorna:
        {'ok': True, 'cita_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor = conn.execute("""
            INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta)
            VALUES (?, ?, ?)
        """, (paciente_id, agenda_id, motivo_consulta))

        cita_id = cursor.lastrowid

        conn.commit()
        return {"ok": True, "cita_id": cita_id}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# ─── READ ALL ─────────────────────────────────────────────────────────────────

def read_all_citas() -> list[dict]:
    """
    Lista todas las citas con información legible (JOIN completo).
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,

                p.Paciente_ID,
                u.Nombres || ' ' || u.Apellidos AS Paciente,

                a.Agenda_ID,
                a.Fecha,
                a.Hora,

                e.Nombre_Estado AS Estado_Cita

            FROM cita c
            JOIN paciente p      ON c.Paciente_ID = p.Paciente_ID
            JOIN usuarios u      ON p.Usuario_ID  = u.Usuario_ID
            JOIN agenda a        ON c.Agenda_ID    = a.Agenda_ID
            LEFT JOIN estado_cita e ON c.Estado_ID = e.Estado_ID

            ORDER BY a.Fecha DESC, a.Hora DESC
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[read_all_citas] Error: {e}")
        return []

    finally:
        conn.close()


# ─── READ BY ID ───────────────────────────────────────────────────────────────

def read_cita_by_id(cita_id: int) -> dict | None:
    """
    Obtiene una cita con información completa.
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,

                p.Paciente_ID,
                u.Nombres || ' ' || u.Apellidos AS Paciente,

                a.Agenda_ID,
                a.Fecha,
                a.Hora,

                e.Nombre_Estado AS Estado_Cita

            FROM cita c
            JOIN paciente p      ON c.Paciente_ID = p.Paciente_ID
            JOIN usuarios u      ON p.Usuario_ID  = u.Usuario_ID
            JOIN agenda a        ON c.Agenda_ID    = a.Agenda_ID
            LEFT JOIN estado_cita e ON c.Estado_ID = e.Estado_ID

            WHERE c.Cita_ID = ?
        """, (cita_id,)).fetchone()

        return dict(row) if row else None

    except Error as e:
        print(f"[read_cita_by_id] Error: {e}")
        return None

    finally:
        conn.close()


# ─── UPDATE ───────────────────────────────────────────────────────────────────

def update_cita(cita_id: int, motivo_consulta: str) -> dict:
    """
    Actualiza el motivo de la cita.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        cursor = conn.execute("""
            UPDATE cita
            SET Motivo_Consulta = ?
            WHERE Cita_ID = ?
        """, (motivo_consulta, cita_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return {"ok": False, "error": f"No existe la cita {cita_id}"}

        conn.commit()
        return {"ok": True, "mensaje": "Cita actualizada correctamente"}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# ─── DELETE ───────────────────────────────────────────────────────────────────

def delete_cita(cita_id: int) -> dict:
    """
    Elimina una cita.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")

        existe = conn.execute("""
            SELECT Cita_ID FROM cita WHERE Cita_ID = ?
        """, (cita_id,)).fetchone()

        if not existe:
            conn.rollback()
            return {"ok": False, "error": f"No existe la cita {cita_id}"}

        conn.execute("""
            DELETE FROM cita WHERE Cita_ID = ?
        """, (cita_id,))

        conn.commit()
        return {"ok": True, "mensaje": "Cita eliminada correctamente"}

    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}

    finally:
        conn.close()


# ─── REPORTES ─────────────────────────────────────────────────────────────────

def reporte_citas_por_estado() -> list[dict]:
    """
    Cantidad de citas agrupadas por estado.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                e.Nombre_Estado AS Estado,
                COUNT(c.Cita_ID) AS TotalCitas
            FROM cita c
            JOIN estado_cita e ON c.Estado_ID = e.Estado_ID
            GROUP BY c.Estado_ID
            ORDER BY TotalCitas DESC
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[reporte_citas_por_estado] Error: {e}")
        return []

    finally:
        conn.close()


def reporte_citas_por_fecha() -> list[dict]:
    """
    Número de citas por fecha.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                a.Fecha,
                COUNT(c.Cita_ID) AS TotalCitas
            FROM cita c
            JOIN agenda a ON c.Agenda_ID = a.Agenda_ID
            GROUP BY a.Fecha
            ORDER BY a.Fecha DESC
        """).fetchall()

        return [dict(r) for r in rows]

    except Error as e:
        print(f"[reporte_citas_por_fecha] Error: {e}")
        return []

    finally:
        conn.close()