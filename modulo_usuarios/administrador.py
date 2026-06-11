"""
modulo_usuarios/administrador.py
=================================
Gestión de la tabla 'administrador'.
 
Depende de:
    - usuarios (Usuario_ID)
 
Columnas:
    Administrador_ID  INTEGER PRIMARY KEY AUTOINCREMENT
    Usuario_ID        INT NOT NULL → FK usuarios
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
 
def create_administrador(usuario_id: int) -> dict:
    """
    TRANSACCIÓN: Asigna rol Administrador a un usuario existente.
    Actualiza Rol_ID en usuarios y crea el registro en administrador.
 
    Parámetros:
        usuario_id : ID del usuario que será administrador
 
    Retorna:
        {'ok': True,  'administrador_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        # Verificar que el usuario exista
        existe = conn.execute(
            "SELECT Usuario_ID FROM usuarios WHERE Usuario_ID = ?", (usuario_id,)
        ).fetchone()
        if not existe:
            conn.rollback()
            return {"ok": False, "error": f"No existe el usuario con ID {usuario_id}"}
 
        # Actualizar rol a Administrador (Rol_ID = 1)
        conn.execute(
            "UPDATE usuarios SET Rol_ID = 1 WHERE Usuario_ID = ?", (usuario_id,)
        )
 
        # Crear registro en administrador
        cursor = conn.execute(
            "INSERT INTO administrador (Usuario_ID) VALUES (?)", (usuario_id,)
        )
        admin_id = cursor.lastrowid
 
        # Auditoría
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 2, date('now'), 'Asignado como Administrador')
        """, (usuario_id,))
 
        conn.commit()
        return {"ok": True, "administrador_id": admin_id}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_administradores() -> list[dict]:
    """
    JOIN: administrador + usuarios + estado_usuario
 
    Retorna todos los administradores con sus datos de usuario.
 
    Retorna:
        Lista de dicts con: Administrador_ID, Usuario_ID, Nombres,
                            Apellidos, Correo, Telefono, Estado
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                a.Administrador_ID,
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.Correo,
                u.Telefono,
                eu.Nombre_Estado AS Estado
            FROM administrador a
            JOIN usuarios u        ON a.Usuario_ID = u.Usuario_ID
            JOIN estado_usuario eu ON u.Estado_ID  = eu.Estado_ID
            ORDER BY u.Apellidos
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_administradores] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_administrador_by_id(admin_id: int) -> dict | None:
    """
    Busca un administrador por su ID con datos de usuario.
 
    Parámetros:
        admin_id : ID del administrador
 
    Retorna:
        dict con datos completos, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                a.Administrador_ID,
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.Correo,
                u.Telefono,
                eu.Nombre_Estado AS Estado
            FROM administrador a
            JOIN usuarios u        ON a.Usuario_ID = u.Usuario_ID
            JOIN estado_usuario eu ON u.Estado_ID  = eu.Estado_ID
            WHERE a.Administrador_ID = ?
        """, (admin_id,)).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_administrador_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_administrador(admin_id: int, nuevo_usuario_id: int) -> dict:
    """
    Reasigna el administrador a otro usuario.
 
    Parámetros:
        admin_id         : ID del registro de administrador
        nuevo_usuario_id : Nuevo usuario_id para este administrador
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE administrador SET Usuario_ID = ? WHERE Administrador_ID = ?",
            (nuevo_usuario_id, admin_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Administrador {admin_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_administrador(admin_id: int) -> dict:
    """
    Elimina el registro de administrador.
 
    Parámetros:
        admin_id : ID del administrador a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM administrador WHERE Administrador_ID = ?", (admin_id,)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Administrador {admin_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTE ──────────────────────────────────────────────────────────────────
 
def reporte_administradores_activos() -> list[dict]:
    """
    REPORTE — JOIN: administrador + usuarios + estado_usuario
 
    Lista de administradores activos en el sistema.
 
    Retorna:
        Lista de dicts con: NombreCompleto, Correo, Telefono, Estado
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                u.Nombres || ' ' || u.Apellidos AS NombreCompleto,
                u.Correo,
                u.Telefono,
                eu.Nombre_Estado AS Estado
            FROM administrador a
            JOIN usuarios u        ON a.Usuario_ID = u.Usuario_ID
            JOIN estado_usuario eu ON u.Estado_ID  = eu.Estado_ID
            WHERE eu.Nombre_Estado = 'Activo'
            ORDER BY u.Apellidos
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_administradores_activos] Error: {e}")
        return []
    finally:
        conn.close()