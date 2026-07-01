# =============================================================================
# modulo_config_ranking/config_ranking.py  —  VERSIÓN CORREGIDA (v2)
# Lógica de negocio para la tabla config_ranking.
#
# IMPORTANTE: get_db_connection() en db.py YA garantiza, en cada conexión,
# que la tabla config_ranking existe, tiene la columna Estado, y contiene
# la fila semilla Config_ID=1 (ver _asegurar_config_ranking en db.py).
# Por lo tanto este módulo NO repite esa creación/migración — solo confía
# en que la fila existe al momento de leer/escribir, y sigue verificando
# rowcount + relectura para detectar cualquier fallo silencioso residual
# (por ejemplo, si alguien más borra la fila entre la conexión y el UPDATE).
#
# La tabla tiene UNA sola fila de configuración (Config_ID = 1).
# El campo Estado admite únicamente: 1 = Activo, 2 = Inactivo.
# =============================================================================

from db import get_db_connection

_CONFIG_ID       = 1
_ESTADOS_VALIDOS = {1, 2}
_LABEL_ESTADO    = {1: "Activo", 2: "Inactivo"}


# ---------------------------------------------------------------------------
# LECTURA
# ---------------------------------------------------------------------------

def obtener_config() -> dict | None:
    """
    Devuelve el registro único de config_ranking como dict.

    Gracias a _asegurar_config_ranking() en db.py, esta función normalmente
    NUNCA debería devolver None (la fila siempre se crea al conectar). Aun
    así se conserva el chequeo de None por robustez ante escenarios
    inesperados (por ejemplo, otra conexión concurrente borrando la fila).
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = ?",
            (_CONFIG_ID,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        data = dict(row)
        data["Nombre_Estado"] = _LABEL_ESTADO.get(data["Estado"], "Desconocido")
        return data
    finally:
        if con:
            con.close()


# ---------------------------------------------------------------------------
# ACTUALIZACIÓN
# ---------------------------------------------------------------------------

def actualizar_config(nuevo_estado: int) -> dict:
    """
    Actualiza el campo Estado del registro único (Config_ID = 1).

    Como get_db_connection() ya garantiza la existencia de la fila antes de
    llegar aquí, este UPDATE debería afectar siempre exactamente 1 fila.
    Se mantienen las verificaciones explícitas de rowcount y relectura
    porque son las que exponen fallos que antes eran silenciosos:
      - rowcount == 0 tras un UPDATE con WHERE Config_ID=1 indica que la fila
        desapareció entre la conexión y este punto (condición de carrera o
        alguien la borró manualmente).
      - la relectura tras commit() detecta si se está escribiendo en un
        archivo .db distinto al que se lee (dos procesos con distinto cwd,
        por ejemplo).

    Parámetros
    ----------
    nuevo_estado : int
        1 = Activo  |  2 = Inactivo

    Retorna
    -------
    dict con los campos actualizados o lanza ValueError / RuntimeError.
    """
    if nuevo_estado not in _ESTADOS_VALIDOS:
        raise ValueError(
            f"Estado inválido: '{nuevo_estado}'. Use 1 (Activo) o 2 (Inactivo)."
        )

    con = None
    try:
        # get_db_connection() ya corre _asegurar_config_ranking(): al salir
        # de esta línea, Config_ID=1 existe (creada si hacía falta).
        con = get_db_connection()
        cur = con.cursor()

        cur.execute(
            "UPDATE config_ranking SET Estado = ? WHERE Config_ID = ?",
            (nuevo_estado, _CONFIG_ID)
        )
        con.commit()

        if cur.rowcount == 0:
            # Esto solo puede ocurrir si la fila fue eliminada por otra
            # conexión justo después de _asegurar_config_ranking() y antes
            # de este UPDATE. Es un caso extremadamente raro, pero ya no
            # falla en silencio: se reporta explícitamente.
            raise RuntimeError(
                "El UPDATE no afectó ninguna fila (Config_ID=1 no encontrada "
                "en el momento de escribir). Verifica que ningún otro proceso "
                "esté eliminando filas de config_ranking concurrentemente."
            )

        # Verificación de relectura: confirma que lo escrito es lo que se lee.
        # Si esto falla, es señal casi segura de estar leyendo/escribiendo
        # en DOS ARCHIVOS DE BASE DE DATOS DISTINTOS.
        cur.execute(
            "SELECT Estado FROM config_ranking WHERE Config_ID = ?",
            (_CONFIG_ID,)
        )
        confirmado = cur.fetchone()
        if confirmado is None or confirmado["Estado"] != nuevo_estado:
            raise RuntimeError(
                "Inconsistencia tras commit: el valor leído no coincide con "
                "el valor escrito. Revisa que DB_FILE en db.py apunte siempre "
                "al mismo archivo .db sin importar el directorio de trabajo "
                "desde el que se ejecuta la app (usa una ruta absoluta si "
                "el proceso puede lanzarse desde distintos cwd)."
            )

        return {
            "Config_ID":     _CONFIG_ID,
            "Estado":        nuevo_estado,
            "Nombre_Estado": _LABEL_ESTADO[nuevo_estado],
        }

    except Exception:
        if con:
            con.rollback()
        raise
    finally:
        if con:
            con.close()


# ---------------------------------------------------------------------------
# TOGGLE
# ---------------------------------------------------------------------------

def toggle_estado_config() -> dict:
    """
    Alterna el Estado entre 1 (Activo) y 2 (Inactivo).
    Devuelve el nuevo estado como dict igual que actualizar_config().
    """
    config = obtener_config()
    if config is None:
        # Caso extremo: _asegurar_config_ranking() no pudo crear la fila.
        # En vez de exigir un init_db.py manual, la creamos aquí también.
        return actualizar_config(1)

    nuevo = 2 if config["Estado"] == 1 else 1
    return actualizar_config(nuevo)


# ---------------------------------------------------------------------------
# REPORTE — historial de cambios cruzando aseguramiento_datos
# ---------------------------------------------------------------------------

def reporte_historial_config() -> list[dict]:
    """
    Devuelve un listado de las acciones de aseguramiento relacionadas con
    config_ranking (Accion_ID en 1, 2, 3) para tener trazabilidad de quién
    y cuándo modificó la configuración del ranking.

    Columnas devueltas:
        AseguramientoDatos_ID, Usuario_ID, NombreCompleto, Accion_ID,
        Nombre_Accion, Fecha, Descripcion
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                ad.AseguramientoDatos_ID,
                ad.Usuario_ID,
                (u.Nombres || ' ' || u.Apellidos) AS NombreCompleto,
                ad.Accion_ID,
                aa.Nombre_Accion,
                ad.Fecha,
                ad.Descripcion
            FROM aseguramiento_datos ad
            INNER JOIN usuarios             u  ON ad.Usuario_ID = u.Usuario_ID
            INNER JOIN accion_aseguramiento aa ON ad.Accion_ID  = aa.Accion_ID
            WHERE LOWER(ad.Descripcion) LIKE '%config_ranking%'
               OR LOWER(ad.Descripcion) LIKE '%configuración ranking%'
               OR LOWER(ad.Descripcion) LIKE '%configuracion ranking%'
            ORDER BY ad.Fecha DESC, ad.AseguramientoDatos_ID DESC
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        if con:
            con.close()


