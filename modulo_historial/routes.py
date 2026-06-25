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
    POST /api/historial/guardar
    POST /api/historial/finalizar

REGISTRO EN app.py (sin url_prefix):
    from modulo_historial.routes import historial_bp
    app.register_blueprint(historial_bp)

  ⚠ NO usar url_prefix aquí porque las rutas de API ya llevan
    el segmento /api/ embebido en cada decorador, garantizando
    que nunca colisionen con citas_bp (que sí usa url_prefix='/api').

COLISIÓN EVITADA:
  /api/historial-clinico/<cita_id>  → vive en citas_bp  (devuelve JSON)
  /api/historial/paciente/<id>/...  → vive aquí          (devuelve JSON)
  /historial/paciente/<id>          → vive aquí          (devuelve HTML)
  Las tres rutas son léxicamente distintas → cero conflictos.
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
    return jsonify(data), code


def _json_error(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code


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


# ══════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL
# GET /historial/paciente/<paciente_id>?cita_id=<cita_id>
#
# ▸ SIEMPRE devuelve render_template('historia_clinica.html')
# ▸ NUNCA devuelve jsonify()
# ▸ Es el ÚNICO endpoint que el navegador debe visitar para abrir la HC
# ▸ Los valores paciente_id y cita_id se inyectan en data-* del <body>
#   para que el JS del frontend los lea sin necesidad de variables inline
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def vista_historia_clinica(paciente_id):
    """
    Ruta de VISTA — renderiza historia_clinica.html.

    El frontend SIEMPRE debe navegar aquí (window.location.href).
    Jamás debe hacer fetch() a esta URL; eso devolvería HTML al fetch
    y el navegador lo ignoraría sin navegar.
    """
    cita_id = request.args.get('cita_id', type=int)
    return render_template(
        'historia_clinica.html',
        paciente_id=paciente_id,
        # Si cita_id es None, Jinja2 recibe string vacío → data-cita-id=""
        # y el JS lo convierte en 0 de forma segura con parseInt(... || '0', 10)
        cita_id=cita_id if cita_id else ''
    )


# ══════════════════════════════════════════════════════════════════════════════
# API — INFORMACIÓN CLÍNICA DEL PACIENTE
# GET /api/historial/paciente/<paciente_id>/info
#
# ▸ SIEMPRE devuelve jsonify()
# ▸ NUNCA devuelve render_template()
# ▸ Solo la llama el JS de historia_clinica.js vía fetch(), nunca el navegador
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

        # Fallback legacy: intentar TipoAfiliacion desde tipo_eps
        if not info.get('TipoAfiliacion'):
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
# ▸ SIEMPRE devuelve jsonify()
# ▸ NUNCA devuelve render_template()
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/evoluciones', methods=['GET'])
def get_evoluciones_paciente(paciente_id):
    """Ruta de API — devuelve el historial de evoluciones como JSON."""
    cita_id = request.args.get('cita_id', type=int)
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        sql = """
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                ea.Nombre_Estado                          AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos         AS NombreEspecialista,
                esp.Nombre_Especialidad,
                hc.Historial_ID,
                d.Nombre_Diagnostico                      AS Diagnostico,
                t.Descripcion                             AS Tratamiento,
                t.FechaRegistro
            FROM cita c
            JOIN agenda a        ON a.Agenda_ID        = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue     ON ue.Usuario_ID       = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN historial_clinico hc ON hc.Cita_ID = c.Cita_ID
            LEFT JOIN historial_diagnostico hd ON hd.Historial_ID = hc.Historial_ID
            LEFT JOIN diagnostico d  ON d.Diagnostico_ID = hd.Diagnostico_ID
            LEFT JOIN tratamiento t  ON t.Historial_ID   = hc.Historial_ID
            WHERE c.Paciente_ID = ?
        """
        params = [paciente_id]
        if cita_id:
            sql += " AND c.Cita_ID = ?"
            params.append(cita_id)

        sql += " GROUP BY c.Cita_ID ORDER BY a.Fecha DESC, a.Hora_Inicio DESC"
        cur.execute(sql, params)

        filas = [dict(r) for r in cur.fetchall()]

        # Descomprimir campo Tratamiento codificado como "evolucion\n---\ntratamiento"
        for f in filas:
            desc = f.get('Tratamiento') or ''
            if '---' in desc:
                partes       = desc.split('---', 1)
                f['Evolucion']   = partes[0].strip()
                f['Tratamiento'] = partes[1].strip()
            else:
                f['Evolucion']   = desc
                f['Tratamiento'] = ''

        return _json_ok({"ok": True, "data": filas})

    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ══════════════════════════════════════════════════════════════════════════════
# API — GUARDAR HISTORIA CLÍNICA
# POST /api/historial/guardar
#
# ▸ SIEMPRE devuelve jsonify()
# ▸ NUNCA devuelve render_template()
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
    motivo      = (datos.get('MotivoConsulta') or '').strip()

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

        if motivo:
            cur.execute(
                "UPDATE cita SET Motivo_Consulta = ? WHERE Cita_ID = ?",
                (motivo, cita_id)
            )

        # Upsert historial_clinico
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

        # Diagnóstico
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

        # Tratamiento (codificado con separador para preservar evolución)
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

        # Columnas opcionales MapaDental / Hallazgos (ALTER si no existen)
        cur.execute("PRAGMA table_info(historial_clinico)")
        hc_cols = [c[1] for c in cur.fetchall()]
        if 'MapaDental' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MapaDental TEXT")
        if 'Hallazgos' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN Hallazgos TEXT")
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
#
# ▸ SIEMPRE devuelve jsonify()
# ▸ NUNCA devuelve render_template()
# ══════════════════════════════════════════════════════════════════════════════

@historial_bp.route('/api/historial/finalizar', methods=['POST'])
def finalizar_desde_historial():
    """Ruta de API — guarda la HC y marca la agenda como EstadoAgenda_ID = 4 (Cumplida)."""
    datos       = request.get_json(silent=True) or {}
    cita_id     = datos.get('Cita_ID')
    diagnostico = (datos.get('Diagnostico')    or '').strip()
    evolucion   = (datos.get('Evolucion')      or '').strip()
    tratamiento = (datos.get('Tratamiento')    or '').strip()
    mapa_dental = datos.get('MapaDental')      or '{}'
    hallazgos   = datos.get('Hallazgos')       or '[]'
    motivo      = (datos.get('MotivoConsulta') or '').strip()

    if not cita_id:
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
            return _json_error('Cita no encontrada.', 404)

        if motivo:
            cur.execute(
                "UPDATE cita SET Motivo_Consulta = ? WHERE Cita_ID = ?",
                (motivo, cita_id)
            )

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
        cur.execute("PRAGMA table_info(historial_clinico)")
        hc_cols = [c[1] for c in cur.fetchall()]
        if 'MapaDental' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN MapaDental TEXT")
        if 'Hallazgos' not in hc_cols:
            cur.execute("ALTER TABLE historial_clinico ADD COLUMN Hallazgos TEXT")
        cur.execute(
            "UPDATE historial_clinico SET MapaDental = ?, Hallazgos = ? WHERE Historial_ID = ?",
            (str(mapa_dental), str(hallazgos), historial_id)
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
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()