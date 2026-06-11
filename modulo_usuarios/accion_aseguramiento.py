"""
modulo_usuarios/accion_aseguramiento.py
========================================
Gestión de la tabla 'accion_aseguramiento'.
Tabla catálogo — sin dependencias externas.
 
Columnas:
    Accion_ID    INTEGER PRIMARY KEY AUTOINCREMENT
    Nombre_Accion VARCHAR(20) NOT NULL
"""
 
import sqlite3
from sqlite3 import Error
 
DB_NAME = "odent.db"
 
 
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
 
 
def create_accion(nombre: str) -> dict:
    """Crea una nueva acción de aseguramiento."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO accion_aseguramiento (Nombre_Accion) VALUES (?)", (nombre,)
        )
        conn.commit()
        return {"ok": True, "accion_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
def read_all_acciones() -> list[dict]:
    """Retorna todas las acciones de aseguramiento."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT Accion_ID, Nombre_Accion FROM accion_aseguramiento ORDER BY Accion_ID"
        ).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_acciones] Error: {e}")
        return []
    finally:
        conn.close()
 
 
def read_accion_by_id(accion_id: int) -> dict | None:
    """Busca una acción por su ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT Accion_ID, Nombre_Accion FROM accion_aseguramiento WHERE Accion_ID = ?",
            (accion_id,)
        ).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_accion_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
def update_accion(accion_id: int, nombre: str) -> dict:
    """Actualiza el nombre de una acción."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE accion_aseguramiento SET Nombre_Accion = ? WHERE Accion_ID = ?",
            (nombre, accion_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Acción {accion_id} actualizada"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
def delete_accion(accion_id: int) -> dict:
    """Elimina una acción de aseguramiento."""
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM accion_aseguramiento WHERE Accion_ID = ?", (accion_id,)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Acción {accion_id} eliminada"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()