# ---------------------------------------------------------------------------
# REPORTE — estado actual del ranking con estadísticas
# ---------------------------------------------------------------------------

def reporte_estado_ranking() -> dict:
    """
    Combina la configuración actual con las estadísticas de evaluaciones
    almacenadas en puntuacion_especialista para dar una vista consolidada
    del estado del módulo de ranking.

    Retorna un dict con:
        config            : dict (Config_ID, Estado, Nombre_Estado)
        total_evaluaciones: int
        promedio_general  : float
        top_especialistas : list[dict] (máx. 5, ordenados por promedio DESC)
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # Configuración actual
        cur.execute(
            "SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = ?",
            (_CONFIG_ID,)
        )
        row_cfg = cur.fetchone()
        if row_cfg is None:
            raise RuntimeError("Fila de configuración no encontrada.")

        config = dict(row_cfg)
        config["Nombre_Estado"] = _LABEL_ESTADO.get(config["Estado"], "Desconocido")

        # Totales
        cur.execute("""
            SELECT
                COUNT(*)                                           AS total_evaluaciones,
                ROUND(AVG(CAST(Calificacion_Promedio AS REAL)), 2) AS promedio_general
            FROM puntuacion_especialista
            WHERE Calificacion_Promedio IS NOT NULL
        """)
        row_stats = cur.fetchone()
        total     = int(row_stats["total_evaluaciones"] or 0)
        promedio  = float(row_stats["promedio_general"] or 0.0)

        # Top 5 especialistas
        cur.execute("""
            SELECT
                e.Especialista_ID,
                (u.Nombres || ' ' || u.Apellidos)          AS NombreCompleto,
                COUNT(pe.Puntuacion_ID)                    AS total_evaluaciones,
                ROUND(AVG(pe.Calificacion_Promedio), 2)    AS promedio
            FROM puntuacion_especialista pe
            INNER JOIN especialista e ON pe.Especialista_ID = e.Especialista_ID
            INNER JOIN usuarios     u ON e.Usuario_ID       = u.Usuario_ID
            WHERE pe.Calificacion_Promedio IS NOT NULL
            GROUP BY e.Especialista_ID
            ORDER BY promedio DESC
            LIMIT 5
        """)
        top = [dict(r) for r in cur.fetchall()]

        return {
            "config":             config,
            "total_evaluaciones": total,
            "promedio_general":   promedio,
            "top_especialistas":  top,
        }
    finally:
        if con:
            con.close()