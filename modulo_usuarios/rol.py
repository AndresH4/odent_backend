"""
modulo_usuarios/rol.py
======================
Gestión de la tabla 'rol'.
Tabla catálogo — sin dependencias externas.
 
Columnas:
    Rol_ID      INTEGER PRIMARY KEY AUTOINCREMENT
    Descripcion VARCHAR(30) NOT NULL
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
 
def create_rol(descripcion: str) -> dict:
    """
    Crea un nuevo rol.
 
    Parámetros:
        descripcion : Nombre del rol (ej: 'Administrador', 'Paciente')
 
    Retorna:
        {'ok': True,  'rol_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO rol (Descripcion) VALUES (?)", (descripcion,)
        )
        conn.commit()
        return {"ok": True, "rol_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_roles() -> list[dict]:
    """
    Retorna todos los roles ordenados por ID.
 
    Retorna:
        Lista de dicts con: Rol_ID, Descripcion
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT Rol_ID, Descripcion FROM rol ORDER BY Rol_ID"
        ).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_roles] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_rol_by_id(rol_id: int) -> dict | None:
    """
    Busca un rol por su ID.
 
    Parámetros:
        rol_id : ID del rol a buscar
 
    Retorna:
        dict con Rol_ID y Descripcion, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT Rol_ID, Descripcion FROM rol WHERE Rol_ID = ?", (rol_id,)
        ).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_rol_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_rol(rol_id: int, descripcion: str) -> dict:
    """
    Actualiza la descripción de un rol.
 
    Parámetros:
        rol_id      : ID del rol a actualizar
        descripcion : Nueva descripción
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE rol SET Descripcion = ? WHERE Rol_ID = ?",
            (descripcion, rol_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Rol {rol_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_rol(rol_id: int) -> dict:
    """
    Elimina un rol.
 
    ⚠ Si hay usuarios usando este rol, SQLite lanzará error de FK.
    Verifica que no haya usuarios con este rol antes de eliminar.
 
    Parámetros:
        rol_id : ID del rol a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM rol WHERE Rol_ID = ?", (rol_id,))
        conn.commit()
        return {"ok": True, "mensaje": f"Rol {rol_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTE ──────────────────────────────────────────────────────────────────
 
def reporte_usuarios_por_rol() -> list[dict]:
    """
    REPORTE — JOIN: rol + usuarios
 
    Muestra cuántos usuarios activos e inactivos tiene cada rol.
 
    Retorna:
        Lista de dicts con: Rol, Estado, TotalUsuarios
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                r.Descripcion        AS Rol,
                eu.Nombre_Estado     AS Estado,
                COUNT(u.Usuario_ID)  AS TotalUsuarios
            FROM rol r
            LEFT JOIN usuarios u       ON u.Rol_ID    = r.Rol_ID
            LEFT JOIN estado_usuario eu ON u.Estado_ID = eu.Estado_ID
            GROUP BY r.Rol_ID, eu.Estado_ID
            ORDER BY r.Descripcion
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_por_rol] Error: {e}")
        return []
    finally:
        conn.close()