"""
modulo_usuarios/usuario.py
==========================
Gestión de la tabla 'usuarios'.
 
Depende de:
    - rol               (Rol_ID)
    - estado_usuario    (Estado_ID)
    - genero            (Genero_ID)
    - tipo_documento    (TipoDoc_ID)
    - afiliacion        (LEFT JOIN para perfil completo)
    - eps               (LEFT JOIN para perfil completo)
 
Columnas:
    Usuario_ID       INTEGER PRIMARY KEY AUTOINCREMENT
    Nombres          VARCHAR(50) NOT NULL
    Apellidos        VARCHAR(50) NOT NULL
    TipoDoc_ID       INT NOT NULL  → FK tipo_documento
    NumeroDocumento  VARCHAR(15) NOT NULL
    Contrasena       VARCHAR(100) NOT NULL
    FechaNacimiento  DATE NOT NULL
    Genero_ID        INT NOT NULL  → FK genero
    Correo           VARCHAR(100) NOT NULL
    Telefono         VARCHAR(15) NOT NULL
    Estado_ID        INT NOT NULL  → FK estado_usuario
    Rol_ID           INT NOT NULL  → FK rol
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
 
def create_usuario(
    nombres: str,
    apellidos: str,
    tipodoc_id: int,
    numero_documento: str,
    contrasena: str,
    fecha_nacimiento: str,
    genero_id: int,
    correo: str,
    telefono: str,
    rol_id: int,
    estado_id: int = 1
) -> dict:
    """
    TRANSACCIÓN: Crea un usuario y registra automáticamente su alta
    en aseguramiento_datos con acción 'Asegurar' (Accion_ID = 1).
 
    Si falla cualquiera de las dos inserciones se hace rollback completo.
 
    Parámetros:
        nombres          : Nombres del usuario
        apellidos        : Apellidos del usuario
        tipodoc_id       : FK tipo_documento
        numero_documento : Número de documento
        contrasena       : Contraseña (en producción: hashear con bcrypt)
        fecha_nacimiento : Formato 'YYYY-MM-DD'
        genero_id        : FK genero
        correo           : Correo electrónico
        telefono         : Teléfono de contacto
        rol_id           : FK rol (1=Admin, 2=Especialista, 3=Paciente)
        estado_id        : FK estado_usuario (por defecto 1 = Activo)
 
    Retorna:
        {'ok': True,  'usuario_id': int}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        cursor = conn.execute("""
            INSERT INTO usuarios (
                Nombres, Apellidos, TipoDoc_ID, NumeroDocumento,
                Contrasena, FechaNacimiento, Genero_ID, Correo,
                Telefono, Estado_ID, Rol_ID
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nombres, apellidos, tipodoc_id, numero_documento,
            contrasena, fecha_nacimiento, genero_id, correo,
            telefono, estado_id, rol_id
        ))
        nuevo_id = cursor.lastrowid
 
        # Registrar alta en auditoría
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 1, date('now'), 'Registro inicial de usuario')
        """, (nuevo_id,))
 
        conn.commit()
        return {"ok": True, "usuario_id": nuevo_id}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── READ ALL ─────────────────────────────────────────────────────────────────
 
