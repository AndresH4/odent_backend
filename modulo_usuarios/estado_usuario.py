"""
modulo_usuarios/estado_usuario.py
==================================
Gestión de la tabla 'estado_usuario'.
Tabla catálogo — sin dependencias externas.
 
Columnas:
    Estado_ID    INTEGER PRIMARY KEY AUTOINCREMENT
    Nombre_Estado VARCHAR(20) NOT NULL
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
 
def create_estado_usuario(nombre: str) -> dict:
    """
    Crea un nuevo estado de usuario.
 
    Parámetros:
        nombre : Nombre del estado (ej: 'Activo', 'Inactivo')
 
    Retorna:
        {'ok': True,  'estado_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO estado_usuario (Nombre_Estado) VALUES (?)", (nombre,)
        )
        conn.commit()
        return {"ok": True, "estado_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_estados() -> list[dict]:
    """
    Retorna todos los estados de usuario.
 
    Retorna:
        Lista de dicts con: Estado_ID, Nombre_Estado
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT Estado_ID, Nombre_Estado FROM estado_usuario ORDER BY Estado_ID"
        ).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_estados] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_estado_by_id(estado_id: int) -> dict | None:
    """
    Busca un estado por su ID.
 
    Parámetros:
        estado_id : ID del estado
 
    Retorna:
        dict con Estado_ID y Nombre_Estado, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT Estado_ID, Nombre_Estado FROM estado_usuario WHERE Estado_ID = ?",
            (estado_id,)
        ).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_estado_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_estado_usuario(estado_id: int, nombre: str) -> dict:
    """
    Actualiza el nombre de un estado.
 
    Parámetros:
        estado_id : ID del estado a actualizar
        nombre    : Nuevo nombre
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE estado_usuario SET Nombre_Estado = ? WHERE Estado_ID = ?",
            (nombre, estado_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Estado {estado_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_estado_usuario(estado_id: int) -> dict:
    """
    Elimina un estado de usuario.
 
    ⚠ Si hay usuarios con este estado, SQLite lanzará error de FK.
 
    Parámetros:
        estado_id : ID del estado a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM estado_usuario WHERE Estado_ID = ?", (estado_id,)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Estado {estado_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTE ──────────────────────────────────────────────────────────────────
 
def reporte_usuarios_activos_vs_inactivos() -> list[dict]:
    """
    REPORTE — JOIN: estado_usuario + usuarios
 
    Muestra el conteo de usuarios activos vs inactivos por rol.
 
    Retorna:
        Lista de dicts con: Estado, Rol, TotalUsuarios
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                eu.Nombre_Estado     AS Estado,
                r.Descripcion        AS Rol,
                COUNT(u.Usuario_ID)  AS TotalUsuarios
            FROM estado_usuario eu
            LEFT JOIN usuarios u ON u.Estado_ID = eu.Estado_ID
            LEFT JOIN rol r      ON u.Rol_ID    = r.Rol_ID
            GROUP BY eu.Estado_ID, r.Rol_ID
            ORDER BY eu.Nombre_Estado, r.Descripcion
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_activos_vs_inactivos] Error: {e}")
        return []
    finally:
        conn.close()