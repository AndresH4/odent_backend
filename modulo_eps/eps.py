"""
modulo_eps/eps.py
-----------------
Gestión de entidades EPS.
Depende de la tabla `regimen_eps`.
El READ incluye un JOIN para retornar la descripción del régimen en lugar
de solo el ID foráneo.
 
Columnas de `eps`: EPS_ID (PK), Nombre_EPS, Telefono_EPS, Regimen_ID (FK → regimen_eps)
"""
 
import sqlite3
 
DB_PATH = "odent.db"
 
 
def _get_conn():
    """Abre y configura la conexión a odent.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn
 
 
# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────
def crear_eps(nombre_eps: str, telefono_eps: str, regimen_id: int) -> dict:
    """
    Inserta una nueva EPS en la tabla `eps`.
 
    Args:
        nombre_eps:   Nombre de la EPS (ej. 'Compensar').
        telefono_eps: Teléfono de contacto de la EPS.
        regimen_id:   FK hacia `regimen_eps` (Contributivo / Subsidiado).
 
    Returns:
        {'ok': True, 'id_generado': int} en éxito.
        {'ok': False, 'error': str}       en fallo.
    """
    sql = """
        INSERT INTO eps (Nombre_EPS, Telefono_EPS, Regimen_ID)
        VALUES (?, ?, ?);
    """
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, (nombre_eps, telefono_eps, regimen_id))
        conn.commit()
        return {"ok": True, "id_generado": cursor.lastrowid}
    except sqlite3.Error as e:
        print(f"[eps][crear] Error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()
 
 
# ─────────────────────────────────────────────
# READ ALL  (con JOIN a regimen_eps)
# ─────────────────────────────────────────────
def obtener_eps() -> list:
    """
    Retorna todas las EPS registradas, enriquecidas con la descripción
    de su régimen mediante un JOIN a `regimen_eps`.
 
    Returns:
        Lista de dicts con:
            {EPS_ID, Nombre_EPS, Telefono_EPS, Regimen_ID, Descripcion_Regimen}
        Lista vacía [] si no hay registros o si ocurre un error.
    """
    sql = """
        SELECT
            e.EPS_ID,
            e.Nombre_EPS,
            e.Telefono_EPS,
            e.Regimen_ID,
            r.Descripcion AS Descripcion_Regimen
        FROM eps e
        INNER JOIN regimen_eps r ON e.Regimen_ID = r.Regimen_ID
        ORDER BY e.EPS_ID;
    """
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[eps][obtener_todos] Error: {e}")
        return []
    finally:
        if conn:
            conn.close()
 
 
# ─────────────────────────────────────────────
# READ BY ID  (con JOIN a regimen_eps)
# ─────────────────────────────────────────────
def obtener_eps_por_id(eps_id: int) -> dict | None:
    """
    Busca una EPS por su clave primaria, incluyendo la descripción del régimen.
 
    Args:
        eps_id: Identificador único de la EPS.
 
    Returns:
        Dict con los datos del registro (incluye Descripcion_Regimen),
        o None si no existe o si ocurre un error.
    """
    sql = """
        SELECT
            e.EPS_ID,
            e.Nombre_EPS,
            e.Telefono_EPS,
            e.Regimen_ID,
            r.Descripcion AS Descripcion_Regimen
        FROM eps e
        INNER JOIN regimen_eps r ON e.Regimen_ID = r.Regimen_ID
        WHERE e.EPS_ID = ?;
    """
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, (eps_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[eps][obtener_por_id] Error: {e}")
        return None
    finally:
        if conn:
            conn.close()
 
 
# ─────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────
def actualizar_eps(eps_id: int, nombre_eps: str, telefono_eps: str, regimen_id: int) -> dict:
    """
    Actualiza los datos de una EPS existente.
 
    Args:
        eps_id:       ID del registro a modificar.
        nombre_eps:   Nuevo nombre de la EPS.
        telefono_eps: Nuevo teléfono de la EPS.
        regimen_id:   Nuevo ID de régimen (FK → regimen_eps).
 
    Returns:
        {'ok': True,  'mensaje': str} si se actualizó al menos 1 fila.
        {'ok': False, 'error': str}   si no existe o falla la consulta.
    """
    sql = """
        UPDATE eps
        SET Nombre_EPS   = ?,
            Telefono_EPS = ?,
            Regimen_ID   = ?
        WHERE EPS_ID = ?;
    """
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, (nombre_eps, telefono_eps, regimen_id, eps_id))
        conn.commit()
        if cursor.rowcount == 0:
            return {"ok": False, "error": f"No existe eps con ID {eps_id}."}
        return {"ok": True, "mensaje": f"eps ID {eps_id} actualizada correctamente."}
    except sqlite3.Error as e:
        print(f"[eps][actualizar] Error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()
 
 
# ─────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────
def eliminar_eps(eps_id: int) -> dict:
    """
    Elimina una EPS por ID.
    Fallará si existen afiliaciones que referencian esta EPS (FK activa).
 
    Args:
        eps_id: ID del registro a eliminar.
 
    Returns:
        {'ok': True,  'mensaje': str} si se eliminó correctamente.
        {'ok': False, 'error': str}   si hay dependencias o no existe.
    """
    sql = "DELETE FROM eps WHERE EPS_ID = ?;"
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, (eps_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"ok": False, "error": f"No existe eps con ID {eps_id}."}
        return {"ok": True, "mensaje": f"eps ID {eps_id} eliminada correctamente."}
    except sqlite3.Error as e:
        print(f"[eps][eliminar] Error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()