"""
modulo_usuarios/genero.py
=========================
Gestión de la tabla 'genero'.
Tabla catálogo — sin dependencias externas.
 
Columnas:
    Genero_ID   INTEGER PRIMARY KEY AUTOINCREMENT
    NombreGenero VARCHAR(20) NOT NULL
"""
 
import sqlite3
from sqlite3 import Error
 
DB_NAME = "odent.db"
 
 
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
 
 
# ─── CREATE ───────────────────────────────────────────────────────────────────
 
def create_genero(nombre: str) -> dict:
    """
    Crea un nuevo género.
 
    Parámetros:
        nombre : Nombre del género (ej: 'Femenino', 'Masculino')
 
    Retorna:
        {'ok': True,  'genero_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO genero (NombreGenero) VALUES (?)", (nombre,)
        )
        conn.commit()
        return {"ok": True, "genero_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_generos() -> list[dict]:
    """
    Retorna todos los géneros.
 
    Retorna:
        Lista de dicts con: Genero_ID, NombreGenero
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT Genero_ID, NombreGenero FROM genero ORDER BY Genero_ID"
        ).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_generos] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_genero_by_id(genero_id: int) -> dict | None:
    """
    Busca un género por su ID.
 
    Parámetros:
        genero_id : ID del género
 
    Retorna:
        dict con Genero_ID y NombreGenero, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT Genero_ID, NombreGenero FROM genero WHERE Genero_ID = ?",
            (genero_id,)
        ).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_genero_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_genero(genero_id: int, nombre: str) -> dict:
    """
    Actualiza el nombre de un género.
 
    Parámetros:
        genero_id : ID del género a actualizar
        nombre    : Nuevo nombre
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE genero SET NombreGenero = ? WHERE Genero_ID = ?",
            (nombre, genero_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Género {genero_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_genero(genero_id: int) -> dict:
    """
    Elimina un género.
 
    ⚠ Si hay usuarios con este género, SQLite lanzará error de FK.
 
    Parámetros:
        genero_id : ID del género a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM genero WHERE Genero_ID = ?", (genero_id,))
        conn.commit()
        return {"ok": True, "mensaje": f"Género {genero_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTE ──────────────────────────────────────────────────────────────────
 
def reporte_usuarios_por_genero() -> list[dict]:
    """
    REPORTE — JOIN: genero + usuarios
 
    Muestra cuántos usuarios hay por género.
 
    Retorna:
        Lista de dicts con: Genero, TotalUsuarios
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                g.NombreGenero      AS Genero,
                COUNT(u.Usuario_ID) AS TotalUsuarios
            FROM genero g
            LEFT JOIN usuarios u ON u.Genero_ID = g.Genero_ID
            GROUP BY g.Genero_ID
            ORDER BY TotalUsuarios DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_por_genero] Error: {e}")
        return []
    finally:
        conn.close()