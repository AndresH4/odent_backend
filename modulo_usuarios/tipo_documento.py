"""
modulo_usuarios/tipo_documento.py
==================================
Gestión de la tabla 'tipo_documento'.
Tabla catálogo — sin dependencias externas.
 
Columnas:
    TipoDoc_ID              INTEGER PRIMARY KEY AUTOINCREMENT
    Nombre_Tipo_Documento   VARCHAR(50) NOT NULL
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
 
def create_tipo_documento(nombre: str) -> dict:
    """
    Crea un nuevo tipo de documento.
 
    Parámetros:
        nombre : Nombre del tipo (ej: 'Cedula de ciudadania')
 
    Retorna:
        {'ok': True,  'tipodoc_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO tipo_documento (Nombre_Tipo_Documento) VALUES (?)", (nombre,)
        )
        conn.commit()
        return {"ok": True, "tipodoc_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_tipos_documento() -> list[dict]:
    """
    Retorna todos los tipos de documento.
 
    Retorna:
        Lista de dicts con: TipoDoc_ID, Nombre_Tipo_Documento
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT TipoDoc_ID, Nombre_Tipo_Documento FROM tipo_documento ORDER BY TipoDoc_ID"
        ).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_tipos_documento] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_tipo_documento_by_id(tipodoc_id: int) -> dict | None:
    """
    Busca un tipo de documento por su ID.
 
    Parámetros:
        tipodoc_id : ID del tipo de documento
 
    Retorna:
        dict con TipoDoc_ID y Nombre_Tipo_Documento, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT TipoDoc_ID, Nombre_Tipo_Documento FROM tipo_documento WHERE TipoDoc_ID = ?",
            (tipodoc_id,)
        ).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_tipo_documento_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_tipo_documento(tipodoc_id: int, nombre: str) -> dict:
    """
    Actualiza el nombre de un tipo de documento.
 
    Parámetros:
        tipodoc_id : ID del tipo de documento
        nombre     : Nuevo nombre
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE tipo_documento SET Nombre_Tipo_Documento = ? WHERE TipoDoc_ID = ?",
            (nombre, tipodoc_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Tipo de documento {tipodoc_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_tipo_documento(tipodoc_id: int) -> dict:
    """
    Elimina un tipo de documento.
 
    ⚠ Si hay usuarios usando este tipo de documento, SQLite lanzará error de FK.
 
    Parámetros:
        tipodoc_id : ID del tipo de documento a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM tipo_documento WHERE TipoDoc_ID = ?", (tipodoc_id,)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Tipo de documento {tipodoc_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTE ──────────────────────────────────────────────────────────────────
 
def reporte_usuarios_por_tipo_documento() -> list[dict]:
    """
    REPORTE — JOIN: tipo_documento + usuarios
 
    Muestra cuántos usuarios hay por tipo de documento.
 
    Retorna:
        Lista de dicts con: TipoDocumento, TotalUsuarios
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                td.Nombre_Tipo_Documento AS TipoDocumento,
                COUNT(u.Usuario_ID)      AS TotalUsuarios
            FROM tipo_documento td
            LEFT JOIN usuarios u ON u.TipoDoc_ID = td.TipoDoc_ID
            GROUP BY td.TipoDoc_ID
            ORDER BY TotalUsuarios DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_por_tipo_documento] Error: {e}")
        return []
    finally:
        conn.close()