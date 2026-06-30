"""
modulo_historial/routes.py — Stylo Dental
==========================================
Endpoints para Historia Clínica.

SEPARACIÓN ESTRICTA Vista / API
────────────────────────────────
  VISTA  (render_template, NUNCA jsonify):
    GET  /historial/paciente/<paciente_id>
         └─ Recibe cita_id como query param (?cita_id=)
         └─ ÚNICO punto de entrada visual al HTML de Historia Clínica

  API    (jsonify, NUNCA render_template):
    GET  /api/historial/paciente/<paciente_id>/info
    GET  /api/historial/paciente/<paciente_id>/evoluciones
    GET  /api/historial/cita/<cita_id>          ← para la vista del especialista
    GET  /api/historial-clinico/<cita_id>       ← endpoint de respaldo usado por especialista.js
    POST /api/historial/guardar
    POST /api/historial/finalizar

REGISTRO EN app.py (sin url_prefix):
    from modulo_historial.routes import historial_bp
    app.register_blueprint(historial_bp)

CAMBIO 3 — AISLAMIENTO DEL MOTIVO DE CONSULTA:
  El campo MotivoConsulta que llega desde Historia Clínica se guarda
  EXCLUSIVAMENTE en historial_clinico.MotivoHC (columna propia del historial).
  Queda terminantemente prohibido que guardar_historia_clinica() y
  finalizar_desde_historial() escriban sobre cita.Motivo_Consulta, que es
  el campo estático que muestra la interfaz del especialista y debe
  permanecer intacto.

CAMBIO 4 (integración Reporte del Especialista) — FIX DE SINCRONIZACIÓN:
  GET /api/historial/cita/<cita_id> es el puente OFICIAL de sincronización
  Especialista ↔ Historia Clínica. especialista.js (verReporteProfesional)
  consulta este endpoint como fuente PRIMARIA al hacer clic en "Reporte".

CAMBIO 5 — FIX DEL ERROR 500 EN LOS ENDPOINTS DE REPORTE.

CAMBIO 6 — FIX DEFINITIVO DEL 500 EN /api/historial/paciente/<id>/evoluciones.

CAMBIO 7 — UNIFICACIÓN DEFINITIVA DE CLAVES PARA EL REPORTE DEL ESPECIALISTA:
  Todos los endpoints de lectura relacionados con el Reporte ahora incluyen,
  además de las claves Pascal ya existentes (compatibilidad retro), un set
  de claves simples y directas en minúscula: 'diagnostico', 'evolucion' y
  'tratamiento'. Estas tres claves son el contrato OFICIAL y PRIMARIO que
  debe leer especialista.js.

CAMBIO 8 — RASTREO DE DATOS PESADO (DIAGNÓSTICO TEMPORAL):
  Se inyectó un bloque de print() de diagnóstico ANTES de cada
  return _json_ok(...) en los endpoints relacionados con el Reporte
  (/api/historial/cita/<id>, /api/historial-clinico/<id> y
  /api/historial/paciente/<id>/evoluciones), mostrando en la terminal del
  servidor exactamente qué fila/datos se recuperaron de SQL y qué
  diccionario final se está serializando como JSON. Esto permite ver en
  qué punto exacto el dato se vuelve vacío: si ya viene vacío desde SQL
  (problema de datos/consulta) o si se vacía al construir el diccionario
  de respuesta (problema de mapeo en el backend).
"""

import os
import sqlite3
from datetime import datetime, date
from flask import Blueprint, request, jsonify, render_template

historial_bp = Blueprint('historial_bp', __name__)

# ─── Ruta absoluta a odent.db ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'odent.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _json_ok(data, code=200):
    resp = jsonify(data)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp, code


def _json_error(msg, code=400):
    resp = jsonify({"ok": False, "error": msg})
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp, code


def _calcular_edad(fecha_nac_str):
    """Calcula la edad a partir de una cadena de fecha (YYYY-MM-DD)."""
    if not fecha_nac_str:
        return None
    try:
        nac = datetime.strptime(str(fecha_nac_str)[:10], '%Y-%m-%d').date()
        hoy = date.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except (ValueError, TypeError):
        return None


