# =============================================================================
# modulo_config_ranking/config_ranking.py
# =============================================================================

from db import get_db_connection

_CONFIG_ID       = 1
_ESTADOS_VALIDOS = {1, 2}
_LABEL_ESTADO    = {1: "Activo", 2: "Inactivo"}


# ---------------------------------------------------------------------------
# LECTURA
# ---------------------------------------------------------------------------

def obtener_config() -> dict | None:
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

    BUG CORREGIDO:
    La versión anterior hacía con.commit() ANTES de verificar cur.rowcount.
    Si rowcount era 0, lanzaba RuntimeError dentro del bloque try, lo que
    ejecutaba con.rollback() en el except — pero el commit ya había ocurrido,
    así que el rollback no tenía efecto y la excepción llegaba a routes.py
    como un 409, haciendo que el frontend revirtiera el toggle visualmente
    aunque el UPDATE hubiera funcionado correctamente (o no hubiera ocurrido
    en absoluto). El usuario veía "no se guardó" aunque a veces sí se guardó.

    Orden correcto:
      1. ejecutar UPDATE
      2. verificar rowcount ANTES del commit
      3. si rowcount == 0 → raise sin commit (la transacción se descarta)
      4. si rowcount > 0  → commit()
      5. releer para confirmar
    """
    if nuevo_estado not in _ESTADOS_VALIDOS:
        raise ValueError(
            "Estado inválido: '{}'. Use 1 (Activo) o 2 (Inactivo).".format(nuevo_estado)
        )

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute(
            "UPDATE config_ranking SET Estado = ? WHERE Config_ID = ?",
            (nuevo_estado, _CONFIG_ID)
        )

        # VERIFICAR ROWCOUNT ANTES DEL COMMIT
        if cur.rowcount == 0:
            # La fila Config_ID=1 no existe en este momento.
            # Intentar crearla y luego actualizar.
            cur.execute(
                "INSERT OR REPLACE INTO config_ranking (Config_ID, Estado) VALUES (?, ?)",
                (_CONFIG_ID, nuevo_estado)
            )
            if cur.rowcount == 0:
                raise RuntimeError(
                    "No se pudo crear ni actualizar la fila Config_ID=1 en config_ranking."
                )

        # COMMIT solo cuando hay algo que confirmar
        con.commit()

        # Relectura de confirmación
        cur.execute(
            "SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = ?",
            (_CONFIG_ID,)
        )
        confirmado = cur.fetchone()
        if confirmado is None or int(confirmado["Estado"]) != nuevo_estado:
            raise RuntimeError(
                "Inconsistencia tras commit: se escribió Estado={} pero la BD devuelve Estado={}.".format(
                    nuevo_estado,
                    confirmado["Estado"] if confirmado else "NULL"
                )
            )

        return {
            "Config_ID":     _CONFIG_ID,
            "Estado":        nuevo_estado,
            "Nombre_Estado": _LABEL_ESTADO[nuevo_estado],
        }

    except Exception:
        if con:
            try:
                con.rollback()
            except Exception:
                pass
        raise
    finally:
        if con:
            con.close()


# ---------------------------------------------------------------------------
# TOGGLE
# ---------------------------------------------------------------------------

def toggle_estado_config() -> dict:
    config = obtener_config()
    if config is None:
        return actualizar_config(1)
    nuevo = 2 if config["Estado"] == 1 else 1
    return actualizar_config(nuevo)


# ---------------------------------------------------------------------------
# REPORTE — historial de cambios cruzando aseguramiento_datos
# ---------------------------------------------------------------------------

def reporte_historial_config() -> list[dict]:
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
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT Config_ID, Estado FROM config_ranking WHERE Config_ID = ?",
            (_CONFIG_ID,)
        )
        row_cfg = cur.fetchone()
        if row_cfg is None:
            raise RuntimeError("Fila de configuración no encontrada.")

        config = dict(row_cfg)
        config["Nombre_Estado"] = _LABEL_ESTADO.get(config["Estado"], "Desconocido")

        cur.execute("""
            SELECT
                COUNT(*)                                           AS total_evaluaciones,
                ROUND(AVG(CAST(Calificacion_Promedio AS REAL)), 2) AS promedio_general
            FROM puntuacion_especialista
            WHERE Calificacion_Promedio IS NOT NULL
        """)
        row_stats = cur.fetchone()
        total    = int(row_stats["total_evaluaciones"] or 0)
        promedio = float(row_stats["promedio_general"] or 0.0)

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