def read_all_usuarios() -> list[dict]:
    """
    JOIN: usuarios + rol + estado_usuario + genero + tipo_documento
 
    Retorna todos los usuarios con nombres legibles en lugar de IDs.
    Ideal para la tabla principal del frontend.
 
    Retorna:
        Lista de dicts con: Usuario_ID, Nombres, Apellidos, NumeroDocumento,
        Correo, Telefono, FechaNacimiento, Rol, Estado, Genero, TipoDocumento
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.FechaNacimiento,
                r.Descripcion            AS Rol,
                eu.Nombre_Estado         AS Estado,
                g.NombreGenero           AS Genero,
                td.Nombre_Tipo_Documento AS TipoDocumento
            FROM usuarios u
            JOIN rol r              ON u.Rol_ID     = r.Rol_ID
            JOIN estado_usuario eu  ON u.Estado_ID  = eu.Estado_ID
            JOIN genero g           ON u.Genero_ID  = g.Genero_ID
            JOIN tipo_documento td  ON u.TipoDoc_ID = td.TipoDoc_ID
            ORDER BY u.Apellidos, u.Nombres
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[read_all_usuarios] Error: {e}")
        return []
    finally:
        conn.close()
 
 
# ─── READ BY ID ───────────────────────────────────────────────────────────────
 
def read_usuario_by_id(usuario_id: int) -> dict | None:
    """
    JOIN completo: usuarios + rol + estado_usuario + genero +
                   tipo_documento + afiliacion + eps + regimen_eps + tipo_eps
 
    Retorna el perfil completo del usuario incluyendo su EPS si tiene.
 
    Parámetros:
        usuario_id : ID del usuario
 
    Retorna:
        dict con todos los datos, o None si no existe
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.NumeroDocumento,
                u.Correo,
                u.Telefono,
                u.FechaNacimiento,
                r.Descripcion            AS Rol,
                eu.Nombre_Estado         AS Estado,
                g.NombreGenero           AS Genero,
                td.Nombre_Tipo_Documento AS TipoDocumento,
                e.Nombre_EPS             AS EPS,
                re.Descripcion           AS RegimenEPS,
                te.Nombre_Tipo           AS TipoEPS,
                a.Fecha_Afiliacion
            FROM usuarios u
            JOIN rol r              ON u.Rol_ID     = r.Rol_ID
            JOIN estado_usuario eu  ON u.Estado_ID  = eu.Estado_ID
            JOIN genero g           ON u.Genero_ID  = g.Genero_ID
            JOIN tipo_documento td  ON u.TipoDoc_ID = td.TipoDoc_ID
            LEFT JOIN afiliacion a  ON a.Usuario_ID = u.Usuario_ID
            LEFT JOIN eps e         ON a.EPS_ID     = e.EPS_ID
            LEFT JOIN regimen_eps re ON e.Regimen_ID = re.Regimen_ID
            LEFT JOIN tipo_eps te   ON a.TipoEPS_ID = te.TipoEPS_ID
            WHERE u.Usuario_ID = ?
        """, (usuario_id,)).fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[read_usuario_by_id] Error: {e}")
        return None
    finally:
        conn.close()
 
 
def login_usuario(correo: str, contrasena: str) -> dict:
    """
    Valida las credenciales del usuario.
 
    Retorna el Usuario_ID y Rol_ID para que el frontend
    sepa a qué pantalla redirigir tras el login.
 
    Parámetros:
        correo     : Correo del usuario
        contrasena : Contraseña
 
    Retorna:
        {'ok': True,  'usuario': dict}   → credenciales válidas
        {'ok': False, 'error': str}      → credenciales incorrectas o inactivo
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres,
                u.Apellidos,
                u.Correo,
                u.Rol_ID,
                r.Descripcion       AS Rol,
                eu.Nombre_Estado    AS Estado
            FROM usuarios u
            JOIN rol r             ON u.Rol_ID    = r.Rol_ID
            JOIN estado_usuario eu ON u.Estado_ID = eu.Estado_ID
            WHERE u.Correo = ? AND u.Contrasena = ?
        """, (correo, contrasena)).fetchone()
 
        if not row:
            return {"ok": False, "error": "Correo o contraseña incorrectos"}
 
        usuario = dict(row)
        if usuario["Estado"].lower() != "activo":
            return {"ok": False, "error": "Usuario inactivo. Contacte al administrador"}
 
        return {"ok": True, "usuario": usuario}
 
    except Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── UPDATE ───────────────────────────────────────────────────────────────────
 
def update_usuario(
    usuario_id: int,
    nombres: str,
    apellidos: str,
    tipodoc_id: int,
    numero_documento: str,
    fecha_nacimiento: str,
    genero_id: int,
    correo: str,
    telefono: str
) -> dict:
    """
    TRANSACCIÓN: Actualiza los datos personales del usuario y registra
    la acción en aseguramiento_datos con 'Actualizar' (Accion_ID = 2).
 
    No modifica rol, estado ni contraseña (tienen sus propias funciones).
 
    Parámetros:
        usuario_id       : ID del usuario a actualizar
        nombres          : Nuevos nombres
        apellidos        : Nuevos apellidos
        tipodoc_id       : FK tipo_documento
        numero_documento : Nuevo número de documento
        fecha_nacimiento : Nueva fecha 'YYYY-MM-DD'
        genero_id        : FK genero
        correo           : Nuevo correo
        telefono         : Nuevo teléfono
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        conn.execute("""
            UPDATE usuarios SET
                Nombres         = ?,
                Apellidos       = ?,
                TipoDoc_ID      = ?,
                NumeroDocumento = ?,
                FechaNacimiento = ?,
                Genero_ID       = ?,
                Correo          = ?,
                Telefono        = ?
            WHERE Usuario_ID = ?
        """, (
            nombres, apellidos, tipodoc_id, numero_documento,
            fecha_nacimiento, genero_id, correo, telefono,
            usuario_id
        ))
 
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 2, date('now'), 'Actualización de datos personales')
        """, (usuario_id,))
 
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario {usuario_id} actualizado"}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
def update_contrasena(usuario_id: int, contrasena_actual: str, contrasena_nueva: str) -> dict:
    """
    TRANSACCIÓN: Cambia la contraseña validando primero la actual.
 
    Parámetros:
        usuario_id        : ID del usuario
        contrasena_actual : Contraseña actual para verificación
        contrasena_nueva  : Nueva contraseña
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        existe = conn.execute("""
            SELECT Usuario_ID FROM usuarios
            WHERE Usuario_ID = ? AND Contrasena = ?
        """, (usuario_id, contrasena_actual)).fetchone()
 
        if not existe:
            conn.rollback()
            return {"ok": False, "error": "La contraseña actual es incorrecta"}
 
        conn.execute("""
            UPDATE usuarios SET Contrasena = ? WHERE Usuario_ID = ?
        """, (contrasena_nueva, usuario_id))
 
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 2, date('now'), 'Cambio de contraseña')
        """, (usuario_id,))
 
        conn.commit()
        return {"ok": True, "mensaje": "Contraseña actualizada correctamente"}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
def update_estado(usuario_id: int, nuevo_estado_id: int, descripcion: str = "") -> dict:
    """
    TRANSACCIÓN: Cambia el estado de un usuario y deja trazabilidad.
 
    Usar para activar o desactivar usuarios sin eliminarlos.
 
    Parámetros:
        usuario_id      : ID del usuario
        nuevo_estado_id : FK estado_usuario
        descripcion     : Motivo opcional del cambio
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        conn.execute("""
            UPDATE usuarios SET Estado_ID = ? WHERE Usuario_ID = ?
        """, (nuevo_estado_id, usuario_id))
 
        estado = conn.execute("""
            SELECT Nombre_Estado FROM estado_usuario WHERE Estado_ID = ?
        """, (nuevo_estado_id,)).fetchone()
        nombre_estado = estado["Nombre_Estado"] if estado else str(nuevo_estado_id)
 
        desc = descripcion or f"Cambio de estado a: {nombre_estado}"
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 2, date('now'), ?)
        """, (usuario_id, desc))
 
        conn.commit()
        return {"ok": True, "mensaje": f"Estado actualizado a '{nombre_estado}'"}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── DELETE ───────────────────────────────────────────────────────────────────
 
def delete_usuario(usuario_id: int) -> dict:
    """
    TRANSACCIÓN: Registra la eliminación en auditoría ANTES de borrar.
 
    ⚠ Si el usuario tiene citas, historial o multas vinculadas,
    SQLite lanzará error de FK y se hará rollback automático.
    En ese caso usa update_estado() para desactivarlo en su lugar.
 
    Parámetros:
        usuario_id : ID del usuario a eliminar
 
    Retorna:
        {'ok': True,  'mensaje': str}
        {'ok': False, 'error': str}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN TRANSACTION;")
 
        existe = conn.execute("""
            SELECT Nombres, Apellidos FROM usuarios WHERE Usuario_ID = ?
        """, (usuario_id,)).fetchone()
 
        if not existe:
            conn.rollback()
            return {"ok": False, "error": f"No existe el usuario con ID {usuario_id}"}
 
        nombre_completo = f"{existe['Nombres']} {existe['Apellidos']}"
 
        # Auditoría ANTES de eliminar (Accion_ID = 3 → 'Eliminar')
        conn.execute("""
            INSERT INTO aseguramiento_datos (Usuario_ID, Accion_ID, Fecha, Descripcion)
            VALUES (?, 3, date('now'), ?)
        """, (usuario_id, f"Eliminación del usuario: {nombre_completo}"))
 
        conn.execute("DELETE FROM usuarios WHERE Usuario_ID = ?", (usuario_id,))
 
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario '{nombre_completo}' eliminado"}
 
    except Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
 
 
