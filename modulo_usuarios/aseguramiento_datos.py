"""
modulo_usuarios/aseguramiento_datos.py
=======================================
Gestión de la tabla 'aseguramiento_datos'.
Registra todas las acciones realizadas sobre los usuarios (auditoría).
 
Depende de:
    - usuarios              (Usuario_ID)
    - accion_aseguramiento  (Accion_ID)
 
Columnas:
    AseguramientoDatos_ID  INTEGER PRIMARY KEY AUTOINCREMENT
    Usuario_ID             INT NOT NULL  → FK usuarios
    Accion_ID              INT NOT NULL  → FK accion_aseguramiento
    Fecha                  DATE NOT NULL
    Descripcion            TEXT NOT NULL
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
 
def create_aseguramiento(usuario_id: int, accion_id: int, descripcion: str) -> dict:
    """
    Registra una nueva acción de auditoría para un usuario.
 
    Generalmente llamado automáticamente desde usuario.py en cada
    operación. Se expone también para registros manuales del admin.
 
    Parámetros:
        usuario_id  : FK usuarios
        accion_id   : FK accion_aseguramiento (1=Asegurar, 2=Actualizar, 3=Eliminar)
        descripcion : Detalle de la acción realizada
 
    Retorna:
        {'ok': True,  'aseguramiento_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, ?, date('now'), ?)
        """, (usuario_id, accion_id, descripcion))
        conn.commit()
        return {"ok": True, "aseguramiento_id": cursor.lastrowid}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_aseguramientos() -> list[dict]:
    """
    JOIN: aseguramiento_datos + usuarios + accion_aseguramiento
 
    Retorna toda la auditoría del sistema ordenada del más reciente.
 
    Retorna:
        Lista de dicts con: AseguramientoDatos_ID, Fecha, NombreUsuario,
                            Correo, Accion, Descripcion
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ad.AseguramientoDatos_ID,
                ad.Fecha,
                u.Nombres || ' ' || u.Apellidos AS NombreUsuario,
                u.Correo,
                ac.Nombre_Accion                AS Accion,
                ad.Descripcion
            FROM aseguramiento_datos ad
            JOIN usuarios u              ON ad.Usuario_ID = u.Usuario_ID
            JOIN accion_aseguramiento ac ON ad.Accion_ID  = ac.Accion_ID
            ORDER BY ad.Fecha DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_aseguramientos] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY USUARIO ──────────────────────────────────────────────────────────
 
def read_aseguramiento_by_usuario(usuario_id: int) -> list[dict]:
    """
    JOIN: aseguramiento_datos + accion_aseguramiento
 
    Historial de auditoría de un usuario específico.
 
    Parámetros:
        usuario_id : ID del usuario
 
    Retorna:
        Lista de dicts con: Fecha, Accion, Descripcion
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ad.AseguramientoDatos_ID,
                ad.Fecha,
                ac.Nombre_Accion AS Accion,
                ad.Descripcion
            FROM aseguramiento_datos ad
            JOIN accion_aseguramiento ac ON ad.Accion_ID = ac.Accion_ID
            WHERE ad.Usuario_ID = ?
            ORDER BY ad.Fecha DESC
        """, (usuario_id,)).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_aseguramiento_by_usuario] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_aseguramiento_by_id(aseg_id: int) -> dict | None:
    """Busca un registro de auditoría por su ID."""
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                ad.AseguramientoDatos_ID,
                ad.Fecha,
                u.Nombres || ' ' || u.Apellidos AS NombreUsuario,
                ac.Nombre_Accion                AS Accion,
                ad.Descripcion
            FROM aseguramiento_datos ad
            JOIN usuarios u              ON ad.Usuario_ID = u.Usuario_ID
            JOIN accion_aseguramiento ac ON ad.Accion_ID  = ac.Accion_ID
            WHERE ad.AseguramientoDatos_ID = ?
        """, (aseg_id,)).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_aseguramiento_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_aseguramiento(aseg_id: int, descripcion: str) -> dict:
    """
    Actualiza la descripción de un registro de auditoría.
 
    Parámetros:
        aseg_id     : ID del registro de auditoría
        descripcion : Nueva descripción
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("""
            UPDATE aseguramiento_datos SET Descripcion = ?
            WHERE AseguramientoDatos_ID = ?
        """, (descripcion, aseg_id))
        conn.commit()
        return {"ok": True, "mensaje": f"Registro {aseg_id} actualizado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_aseguramiento(aseg_id: int) -> dict:
    """
    Elimina un registro de auditoría.
 
    Parámetros:
        aseg_id : ID del registro a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM aseguramiento_datos WHERE AseguramientoDatos_ID = ?", (aseg_id,)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Registro de auditoría {aseg_id} eliminado"}
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTES ─────────────────────────────────────────────────────────────────
 
def reporte_acciones_por_tipo() -> list[dict]:
    """
    REPORTE — JOIN: aseguramiento_datos + accion_aseguramiento
 
    Conteo de cuántas veces se ha ejecutado cada tipo de acción.
 
    Retorna:
        Lista de dicts con: Accion, TotalEjecuciones
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ac.Nombre_Accion          AS Accion,
                COUNT(ad.AseguramientoDatos_ID) AS TotalEjecuciones
            FROM accion_aseguramiento ac
            LEFT JOIN aseguramiento_datos ad ON ad.Accion_ID = ac.Accion_ID
            GROUP BY ac.Accion_ID
            ORDER BY TotalEjecuciones DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_acciones_por_tipo] Error: {e}")
        return []
    finally:
        conn.close()
 
 
def reporte_auditoria_por_fecha(fecha_desde: str, fecha_hasta: str) -> list[dict]:
    """
    REPORTE — Auditoría filtrada por rango de fechas.
 
    Parámetros:
        fecha_desde : Fecha inicio 'YYYY-MM-DD'
        fecha_hasta : Fecha fin 'YYYY-MM-DD'
 
    Retorna:
        Lista de dicts con: Fecha, NombreUsuario, Accion, Descripcion
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ad.Fecha,
                u.Nombres || ' ' || u.Apellidos AS NombreUsuario,
                ac.Nombre_Accion                AS Accion,
                ad.Descripcion
            FROM aseguramiento_datos ad
            JOIN usuarios u              ON ad.Usuario_ID = u.Usuario_ID
            JOIN accion_aseguramiento ac ON ad.Accion_ID  = ac.Accion_ID
            WHERE ad.Fecha BETWEEN ? AND ?
            ORDER BY ad.Fecha DESC
        """, (fecha_desde, fecha_hasta)).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_auditoria_por_fecha] Error: {e}")
        return []
    finally:
        conn.close()