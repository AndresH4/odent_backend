"""
modulo_historial/routes.py — Stylo Dental
==========================================
"""

import os
import sqlite3
from datetime import datetime, date
from flask import Blueprint, request, jsonify, render_template

historial_bp = Blueprint('historial_bp', __name__)

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
    if not fecha_nac_str:
        return None
    try:
        nac = datetime.strptime(str(fecha_nac_str)[:10], '%Y-%m-%d').date()
        hoy = date.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except (ValueError, TypeError):
        return None


def _get_alergias_condiciones(cur, usuario_id):
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
    Añade columnas opcionales a historial_clinico si no existen.
    Opera sin transacción activa — llámalo antes de BEGIN o después de COMMIT.
    """
    try:
        cur.execute("PRAGMA table_info(historial_clinico)")
        hc_cols = [c[1] for c in cur.fetchall()]
        if 'MapaDental' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MapaDental TEXT")
        if 'Hallazgos' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN Hallazgos TEXT")
        if 'MotivoHC' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MotivoHC TEXT")
        cur.connection.commit()
    except Exception:
        pass


def _ensure_cita_columns(cur):
    """
    Añade FechaAtencion a cita si no existe.
    Opera sin transacción activa — llámalo antes de BEGIN o después de COMMIT.
    """
    try:
        cur.execute("PRAGMA table_info(cita)")
        cita_cols = [c[1] for c in cur.fetchall()]
        if 'FechaAtencion' not in cita_cols:
            cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
        cur.connection.commit()
    except Exception:
        pass


def _ensure_tratamiento_columns(cur):
    """
    Añade FechaRegistro a tratamiento si no existe.
    Opera sin transacción activa.
    """
    try:
        cur.execute("PRAGMA table_info(tratamiento)")
        t_cols = [c[1] for c in cur.fetchall()]
        if 'FechaRegistro' not in t_cols:
            cur.execute("ALTER TABLE tratamiento ADD COLUMN FechaRegistro TEXT")
        cur.connection.commit()
    except Exception:
        pass


def _tiene_columna(cur, tabla, columna):
    cur.execute(f"PRAGMA table_info({tabla})")
    return any(c[1] == columna for c in cur.fetchall())


def _descomprimir_evolucion_tratamiento(desc):
    desc = desc or ''
    desc = desc.strip()
    if not desc:
        return '', ''
    if '---' in desc:
        partes = desc.split('---', 1)
        return partes[0].strip(), partes[1].strip()
    return desc, desc


def _aplicar_claves_unificadas_reporte(data, diagnostico, evolucion, tratamiento):
    diagnostico = diagnostico if diagnostico is not None else ''
    evolucion   = evolucion   if evolucion   is not None else ''
    tratamiento = tratamiento if tratamiento is not None else ''

    data['Diagnostico']       = diagnostico
    data['Evolucion']         = evolucion
    data['Tratamiento']       = tratamiento
    data['diagnostico']       = diagnostico
    data['evolucion']         = evolucion
    data['tratamiento']       = tratamiento
    data['evolucion_clinica'] = evolucion
    data['diagnostico_texto'] = diagnostico
    data['evolucion_texto']   = evolucion
    data['tratamiento_texto'] = tratamiento

    return data


def _normalizar_datos_paciente(data):
    data['NombrePaciente']      = data.get('NombrePaciente')      or ''
    data['TipoDocumento']       = data.get('TipoDocumento')       or ''
    data['NumeroDocumento']     = data.get('NumeroDocumento')     or ''
    data['Motivo_Consulta']     = data.get('Motivo_Consulta')     or data.get('MotivoHC') or ''
    data['Fecha']               = data.get('Fecha')               or ''
    data['Hora_Inicio']         = data.get('Hora_Inicio')         or ''
    data['EstadoAgenda']        = data.get('EstadoAgenda')        or ''
    data['NombreEspecialista']  = data.get('NombreEspecialista')  or ''
    data['Nombre_Especialidad'] = data.get('Nombre_Especialidad') or ''
    return data


def _respuesta_vacia_cita(cita_id):
    data = {
        "Cita_ID":             cita_id,
        "Motivo_Consulta":     "",
        "Fecha":               "",
        "Hora_Inicio":         "",
        "EstadoAgenda":        "",
        "NombreEspecialista":  "",
        "Nombre_Especialidad": "",
        "NombrePaciente":      "",
        "TipoDocumento":       "",
        "NumeroDocumento":     "",
        "Historial_ID":        None,
        "MapaDental":          "",
        "Hallazgos":           "",
        "MotivoHC":            "",
        "FechaAtencion":       "",
        "FechaRegistro":       "",
    }
    data = _normalizar_datos_paciente(data)
    return _aplicar_claves_unificadas_reporte(data, '', '', '')


def _validar_propiedad_cita(cur, cita_id, paciente_id_qs=None, usuario_id_qs=None):
    """
    Verifica que la cita pertenezca al paciente/usuario que la está
    consultando. Devuelve (permitido: bool, error_response|None).
    Si no se envía ningún identificador por querystring, no bloquea
    (retro-compatibilidad con integraciones internas/administrativas).
    """
    if not paciente_id_qs and not usuario_id_qs:
        return True, None
    try:
        cur.execute("""
            SELECT c.Paciente_ID, p.Usuario_ID
            FROM cita c
            LEFT JOIN paciente p ON p.Paciente_ID = c.Paciente_ID
            WHERE c.Cita_ID = ?
            LIMIT 1
        """, (cita_id,))
        prop = cur.fetchone()
    except sqlite3.OperationalError:
        return True, None

    if not prop:
        return False, _json_error('Cita no encontrada.', 404)
    if paciente_id_qs and prop['Paciente_ID'] != paciente_id_qs:
        return False, _json_error('No tiene permiso para consultar este reporte.', 403)
    if usuario_id_qs and prop['Usuario_ID'] != usuario_id_qs:
        return False, _json_error('No tiene permiso para consultar este reporte.', 403)
    return True, None


# ══════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def vista_historia_clinica(paciente_id):
    cita_id = request.args.get('cita_id', type=int)
    return render_template(
        'historia_clinica.html',
        paciente_id=paciente_id,
        cita_id=cita_id if cita_id else ''
    )


# ══════════════════════════════════════════════════════════════════════════════
# API — CATÁLOGO DE DIAGNÓSTICOS
# Devuelve los 26 diagnósticos CIE-10 con id, codigo y nombre.
# El frontend usa esta respuesta como única fuente de verdad para el
# buscador predictivo; el catálogo estático del JS es solo respaldo offline.
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/diagnosticos', methods=['GET'])
def get_diagnosticos():
    """
    GET /api/diagnosticos?q=<texto_opcional>

    Parámetros opcionales:
      q   — filtra por código o nombre (LIKE %q%)

    Respuesta:
      { "ok": true, "data": [ {"id":1,"codigo":"Z012","nombre":"EXAMEN ODONTOLOGICO"}, ... ] }
    """
    q   = (request.args.get('q', '') or '').strip()
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        if q:
            # Normalizar la query: eliminar punto para comparar contra códigos sin punto
            q_sin_punto = q.replace('.', '')
            patron      = f'%{q}%'
            patron_sp   = f'%{q_sin_punto}%'
            cur.execute("""
                SELECT Diagnostico_ID, Codigo, Nombre_Diagnostico
                FROM diagnostico
                WHERE
                    Nombre_Diagnostico LIKE ?
                    OR Codigo          LIKE ?
                    OR REPLACE(Codigo, '.', '') LIKE ?
                ORDER BY Codigo
                LIMIT 30
            """, (patron, patron, patron_sp))
        else:
            cur.execute("""
                SELECT Diagnostico_ID, Codigo, Nombre_Diagnostico
                FROM diagnostico
                ORDER BY Codigo
                LIMIT 100
            """)

        rows = cur.fetchall()
        return _json_ok({
            "ok":   True,
            "data": [
                {
                    "id":     r["Diagnostico_ID"],
                    "codigo": r["Codigo"]           or '',
                    "nombre": r["Nombre_Diagnostico"],
                }
                for r in rows
            ]
        })
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — INFORMACIÓN CLÍNICA DEL PACIENTE
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/info', methods=['GET'])
def get_info_paciente(paciente_id):
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
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/evoluciones', methods=['GET'])
def get_evoluciones_paciente(paciente_id):
    cita_id = request.args.get('cita_id', type=int)
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        # Migraciones DDL fuera de toda transacción DML
        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        sql = """
            SELECT
                c.Cita_ID,
                COALESCE(hc.MotivoHC, c.Motivo_Consulta, '') AS Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                ea.Nombre_Estado                          AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos         AS NombreEspecialista,
                esp.Nombre_Especialidad,
                hc.Historial_ID,
                hc.MapaDental,
                hc.Hallazgos,
                COALESCE(hc.MotivoHC, '') AS MotivoHC,
                (
                    SELECT d.Codigo || ' — ' || d.Nombre_Diagnostico
                    FROM historial_diagnostico hd
                    JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                    WHERE hd.Historial_ID = hc.Historial_ID
                    ORDER BY hd.rowid DESC
                    LIMIT 1
                ) AS DiagnosticoRaw,
                (
                    SELECT t.Descripcion
                    FROM tratamiento t
                    WHERE t.Historial_ID = hc.Historial_ID
                    ORDER BY t.Tratamiento_ID DESC
                    LIMIT 1
                ) AS TratamientoRaw,
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
            filas_raw = []

        filas = []
        for r in filas_raw:
            f = dict(r)

            diagnostico_bd  = f.pop('DiagnosticoRaw',  None) or ''
            tratamiento_raw = f.pop('TratamientoRaw',  None) or ''

            evolucion_bd, tratamiento_bd = _descomprimir_evolucion_tratamiento(tratamiento_raw)

            f = _aplicar_claves_unificadas_reporte(f, diagnostico_bd, evolucion_bd, tratamiento_bd)
            f['Motivo_Consulta'] = f.get('Motivo_Consulta') or ''
            f['MapaDental']      = f.get('MapaDental')      or ''
            f['Hallazgos']       = f.get('Hallazgos')       or ''
            f['FechaRegistro']   = f.get('FechaRegistro')   or ''
            filas.append(f)

        return _json_ok({"ok": True, "data": filas})

    except Exception:
        return _json_ok({"ok": True, "data": []})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — DATOS CLÍNICOS DE UNA CITA ESPECÍFICA
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/cita/<int:cita_id>', methods=['GET'])
def get_historial_por_cita(cita_id):
    paciente_id_qs = request.args.get('paciente_id', type=int)
    usuario_id_qs  = request.args.get('usuario_id', type=int)

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        # ── Validación de propiedad: el paciente sólo ve sus propias citas ──
        permitido, err_resp = _validar_propiedad_cita(cur, cita_id, paciente_id_qs, usuario_id_qs)
        if not permitido:
            return err_resp

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    COALESCE(hc.MotivoHC, c.Motivo_Consulta, '') AS Motivo_Consulta,
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
                    COALESCE(hc.MotivoHC, '') AS MotivoHC,
                    (
                        SELECT d.Codigo || ' — ' || d.Nombre_Diagnostico
                        FROM historial_diagnostico hd
                        JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                        WHERE hd.Historial_ID = hc.Historial_ID
                        ORDER BY hd.rowid DESC
                        LIMIT 1
                    ) AS DiagnosticoRaw,
                    (
                        SELECT t.Descripcion
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS TratamientoRaw,
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
                LEFT JOIN tipo_documento td ON td.TipoDoc_ID  = up.TipoDoc_ID
                LEFT JOIN historial_clinico hc ON hc.Cita_ID  = c.Cita_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        if not row:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        try:
            data = dict(row)

            diagnostico_bd  = data.pop('DiagnosticoRaw',  None) or ''
            tratamiento_raw = data.pop('TratamientoRaw',  None) or ''

            evolucion_bd, tratamiento_bd = _descomprimir_evolucion_tratamiento(tratamiento_raw)

            data = _aplicar_claves_unificadas_reporte(data, diagnostico_bd, evolucion_bd, tratamiento_bd)
            data['MotivoHC']      = data.get('MotivoHC')      or ''
            data['MapaDental']    = data.get('MapaDental')     or ''
            data['Hallazgos']     = data.get('Hallazgos')      or ''
            data['FechaAtencion'] = data.get('FechaAtencion')  or ''
            data['FechaRegistro'] = data.get('FechaRegistro')  or ''
            data = _normalizar_datos_paciente(data)

            return _json_ok({"ok": True, "data": data})
        except Exception:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

    except Exception:
        return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — REPORTE CLÍNICO PARA EL PACIENTE (SOLO LECTURA)
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/cita/<int:cita_id>/reporte', methods=['GET'])
def get_reporte_cita_paciente(cita_id):
    """
    GET /api/cita/<cita_id>/reporte?paciente_id=<opcional>&usuario_id=<opcional>

    Endpoint de solo lectura pensado para el Panel del Paciente. Reutiliza
    exactamente la misma lógica de resolución de diagnóstico/evolución/
    tratamiento que usa el módulo del especialista, garantizando que ambos
    paneles muestren siempre la misma información para una misma cita.

    Si se recibe 'paciente_id' o 'usuario_id' por querystring, se valida
    que la cita pertenezca a ese paciente antes de devolver los datos
    clínicos, evitando que un paciente consulte reportes ajenos.
    """
    paciente_id_qs = request.args.get('paciente_id', type=int)
    usuario_id_qs  = request.args.get('usuario_id', type=int)

    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        permitido, err_resp = _validar_propiedad_cita(cur, cita_id, paciente_id_qs, usuario_id_qs)
        if not permitido:
            return err_resp

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    COALESCE(hc.MotivoHC, c.Motivo_Consulta, '') AS Motivo_Consulta,
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
                    COALESCE(hc.MotivoHC, '') AS MotivoHC,
                    (
                        SELECT d.Codigo || ' — ' || d.Nombre_Diagnostico
                        FROM historial_diagnostico hd
                        JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                        WHERE hd.Historial_ID = hc.Historial_ID
                        ORDER BY hd.rowid DESC
                        LIMIT 1
                    ) AS DiagnosticoRaw,
                    (
                        SELECT t.Descripcion
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS TratamientoRaw,
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
                LEFT JOIN tipo_documento td ON td.TipoDoc_ID  = up.TipoDoc_ID
                LEFT JOIN historial_clinico hc ON hc.Cita_ID  = c.Cita_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        if not row:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        try:
            data = dict(row)

            diagnostico_bd  = data.pop('DiagnosticoRaw',  None) or ''
            tratamiento_raw = data.pop('TratamientoRaw',  None) or ''

            evolucion_bd, tratamiento_bd = _descomprimir_evolucion_tratamiento(tratamiento_raw)

            data = _aplicar_claves_unificadas_reporte(data, diagnostico_bd, evolucion_bd, tratamiento_bd)
            data['MotivoHC']      = data.get('MotivoHC')      or ''
            data['MapaDental']    = data.get('MapaDental')     or ''
            data['Hallazgos']     = data.get('Hallazgos')      or ''
            data['FechaAtencion'] = data.get('FechaAtencion')  or ''
            data['FechaRegistro'] = data.get('FechaRegistro')  or ''
            data = _normalizar_datos_paciente(data)

            return _json_ok({"ok": True, "data": data})
        except Exception:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

    except Exception:
        return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — ESTADO EN TIEMPO REAL DE UNA CITA (SONDEO / POLLING)
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/citas/<int:cita_id>/estado', methods=['GET'])
def get_estado_cita(cita_id):
    """
    GET /api/citas/<cita_id>/estado

    Endpoint ligero para el setInterval de sondeo del Panel del Paciente.
    Devuelve únicamente el estado actual de la agenda y de la multa
    asociada (si existe), sin cargar el resto de la información clínica.
    Diseñado para NUNCA responder con HTTP 500: ante cualquier fallo de
    esquema o de datos retorna un estado neutro con código 200.
    """
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    c.Paciente_ID,
                    a.Fecha,
                    a.Hora_Inicio,
                    ea.Nombre_Estado AS EstadoAgenda
                FROM cita c
                JOIN agenda a         ON a.Agenda_ID        = c.Agenda_ID
                JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError:
            row = None

        if not row:
            return _json_ok({
                "ok": True,
                "data": {
                    "Cita_ID":      cita_id,
                    "Fecha":        "",
                    "Hora_Inicio":  "",
                    "EstadoAgenda": "",
                    "EstadoMulta":  "Sin multa",
                }
            })

        data = dict(row)

        estado_multa = "Sin multa"
        try:
            cur.execute("""
                SELECT em.Nombre_Estado AS EstadoMulta
                FROM multa m
                JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
                WHERE m.Cita_ID = ?
                ORDER BY m.Multa_ID DESC
                LIMIT 1
            """, (cita_id,))
            mrow = cur.fetchone()
            if mrow and mrow['EstadoMulta']:
                estado_multa = mrow['EstadoMulta']
        except sqlite3.OperationalError:
            estado_multa = "Sin multa"
        except Exception:
            estado_multa = "Sin multa"

        data['EstadoMulta'] = estado_multa

        return _json_ok({"ok": True, "data": data})

    except Exception:
        return _json_ok({
            "ok": True,
            "data": {
                "Cita_ID":      cita_id,
                "Fecha":        "",
                "Hora_Inicio":  "",
                "EstadoAgenda": "",
                "EstadoMulta":  "Sin multa",
            }
        })
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — RESPALDO DE COMPATIBILIDAD
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial-clinico/<int:cita_id>', methods=['GET'])
def get_historial_clinico_legacy(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        try:
            cur.execute("""
                SELECT
                    c.Cita_ID,
                    COALESCE(hc.MotivoHC, c.Motivo_Consulta, '') AS Motivo_Consulta,
                    c.FechaAtencion,
                    a.Fecha,
                    a.Hora_Inicio,
                    up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                    td.Nombre_Tipo_Documento           AS TipoDocumento,
                    up.NumeroDocumento,
                    hc.Historial_ID,
                    hc.MapaDental,
                    hc.Hallazgos,
                    COALESCE(hc.MotivoHC, '') AS MotivoHC,
                    (
                        SELECT d.Codigo || ' — ' || d.Nombre_Diagnostico
                        FROM historial_diagnostico hd
                        JOIN diagnostico d ON d.Diagnostico_ID = hd.Diagnostico_ID
                        WHERE hd.Historial_ID = hc.Historial_ID
                        ORDER BY hd.rowid DESC
                        LIMIT 1
                    ) AS DiagnosticoRaw,
                    (
                        SELECT t.Descripcion
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS TratamientoRaw,
                    (
                        SELECT t.FechaRegistro
                        FROM tratamiento t
                        WHERE t.Historial_ID = hc.Historial_ID
                        ORDER BY t.Tratamiento_ID DESC
                        LIMIT 1
                    ) AS FechaRegistro
                FROM cita c
                LEFT JOIN agenda a    ON a.Agenda_ID    = c.Agenda_ID
                LEFT JOIN paciente p  ON p.Paciente_ID  = c.Paciente_ID
                LEFT JOIN usuarios up ON up.Usuario_ID  = p.Usuario_ID
                LEFT JOIN tipo_documento td ON td.TipoDoc_ID = up.TipoDoc_ID
                LEFT JOIN historial_clinico hc ON hc.Cita_ID = c.Cita_ID
                WHERE c.Cita_ID = ?
                LIMIT 1
            """, (cita_id,))
            row = cur.fetchone()
        except sqlite3.OperationalError:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        if not row:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

        try:
            data = dict(row)

            diagnostico_bd  = data.pop('DiagnosticoRaw',  None) or ''
            tratamiento_raw = data.pop('TratamientoRaw',  None) or ''

            evolucion_bd, tratamiento_bd = _descomprimir_evolucion_tratamiento(tratamiento_raw)

            data = _aplicar_claves_unificadas_reporte(data, diagnostico_bd, evolucion_bd, tratamiento_bd)
            data['MotivoHC']      = data.get('MotivoHC')      or ''
            data['MapaDental']    = data.get('MapaDental')     or ''
            data['Hallazgos']     = data.get('Hallazgos')      or ''
            data['FechaAtencion'] = data.get('FechaAtencion')  or ''
            data['FechaRegistro'] = data.get('FechaRegistro')  or ''
            data = _normalizar_datos_paciente(data)

            return _json_ok({"ok": True, "data": data})
        except Exception:
            return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})

    except Exception:
        return _json_ok({"ok": True, "data": _respuesta_vacia_cita(cita_id)})
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — DATOS DE CITA
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/citas/<int:cita_id>', methods=['GET'])
def get_cita_detalle(cita_id):
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Paciente_ID,
                c.Motivo_Consulta,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                td.Nombre_Tipo_Documento           AS TipoDocumento,
                up.NumeroDocumento                 AS NumeroDocumento
            FROM cita c
            LEFT JOIN paciente p  ON p.Paciente_ID = c.Paciente_ID
            LEFT JOIN usuarios up ON up.Usuario_ID  = p.Usuario_ID
            LEFT JOIN tipo_documento td ON td.TipoDoc_ID = up.TipoDoc_ID
            WHERE c.Cita_ID = ?
            LIMIT 1
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        data = dict(row)
        data['TipoDocumento']   = data.get('TipoDocumento')   or ''
        data['NumeroDocumento'] = data.get('NumeroDocumento') or ''
        return _json_ok(data)
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# HELPER INTERNO: núcleo de escritura de historia clínica
# ══════════════════════════════════════════════════════════════════════════════

def _escribir_historial(cur, cita_id, motivo_hc, diagnostico, diagnostico_id,
                        evolucion, tratamiento, mapa_dental, hallazgos, fecha_ahora):
    """
    Inserta o actualiza el historial clínico de una cita dentro de una
    transacción ya iniciada por el caller.  Devuelve el historial_id.

    Lógica de resolución del diagnóstico (en orden de prioridad):
      1. diagnostico_id numérico explícito → busca en diagnostico por PK.
      2. Texto que empiece con código CIE-10 (patrón "[CODIGO] — NOMBRE" o
         "CODIGO — NOMBRE") → extrae y busca por Codigo en la tabla.
      3. Búsqueda por Nombre_Diagnostico exacto.
      4. Si no existe, inserta un registro nuevo (solo con nombre, sin código).
    """
    # 1. Obtener o crear registro principal en historial_clinico
    cur.execute(
        "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?",
        (cita_id,)
    )
    hc_row = cur.fetchone()
    if hc_row:
        historial_id = hc_row['Historial_ID']
    else:
        cur.execute(
            "INSERT INTO historial_clinico (Cita_ID) VALUES (?)",
            (cita_id,)
        )
        historial_id = cur.lastrowid

    # 2. Guardar motivo en la columna MotivoHC
    if motivo_hc:
        cur.execute(
            "UPDATE historial_clinico SET MotivoHC = ? WHERE Historial_ID = ?",
            (motivo_hc, historial_id)
        )

    # 3. Resolver diagnóstico → Diagnostico_ID
    if diagnostico or diagnostico_id:
        diag_id = None

        # 3a. Buscar por ID explícito
        if diagnostico_id:
            try:
                cur.execute(
                    "SELECT Diagnostico_ID FROM diagnostico WHERE Diagnostico_ID = ?",
                    (int(diagnostico_id),)
                )
                dr = cur.fetchone()
                if dr:
                    diag_id = dr['Diagnostico_ID']
            except (ValueError, TypeError):
                pass

        # 3b. Extraer código del texto con formato "[K02.0] — NOMBRE" o "K020 — NOMBRE"
        if not diag_id and diagnostico:
            import re
            # Acepta "[K020]", "K020", "[K02.0]", "K02.0" al inicio del string
            m = re.match(r'^\[?([A-Z]\d+(?:\.\d+)?)\]?\s*(?:—|-|–)?\s*', diagnostico, re.IGNORECASE)
            if m:
                codigo_extraido = m.group(1).upper().replace('.', '')
                cur.execute(
                    "SELECT Diagnostico_ID FROM diagnostico WHERE REPLACE(Codigo, '.', '') = ?",
                    (codigo_extraido,)
                )
                dr = cur.fetchone()
                if dr:
                    diag_id = dr['Diagnostico_ID']

        # 3c. Buscar por nombre exacto (ignorando mayúsculas)
        if not diag_id and diagnostico:
            cur.execute(
                "SELECT Diagnostico_ID FROM diagnostico "
                "WHERE UPPER(Nombre_Diagnostico) = UPPER(?)",
                (diagnostico,)
            )
            dr = cur.fetchone()
            if dr:
                diag_id = dr['Diagnostico_ID']

        # 3d. Insertar diagnóstico nuevo si no existe en el catálogo
        if not diag_id and diagnostico:
            cur.execute(
                "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)",
                (diagnostico,)
            )
            diag_id = cur.lastrowid

        # 4. Actualizar relación historial ↔ diagnóstico
        if diag_id:
            cur.execute(
                "DELETE FROM historial_diagnostico WHERE Historial_ID = ?",
                (historial_id,)
            )
            cur.execute(
                "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diag_id)
            )

    # 5. Compactar evolución + tratamiento en una sola fila de tratamiento
    desc = ''
    if evolucion and tratamiento:
        desc = f"{evolucion}\n---\n{tratamiento}"
    elif evolucion:
        desc = evolucion
    elif tratamiento:
        desc = tratamiento

    if desc:
        cur.execute(
            "DELETE FROM tratamiento WHERE Historial_ID = ?",
            (historial_id,)
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

    # 6. Guardar mapa dental y hallazgos
    cur.execute(
        "UPDATE historial_clinico SET MapaDental = ?, Hallazgos = ? WHERE Historial_ID = ?",
        (str(mapa_dental), str(hallazgos), historial_id)
    )

    return historial_id


# ══════════════════════════════════════════════════════════════════════════════
# API — GUARDAR HISTORIA CLÍNICA (borrador, sin cambiar estado de agenda)
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/guardar', methods=['POST'])
def guardar_historia_clinica():
    datos          = request.get_json(silent=True) or {}
    cita_id        = datos.get('Cita_ID')
    diagnostico    = (datos.get('Diagnostico')    or '').strip()
    diagnostico_id = datos.get('DiagnosticoID')
    evolucion      = (datos.get('Evolucion')      or '').strip()
    tratamiento    = (datos.get('Tratamiento')    or '').strip()
    mapa_dental    = datos.get('MapaDental')      or '{}'
    hallazgos      = datos.get('Hallazgos')       or '[]'
    motivo_hc      = (datos.get('MotivoConsulta') or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()

        # ── Migraciones DDL ANTES de abrir la transacción DML ──────────────
        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        # ── Verificar que la cita existe ────────────────────────────────────
        cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        if not cur.fetchone():
            return _json_error('Cita no encontrada.', 404)

        fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ── Transacción DML limpia ──────────────────────────────────────────
        cur.execute("BEGIN")
        historial_id = _escribir_historial(
            cur, cita_id, motivo_hc, diagnostico, diagnostico_id,
            evolucion, tratamiento, mapa_dental, hallazgos, fecha_ahora
        )
        cur.execute("COMMIT")

        return _json_ok({
            "ok": True,
            "Historial_ID": historial_id,
            "mensaje": "Historia clínica guardada correctamente.",
            "FechaGuardado": fecha_ahora
        }, 201)

    except Exception as exc:
        if con:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
        return _json_error(f"Error al guardar historia clínica: {exc}", 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — FINALIZAR CONSULTA
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/finalizar', methods=['POST'])
def finalizar_desde_historial():
    datos          = request.get_json(silent=True) or {}
    cita_id        = datos.get('Cita_ID')
    diagnostico    = (datos.get('Diagnostico')    or '').strip()
    diagnostico_id = datos.get('DiagnosticoID')
    evolucion      = (datos.get('Evolucion')      or '').strip()
    tratamiento    = (datos.get('Tratamiento')    or '').strip()
    mapa_dental    = datos.get('MapaDental')      or '{}'
    hallazgos      = datos.get('Hallazgos')       or '[]'
    motivo_hc      = (datos.get('MotivoConsulta') or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()

        # ── Migraciones DDL ANTES de abrir la transacción DML ──────────────
        _ensure_historial_columns(cur)
        _ensure_cita_columns(cur)
        _ensure_tratamiento_columns(cur)

        # ── Verificar cita y obtener Agenda_ID ─────────────────────────────
        cur.execute(
            "SELECT c.Cita_ID, a.Agenda_ID "
            "FROM cita c JOIN agenda a ON a.Agenda_ID = c.Agenda_ID "
            "WHERE c.Cita_ID = ?",
            (cita_id,)
        )
        cita_row = cur.fetchone()
        if not cita_row:
            return _json_error('Cita no encontrada.', 404)

        agenda_id   = cita_row['Agenda_ID']
        fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ── Transacción DML única ───────────────────────────────────────────
        cur.execute("BEGIN")

        # 1. Marcar agenda como Cumplida (EstadoAgenda_ID = 4)
        cur.execute(
            "UPDATE agenda SET EstadoAgenda_ID = 4 WHERE Agenda_ID = ?",
            (agenda_id,)
        )

        # 2. Registrar fecha de atención en la cita
        cur.execute(
            "UPDATE cita SET FechaAtencion = ? WHERE Cita_ID = ?",
            (fecha_ahora, cita_id)
        )

        # 3. Escribir todo el contenido clínico
        historial_id = _escribir_historial(
            cur, cita_id, motivo_hc, diagnostico, diagnostico_id,
            evolucion, tratamiento, mapa_dental, hallazgos, fecha_ahora
        )

        cur.execute("COMMIT")

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
        return _json_error(f"Error al finalizar consulta: {exc}", 500)
    finally:
        if con:
            con.close()