# ─── REPORTES ─────────────────────────────────────────────────────────────────
 
def reporte_usuarios_por_rol_y_estado() -> list[dict]:
    """
    REPORTE — JOIN: usuarios + rol + estado_usuario
 
    Distribución de usuarios por rol y estado.
    Útil para el dashboard del administrador.
 
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
            FROM usuarios u
            JOIN rol r             ON u.Rol_ID    = r.Rol_ID
            JOIN estado_usuario eu ON u.Estado_ID = eu.Estado_ID
            GROUP BY r.Rol_ID, eu.Estado_ID
            ORDER BY r.Descripcion, eu.Nombre_Estado
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_por_rol_y_estado] Error: {e}")
        return []
    finally:
        conn.close()
 
 
def reporte_usuarios_sin_afiliacion() -> list[dict]:
    """
    REPORTE — JOIN: usuarios + rol (filtro Paciente) + afiliacion (ausencia)
 
    Pacientes que no tienen afiliación a ninguna EPS registrada.
    Útil para identificar registros incompletos.
 
    Retorna:
        Lista de dicts con: Usuario_ID, NombreCompleto, Correo, Telefono
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres || ' ' || u.Apellidos AS NombreCompleto,
                u.Correo,
                u.Telefono
            FROM usuarios u
            JOIN rol r ON u.Rol_ID = r.Rol_ID
            WHERE r.Descripcion = 'Paciente'
              AND u.Usuario_ID NOT IN (
                  SELECT DISTINCT Usuario_ID FROM afiliacion
              )
            ORDER BY u.Apellidos
        """).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_usuarios_sin_afiliacion] Error: {e}")
        return []
    finally:
        conn.close()
 
 
def reporte_actividad_reciente(dias: int = 30) -> list[dict]:
    """
    REPORTE — JOIN: usuarios + aseguramiento_datos + accion_aseguramiento
 
    Usuarios con actividad registrada en los últimos N días.
    Útil para monitoreo de seguridad y onboarding.
 
    Parámetros:
        dias : Días hacia atrás a consultar (por defecto 30)
 
    Retorna:
        Lista de dicts con: NombreCompleto, Correo, Rol,
                            TotalAcciones, UltimaAccion, UltimaFecha
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT
                u.Nombres || ' ' || u.Apellidos AS NombreCompleto,
                u.Correo,
                r.Descripcion                   AS Rol,
                COUNT(ad.AseguramientoDatos_ID)  AS TotalAcciones,
                MAX(ac.Nombre_Accion)            AS UltimaAccion,
                MAX(ad.Fecha)                    AS UltimaFecha
            FROM aseguramiento_datos ad
            JOIN usuarios u              ON ad.Usuario_ID = u.Usuario_ID
            JOIN rol r                   ON u.Rol_ID      = r.Rol_ID
            JOIN accion_aseguramiento ac ON ad.Accion_ID  = ac.Accion_ID
            WHERE ad.Fecha >= date('now', ? || ' days')
            GROUP BY u.Usuario_ID
            ORDER BY UltimaFecha DESC
        """, (f"-{dias}",)).fetchall()
        return [dict(r) for r in rows]
    except Error as e:
        print(f"[reporte_actividad_reciente] Error: {e}")
        return []
    finally:
        conn.close()