def _get_alergias_condiciones(cur, usuario_id):
    """
    Intenta obtener alergias y condiciones de riesgo del paciente.
    Devuelve (alergias_str, condiciones_str) o ('', '') si las tablas no existen.
    """
    alergias    = ''
    condiciones = ''
    try:
        cur.execute("""
            SELECT GROUP_CONCAT(Nombre_Alergia, ', ') AS Alergias
            FROM alergia_paciente
            WHERE Usuario_ID = ?
        """, (usuario_id,))
        row = cur.fetchone()
        if row and row['Alergias']:
            alergias = row['Alergias']
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT GROUP_CONCAT(Nombre_Condicion, ', ') AS Condiciones
            FROM condicion_medica_paciente
            WHERE Usuario_ID = ?
        """, (usuario_id,))
        row = cur.fetchone()
        if row and row['Condiciones']:
            condiciones = row['Condiciones']
    except Exception:
        pass
    return alergias, condiciones


def _ensure_historial_columns(cur):
    """
    Garantiza que historial_clinico tenga todas las columnas opcionales necesarias.
    Agrega MotivoHC (CAMBIO 3), MapaDental y Hallazgos si no existen.
    """
    try:
        cur.execute("PRAGMA table_info(historial_clinico)")
        hc_cols = [c[1] for c in cur.fetchall()]
        if 'MapaDental' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MapaDental TEXT")
        if 'Hallazgos' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN Hallazgos TEXT")
        # CAMBIO 3: columna exclusiva para el motivo ingresado desde Historia Clínica
        if 'MotivoHC' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MotivoHC TEXT")
        cur.connection.commit()
    except Exception:
        # No debe abortar la lectura por un fallo al intentar migrar el esquema.
        pass


def _ensure_cita_columns(cur):
    """
    CAMBIO 5: garantiza que 'cita' tenga la columna FechaAtencion.
    """
    try:
        cur.execute("PRAGMA table_info(cita)")
        cita_cols = [c[1] for c in cur.fetchall()]
        if 'FechaAtencion' not in cita_cols:
            cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
        cur.connection.commit()
    except Exception:
        pass


def _descomprimir_evolucion_tratamiento(desc):
    """
    Separa el campo Tratamiento codificado como "evolucion\n---\ntratamiento".
    Devuelve (evolucion, tratamiento), siempre como strings (nunca None).
    """
    desc = desc or ''
    if '---' in desc:
        partes = desc.split('---', 1)
        return partes[0].strip(), partes[1].strip()
    return desc, ''


def _aplicar_claves_unificadas_reporte(data, diagnostico, evolucion, tratamiento):
    """
    CAMBIO 7: aplica sobre el diccionario `data` el set COMPLETO de claves
    que el Reporte del Especialista puede necesitar, en ambas convenciones
    (Pascal legado + minúscula simple, que es ahora el contrato oficial
    leído por especialista.js).
    """
    diagnostico = diagnostico or ''
    evolucion   = evolucion or ''
    tratamiento = tratamiento or ''

    # Claves Pascal (compatibilidad retro con versiones anteriores del JS)
    data['Diagnostico']        = diagnostico
    data['Evolucion']          = evolucion
    data['Tratamiento']        = tratamiento
    data['evolucion_clinica']  = evolucion

    # CAMBIO 7 — Claves OFICIALES simples en minúscula (contrato primario)
    data['diagnostico'] = diagnostico
    data['evolucion']   = evolucion
    data['tratamiento'] = tratamiento

    return data


def _respuesta_vacia_cita(cita_id):
    """
    CAMBIO 6: estructura por defecto cuando una cita no tiene historial
    clínico todavía (paciente nuevo) o cuando ocurre cualquier error no
    crítico al construir la respuesta. Nunca produce un 500.

    CAMBIO 7: se añadieron también las claves simples oficiales
    'diagnostico', 'evolucion' y 'tratamiento'.
    """
    data = {
        "Cita_ID": cita_id,
        "Motivo_Consulta": "",
        "Fecha": "",
        "Hora_Inicio": "",
        "EstadoAgenda": "",
        "NombreEspecialista": "",
        "Nombre_Especialidad": "",
        "NombrePaciente": "",
        "TipoDocumento": "",
        "NumeroDocumento": "",
        "Historial_ID": None,
        "MapaDental": "",
        "Hallazgos": "",
        "MotivoHC": "",
        "FechaAtencion": "",
        "FechaRegistro": "",
    }
    return _aplicar_claves_unificadas_reporte(data, '', '', '')


# ══════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL
# GET /historial/paciente/<paciente_id>?cita_id=<cita_id>
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def vista_historia_clinica(paciente_id):
    """
    Ruta de VISTA — renderiza historia_clinica.html.
    El frontend SIEMPRE debe navegar aquí (window.location.href).
    """
    cita_id = request.args.get('cita_id', type=int)
    return render_template(
        'historia_clinica.html',
        paciente_id=paciente_id,
        cita_id=cita_id if cita_id else ''
    )


# ══════════════════════════════════════════════════════════════════════════════
# API — INFORMACIÓN CLÍNICA DEL PACIENTE
# GET /api/historial/paciente/<paciente_id>/info
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/info', methods=['GET'])
def get_info_paciente(paciente_id):
    """Ruta de API — devuelve datos clínicos del paciente como JSON."""
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        cur.execute("""
            SELECT
                u.Usuario_ID,
                u.Nombres || ' ' || u.Apellidos   AS NombreCompleto,
                td.Nombre_Tipo_Documento           AS TipoDocumento,
                u.NumeroDocumento,
                u.FechaNacimiento,
                u.Correo,
                u.Telefono,
                eps.Nombre_EPS                     AS NombreEPS,
                re.Descripcion                     AS Regimen,
                tae.Nombre_Tipo                    AS TipoAfiliacion,
                p.Paciente_ID
            FROM paciente p
            JOIN usuarios u              ON u.Usuario_ID      = p.Usuario_ID
            LEFT JOIN tipo_documento td  ON td.TipoDoc_ID     = u.TipoDoc_ID
            LEFT JOIN afiliacion a       ON a.Usuario_ID      = u.Usuario_ID
            LEFT JOIN eps                ON eps.EPS_ID        = a.EPS_ID
            LEFT JOIN regimen_eps re     ON re.Regimen_ID     = eps.Regimen_ID
            LEFT JOIN tipo_afiliacion_eps tae ON tae.TipoEPS_ID = a.TipoEPS_ID
            WHERE p.Paciente_ID = ?
            LIMIT 1
        """, (paciente_id,))
        row = cur.fetchone()

        if not row:
            return _json_error('Paciente no encontrado.', 404)

        info = dict(row)
        info['Edad'] = _calcular_edad(info.get('FechaNacimiento'))

        if not info.get('TipoAfiliacion'):
            try:
                cur.execute("""
                    SELECT te.Nombre_Tipo AS TipoAfiliacion
                    FROM afiliacion a
                    LEFT JOIN tipo_eps te ON te.TipoEPS_ID = a.TipoEPS_ID
                    WHERE a.Usuario_ID = ?
                    LIMIT 1
                """, (info['Usuario_ID'],))
                leg = cur.fetchone()
                if leg:
                    info['TipoAfiliacion'] = leg['TipoAfiliacion']
            except Exception:
                pass

        alergias, condiciones = _get_alergias_condiciones(cur, info['Usuario_ID'])
        info['Alergias']    = alergias
        info['Condiciones'] = condiciones

        return _json_ok({"ok": True, "data": info})

    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — EVOLUCIONES / HISTORIAL
# GET /api/historial/paciente/<paciente_id>/evoluciones?cita_id=<cita_id>
#
# CAMBIO 8: print() de diagnóstico ANTES del return _json_ok exitoso, para
# ver en la terminal exactamente qué filas crudas vinieron de SQL y qué
# lista `filas` (ya mapeada con claves unificadas) se está serializando.
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/evoluciones', methods=['GET'])
def get_evoluciones_paciente(paciente_id):
    """Ruta de API — devuelve el historial de evoluciones como JSON."""
    cita_id = request.args.get('cita_id', type=int)
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        # CAMBIO 5: garantizar esquema ANTES de leer columnas dinámicas.
        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)

        sql = """
            SELECT
                c.Cita_ID,
                COALESCE(hc.MotivoHC, '') AS Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                ea.Nombre_Estado                          AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos         AS NombreEspecialista,
                esp.Nombre_Especialidad,
                hc.Historial_ID,
                hc.MapaDental,
                hc.Hallazgos,
                (
                    SELECT d.Nombre_Diagnostico
                    FROM historial_diagnostico hd
                    JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                    WHERE hd.Historial_ID = hc.Historial_ID
                    ORDER BY hd.rowid DESC
                    LIMIT 1
                ) AS Diagnostico,
                (
                    SELECT t.Descripcion
                    FROM tratamiento t
                    WHERE t.Historial_ID = hc.Historial_ID
                    ORDER BY t.Tratamiento_ID DESC
                    LIMIT 1
                ) AS Tratamiento,
                (
                    SELECT t.FechaRegistro
                    FROM tratamiento t
                    WHERE t.Historial_ID = hc.Historial_ID
                    ORDER BY t.Tratamiento_ID DESC
                    LIMIT 1
                ) AS FechaRegistro
            FROM cita c
            JOIN agenda a        ON a.Agenda_ID        = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue     ON ue.Usuario_ID       = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN historial_clinico hc ON hc.Cita_ID = c.Cita_ID
            WHERE c.Paciente_ID = ?
        """
        params = [paciente_id]
        if cita_id:
            sql += " AND c.Cita_ID = ?"
            params.append(cita_id)

        sql += " ORDER BY a.Fecha DESC, a.Hora_Inicio DESC"

        try:
            cur.execute(sql, params)
            filas_raw = cur.fetchall()
        except sqlite3.OperationalError:
            # Si por algún motivo persiste un esquema desincronizado, no
            # se revienta el endpoint: se responde con lista vacía.
            filas_raw = []

        # CAMBIO 8 — RASTREO DE DATOS PESADO: filas crudas de SQL
        print("========= BACKEND DIAGNOSTICO =========")
        print("[evoluciones] Paciente_ID:", paciente_id, "| cita_id filtro:", cita_id)
        print("Datos recuperados de SQL:", [dict(r) for r in filas_raw])
        print("=======================================")

        filas = []
        for r in filas_raw:
            f = dict(r)
            desc = f.get('Tratamiento') or ''
            evolucion, tratamiento = _descomprimir_evolucion_tratamiento(desc)
            diagnostico = f.get('Diagnostico') or ''

            f = _aplicar_claves_unificadas_reporte(f, diagnostico, evolucion, tratamiento)
            f['Motivo_Consulta']  = f.get('Motivo_Consulta') or ''
            f['MapaDental']       = f.get('MapaDental') or ''
            f['Hallazgos']        = f.get('Hallazgos') or ''
            f['FechaRegistro']    = f.get('FechaRegistro') or ''
            filas.append(f)

        # CAMBIO 8 — RASTREO DE DATOS PESADO: payload final a serializar
        print("========= BACKEND DIAGNOSTICO =========")
        print("Datos recuperados de SQL:", filas)
        print("=======================================")

        # CAMBIO 6 — FIX DEL 500: este return faltaba por completo.
        return _json_ok({"ok": True, "data": filas})

    except Exception:
        # Garantiza que la ausencia/fallo de historial nunca rompa el flujo
        # del Reporte: se responde 200 con lista vacía en vez de 500.
        return _json_ok({"ok": True, "data": []})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — DATOS CLÍNICOS DE UNA CITA ESPECÍFICA (para vista del Especialista)
# GET /api/historial/cita/<cita_id>
#
# CAMBIO 8: print() de diagnóstico ANTES del return _json_ok, tanto de la
# fila cruda devuelta por SQL (row) como del diccionario `data` final que
# se está serializando como JSON. Este es el endpoint PRIMARIO que usa
# verReporteProfesional, así que es el punto más importante a rastrear.
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/cita/<int:cita_id>', methods=['GET'])
def get_historial_por_cita(cita_id):
    """
    Ruta de API — devuelve todos los datos clínicos de una cita para el reporte
    del especialista. Refleja en tiempo real los cambios guardados desde HC.
    """
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        # CAMBIO 5: garantizar esquema ANTES de leer columnas dinámicas.
        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    c.Motivo_Consulta,
                    c.FechaAtencion,
                    a.Fecha,
                    a.Hora_Inicio,
                    ea.Nombre_Estado                          AS EstadoAgenda,
                    ue.Nombres || ' ' || ue.Apellidos         AS NombreEspecialista,
                    esp.Nombre_Especialidad,
                    up.Nombres || ' ' || up.Apellidos         AS NombrePaciente,
                    td.Nombre_Tipo_Documento                  AS TipoDocumento,
                    up.NumeroDocumento,
                    hc.Historial_ID,
                    hc.MapaDental,
                    hc.Hallazgos,
                    hc.MotivoHC,
                    (
                        SELECT d.Nombre_Diagnostico
                        FROM historial_diagnostico hd
                        JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                        WHERE hd.Historial_ID = hc.Historial_ID
                        ORDER BY hd.rowid DESC
                        LIMIT 1
                    ) AS Diagnostico,
                    (
                        SELECT t.Descripcion
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS Tratamiento,
                    (
                        SELECT t.FechaRegistro
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS FechaRegistro
                FROM cita c
                JOIN agenda a         ON a.Agenda_ID         = c.Agenda_ID
                JOIN estado_agenda ea ON ea.EstadoAgenda_ID  = a.EstadoAgenda_ID
                JOIN especialista e   ON e.Especialista_ID   = a.Especialista_ID
                JOIN usuarios ue      ON ue.Usuario_ID        = e.Usuario_ID
                LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
                LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
                JOIN paciente p       ON p.Paciente_ID        = c.Paciente_ID
                JOIN usuarios up      ON up.Usuario_ID        = p.Usuario_ID
                LEFT JOIN tipo_documento td ON td.TipoDoc_ID = up.TipoDoc_ID
                LEFT JOIN historial_clinico hc ON hc.Cita_ID = c.Cita_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError as exc_sql:
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial/cita] Cita_ID:", cita_id, "| OperationalError:", exc_sql)
            print("Datos recuperados de SQL:", None)
            print("=======================================")
            # CAMBIO 6: error de esquema -> respuesta vacía 200, no 500.
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        # CAMBIO 8 — RASTREO DE DATOS PESADO: fila cruda devuelta por SQL
        print("========= BACKEND DIAGNOSTICO =========")
        print("[/api/historial/cita] Cita_ID:", cita_id)
        print("Datos recuperados de SQL:", dict(row) if row else None)
        print("=======================================")

        if not row:
            # CAMBIO 6: cita sin historial (paciente nuevo) -> 200 con vacíos.
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        try:
            data = dict(row)

            # Descomprimir Tratamiento + Evolución (acceso seguro vía .get)
            desc = data.get('Tratamiento') or ''
            evolucion, tratamiento = _descomprimir_evolucion_tratamiento(desc)
            diagnostico = data.get('Diagnostico') or ''

            data = _aplicar_claves_unificadas_reporte(data, diagnostico, evolucion, tratamiento)
            data['MotivoHC']            = data.get('MotivoHC') or ''
            data['MapaDental']          = data.get('MapaDental') or ''
            data['Hallazgos']           = data.get('Hallazgos') or ''
            data['FechaAtencion']       = data.get('FechaAtencion') or ''
            data['FechaRegistro']       = data.get('FechaRegistro') or ''

            # CAMBIO 8 — RASTREO DE DATOS PESADO: payload final a serializar
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial/cita] Cita_ID:", cita_id, "| Payload final JSON ->")
            print("Datos recuperados de SQL:", data)
            print("=======================================")

            return _json_ok({"ok": True, "data": data})
        except Exception as exc_build:
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial/cita] Cita_ID:", cita_id, "| EXCEPCION construyendo data:", exc_build)
            print("Datos recuperados de SQL:", dict(row) if row else None)
            print("=======================================")
            # CAMBIO 6: cualquier fallo al armar la respuesta -> vacíos 200.
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

    except Exception as exc_general:
        print("========= BACKEND DIAGNOSTICO =========")
        print("[/api/historial/cita] Cita_ID:", cita_id, "| EXCEPCION GENERAL:", exc_general)
        print("Datos recuperados de SQL:", None)
        print("=======================================")
        # CAMBIO 6: este endpoint ya nunca devuelve 500.
        return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — RESPALDO DE COMPATIBILIDAD PARA EL MODAL "REPORTE" DEL ESPECIALISTA
# GET /api/historial-clinico/<cita_id>
#
# CAMBIO 8: print() de diagnóstico ANTES del return _json_ok, igual que en
# /api/historial/cita/<id>.
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial-clinico/<int:cita_id>', methods=['GET'])
def get_historial_clinico_legacy(cita_id):
    """Ruta de API (respaldo) — alias funcional de /api/historial/cita/<cita_id>."""
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    c.Motivo_Consulta,
                    c.FechaAtencion,
                    hc.Historial_ID,
                    hc.MapaDental,
                    hc.Hallazgos,
                    hc.MotivoHC,
                    (
                        SELECT d.Nombre_Diagnostico
                        FROM historial_diagnostico hd
                        JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                        WHERE hd.Historial_ID = hc.Historial_ID
                        ORDER BY hd.rowid DESC
                        LIMIT 1
                    ) AS Diagnostico,
                    (
                        SELECT t.Descripcion
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS Tratamiento,
                    (
                        SELECT t.FechaRegistro
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS FechaRegistro
                FROM cita c
                LEFT JOIN historial_clinico hc ON hc.Cita_ID = c.Cita_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError as exc_sql:
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial-clinico] Cita_ID:", cita_id, "| OperationalError:", exc_sql)
            print("Datos recuperados de SQL:", None)
            print("=======================================")
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        # CAMBIO 8 — RASTREO DE DATOS PESADO: fila cruda devuelta por SQL
        print("========= BACKEND DIAGNOSTICO =========")
        print("[/api/historial-clinico] Cita_ID:", cita_id)
        print("Datos recuperados de SQL:", dict(row) if row else None)
        print("=======================================")

        if not row:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        try:
            data = dict(row)
            desc = data.get('Tratamiento') or ''
            evolucion, tratamiento = _descomprimir_evolucion_tratamiento(desc)
            diagnostico = data.get('Diagnostico') or ''

            data = _aplicar_claves_unificadas_reporte(data, diagnostico, evolucion, tratamiento)
            data['MotivoHC']           = data.get('MotivoHC') or ''
            data['MapaDental']         = data.get('MapaDental') or ''
            data['Hallazgos']          = data.get('Hallazgos') or ''
            data['FechaAtencion']      = data.get('FechaAtencion') or ''
            data['FechaRegistro']      = data.get('FechaRegistro') or ''

            # CAMBIO 8 — RASTREO DE DATOS PESADO: payload final a serializar
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial-clinico] Cita_ID:", cita_id, "| Payload final JSON ->")
            print("Datos recuperados de SQL:", data)
            print("=======================================")

            return _json_ok({"ok": True, "data": data})
        except Exception as exc_build:
            print("========= BACKEND DIAGNOSTICO =========")
            print("[/api/historial-clinico] Cita_ID:", cita_id, "| EXCEPCION construyendo data:", exc_build)
            print("Datos recuperados de SQL:", dict(row) if row else None)
            print("=======================================")
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

    except Exception as exc_general:
        print("========= BACKEND DIAGNOSTICO =========")
        print("[/api/historial-clinico] Cita_ID:", cita_id, "| EXCEPCION GENERAL:", exc_general)
        print("Datos recuperados de SQL:", None)
        print("=======================================")
        return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — GUARDAR HISTORIA CLÍNICA
# POST /api/historial/guardar
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/guardar', methods=['POST'])
def guardar_historia_clinica():
    """Ruta de API — persiste motivo, diagnóstico, evolución y tratamiento."""
    datos       = request.get_json(silent=True) or {}
    cita_id     = datos.get('Cita_ID')
    diagnostico = (datos.get('Diagnostico')   or '').strip()
    evolucion   = (datos.get('Evolucion')     or '').strip()
    tratamiento = (datos.get('Tratamiento')   or '').strip()
    mapa_dental = datos.get('MapaDental')     or '{}'
    hallazgos   = datos.get('Hallazgos')      or '[]'
    motivo_hc   = (datos.get('MotivoConsulta') or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        if not cur.fetchone():
            cur.execute("ROLLBACK")
            return _json_error('Cita no encontrada.', 404)

        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?",
            (cita_id,)
        )
        hc_row = cur.fetchone()
        historial_id = hc_row['Historial_ID'] if hc_row else None
        if not historial_id:
            cur.execute(
                "INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,)
            )
            historial_id = cur.lastrowid

        _ensure_historial_columns(cur)

        if motivo_hc:
            cur.execute(
                "UPDATE historial_clinico SET MotivoHC = ? WHERE Historial_ID = ?",
                (motivo_hc, historial_id)
            )

        if diagnostico:
            cur.execute(
                "SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?",
                (diagnostico,)
            )
            dr = cur.fetchone()
            diag_id = dr['Diagnostico_ID'] if dr else None
            if not diag_id:
                cur.execute(
                    "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)",
                    (diagnostico,)
                )
                diag_id = cur.lastrowid
            cur.execute(
                "DELETE FROM historial_diagnostico WHERE Historial_ID = ?",
                (historial_id,)
            )
            cur.execute(
                "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diag_id)
            )

        desc = ''
        if evolucion and tratamiento:
            desc = f"{evolucion}\n---\n{tratamiento}"
        elif evolucion:
            desc = evolucion
        elif tratamiento:
            desc = tratamiento

        if desc:
            cur.execute(
                "DELETE FROM tratamiento WHERE Historial_ID = ?", (historial_id,)
            )
            cur.execute("PRAGMA table_info(tratamiento)")
            cols = [c[1] for c in cur.fetchall()]
            fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'FechaRegistro' in cols:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion, FechaRegistro) VALUES (?, ?, ?)",
                    (historial_id, desc, fecha_ahora)
                )
            else:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion) VALUES (?, ?)",
                    (historial_id, desc)
                )

        cur.execute(
            "UPDATE historial_clinico SET MapaDental = ?, Hallazgos = ? WHERE Historial_ID = ?",
            (str(mapa_dental), str(hallazgos), historial_id)
        )

        cur.execute("COMMIT")
        return _json_ok({
            "ok": True,
            "Historial_ID": historial_id,
            "mensaje": "Historia clínica guardada correctamente.",
            "FechaGuardado": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, 201)

    except Exception as exc:
        if con:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — FINALIZAR CONSULTA DESDE HISTORIA CLÍNICA
# POST /api/historial/finalizar
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/finalizar', methods=['POST'])
def finalizar_desde_historial():
    """
    Ruta de API — guarda la HC completa y marca la agenda como Cumplida.
    Los datos quedan inmediatamente disponibles para la vista del especialista
    a través de GET /api/historial/cita/<cita_id> y
    GET /api/historial/paciente/<paciente_id>/evoluciones.
    """
    datos       = request.get_json(silent=True) or {}
    cita_id     = datos.get('Cita_ID')
    diagnostico = (datos.get('Diagnostico')    or '').strip()
    evolucion   = (datos.get('Evolucion')      or '').strip()
    tratamiento = (datos.get('Tratamiento')    or '').strip()
    mapa_dental = datos.get('MapaDental')      or '{}'
    hallazgos   = datos.get('Hallazgos')       or '[]'
    motivo_hc   = (datos.get('MotivoConsulta') or '').strip()

    print(f"[FINALIZAR] payload recibido -> Cita_ID={cita_id!r} "
          f"Diagnostico={diagnostico!r} Evolucion={evolucion!r} "
          f"Tratamiento={tratamiento!r} MotivoHC={motivo_hc!r}")

    if not cita_id:
        print("[FINALIZAR] ABORTADO: Cita_ID vacío/None — revisa _HC_CITA_ID en historia_clinica.js")
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        cur.execute(
            "SELECT c.Cita_ID, a.Agenda_ID FROM cita c "
            "JOIN agenda a ON a.Agenda_ID = c.Agenda_ID WHERE c.Cita_ID = ?",
            (cita_id,)
        )
        cita_row = cur.fetchone()
        if not cita_row:
            cur.execute("ROLLBACK")
            print(f"[FINALIZAR] ABORTADO: no existe cita ni agenda para Cita_ID={cita_id!r}")
            return _json_error('Cita no encontrada.', 404)

        # Marcar agenda como Cumplida (EstadoAgenda_ID = 4)
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 4 WHERE Agenda_ID = ?",
            (cita_row['Agenda_ID'],)
        )

        # Registrar fecha de atención
        fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("PRAGMA table_info(cita)")
        cita_cols = [c[1] for c in cur.fetchall()]
        if 'FechaAtencion' not in cita_cols:
            cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
        cur.execute(
            "UPDATE cita SET FechaAtencion = ? WHERE Cita_ID = ?",
            (fecha_ahora, cita_id)
        )

        # Upsert historial_clinico
        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
        )
        hc_row       = cur.fetchone()
        historial_id = hc_row['Historial_ID'] if hc_row else None
        if not historial_id:
            cur.execute(
                "INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,)
            )
            historial_id = cur.lastrowid

        _ensure_historial_columns(cur)

        # CAMBIO 3: guardar motivo exclusivamente en historial_clinico.MotivoHC
        if motivo_hc:
            cur.execute(
                "UPDATE historial_clinico SET MotivoHC = ? WHERE Historial_ID = ?",
                (motivo_hc, historial_id)
            )

        # Diagnóstico
        if diagnostico:
            cur.execute(
                "SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?",
                (diagnostico,)
            )
            dr      = cur.fetchone()
            diag_id = dr['Diagnostico_ID'] if dr else None
            if not diag_id:
                cur.execute(
                    "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)",
                    (diagnostico,)
                )
                diag_id = cur.lastrowid
            cur.execute(
                "DELETE FROM historial_diagnostico WHERE Historial_ID = ?",
                (historial_id,)
            )
            cur.execute(
                "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diag_id)
            )

        # Tratamiento + Evolución
        desc = ''
        if evolucion and tratamiento:
            desc = f"{evolucion}\n---\n{tratamiento}"
        elif evolucion:
            desc = evolucion
        elif tratamiento:
            desc = tratamiento

        if desc:
            cur.execute(
                "DELETE FROM tratamiento WHERE Historial_ID = ?", (historial_id,)
            )
            cur.execute("PRAGMA table_info(tratamiento)")
            t_cols = [c[1] for c in cur.fetchall()]
            if 'FechaRegistro' in t_cols:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion, FechaRegistro) VALUES (?, ?, ?)",
                    (historial_id, desc, fecha_ahora)
                )
            else:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion) VALUES (?, ?)",
                    (historial_id, desc)
                )

        # MapaDental / Hallazgos
        cur.execute(
            "UPDATE historial_clinico SET MapaDental = ?, Hallazgos = ? WHERE Historial_ID = ?",
            (str(mapa_dental), str(hallazgos), historial_id)
        )

        cur.execute("COMMIT")
        print(f"[FINALIZAR] OK -> Cita_ID={cita_id} Historial_ID={historial_id} "
              f"guardado correctamente en historial_clinico/tratamiento/historial_diagnostico.")
        return _json_ok({
            "ok": True,
            "Historial_ID":  historial_id,
            "FechaAtencion": fecha_ahora,
            "mensaje":       "Consulta finalizada y registrada correctamente."
        })

    except Exception as exc:
        if con:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()