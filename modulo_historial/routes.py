"""
modulo_historial/routes.py — Stylo Dental
==========================================
Endpoints para Historia Clínica:

  • GET  /historial/paciente/<paciente_id>          — Renderiza la vista HC con datos del paciente
  • GET  /api/historial/paciente/<paciente_id>/info  — Datos clínicos del paciente (JSON)
  • GET  /api/historial/paciente/<paciente_id>/evoluciones — Historial de evoluciones (JSON)
  • POST /api/historial/guardar                      — Guarda/actualiza la historia clínica
"""

import os
import sqlite3
from datetime import datetime, date
from flask import Blueprint, request, jsonify, render_template, session

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


# ─────────────────────────────────────────────────────────────────────────────
# VISTA PRINCIPAL — GET /historial/paciente/<paciente_id>
# Recibe también cita_id como query param opcional (?cita_id=)
# ─────────────────────────────────────────────────────────────────────────────

@historial_bp.route('/historial/paciente/<int:paciente_id>', methods=['GET'])
def vista_historia_clinica(paciente_id):
    cita_id = request.args.get('cita_id', type=int)
    return render_template(
        'historia_clinica.html',
        paciente_id=paciente_id,
        cita_id=cita_id or ''
    )


# ─────────────────────────────────────────────────────────────────────────────
# API — INFORMACIÓN CLÍNICA DEL PACIENTE
# GET /api/historial/paciente/<paciente_id>/info
# ─────────────────────────────────────────────────────────────────────────────

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
            JOIN usuarios u        ON u.Usuario_ID      = p.Usuario_ID
            LEFT JOIN tipo_documento td  ON td.TipoDoc_ID    = u.TipoDoc_ID
            LEFT JOIN afiliacion a       ON a.Usuario_ID     = u.Usuario_ID
            LEFT JOIN eps               ON eps.EPS_ID        = a.EPS_ID
            LEFT JOIN regimen_eps re    ON re.Regimen_ID     = eps.Regimen_ID
            LEFT JOIN tipo_afiliacion_eps tae ON tae.TipoEPS_ID = a.TipoEPS_ID
            WHERE p.Paciente_ID = ?
            LIMIT 1
        """, (paciente_id,))
        row = cur.fetchone()

        if not row:
            return _json_error('Paciente no encontrado.', 404)

        info = dict(row)
        info['Edad'] = _calcular_edad(info.get('FechaNacimiento'))

        # Si no tiene afiliación en tabla nueva, intentar con tipo_eps (legacy)
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


# ─────────────────────────────────────────────────────────────────────────────
# API — EVOLUCIONES / HISTORIAL DE UNA CITA ESPECÍFICA
# GET /api/historial/paciente/<paciente_id>/evoluciones?cita_id=
# ─────────────────────────────────────────────────────────────────────────────

@historial_bp.route('/api/historial/paciente/<int:paciente_id>/evoluciones', methods=['GET'])
def get_evoluciones_paciente(paciente_id):
    cita_id = request.args.get('cita_id', type=int)
    con = None
    try:
        con = _get_conn()
        cur = con.cursor()

        # Obtener todas las citas del paciente con su historial
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
            JOIN agenda a       ON a.Agenda_ID      = c.Agenda_ID
            JOIN estado_agenda ea ON ea.EstadoAgenda_ID = a.EstadoAgenda_ID
            JOIN especialista e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue   ON ue.Usuario_ID     = e.Usuario_ID
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

        # Para cada fila, parsear evolución y tratamiento si están combinados
        for f in filas:
            desc = f.get('Tratamiento') or ''
            if '---' in desc:
                partes = desc.split('---', 1)
                f['Evolucion']   = partes[0].strip()
                f['Tratamiento'] = partes[1].strip()
            else:
                f['Evolucion'] = desc
                if '---' not in desc:
                    f['Tratamiento'] = ''

        return _json_ok({"ok": True, "data": filas})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con:
            con.close()


# ─────────────────────────────────────────────────────────────────────────────
# API — GUARDAR HISTORIA CLÍNICA
# POST /api/historial/guardar
# Body JSON: { Cita_ID, Diagnostico, Evolucion, Tratamiento,
#              MapaDental (JSON string), Hallazgos (JSON string),
#              MotivoConsulta }
# ─────────────────────────────────────────────────────────────────────────────

@historial_bp.route('/api/historial/guardar', methods=['POST'])
def guardar_historia_clinica():
    datos        = request.get_json(silent=True) or {}
    cita_id      = datos.get('Cita_ID')
    diagnostico  = (datos.get('Diagnostico')    or '').strip()
    evolucion    = (datos.get('Evolucion')       or '').strip()
    tratamiento  = (datos.get('Tratamiento')     or '').strip()
    mapa_dental  = datos.get('MapaDental')       or '{}'
    hallazgos    = datos.get('Hallazgos')        or '[]'
    motivo       = (datos.get('MotivoConsulta')  or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        # Verificar que la cita existe
        cur.execute("SELECT Cita_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        if not cur.fetchone():
            cur.execute("ROLLBACK")
            return _json_error('Cita no encontrada.', 404)

        # Actualizar motivo de consulta si se proporcionó
        if motivo:
            cur.execute(
                "UPDATE cita SET Motivo_Consulta = ? WHERE Cita_ID = ?",
                (motivo, cita_id)
            )

        # Obtener o crear historial clínico
        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
        )
        hc_row = cur.fetchone()
        if hc_row:
            historial_id = hc_row['Historial_ID']
        else:
            cur.execute(
                "INSERT INTO historial_clinico (Cita_ID) VALUES (?)", (cita_id,)
            )
            historial_id = cur.lastrowid

        # ── Diagnóstico ───────────────────────────────────────────────────────
        if diagnostico:
            # Buscar o crear diagnóstico
            cur.execute(
                "SELECT Diagnostico_ID FROM diagnostico WHERE Nombre_Diagnostico = ?",
                (diagnostico,)
            )
            diag_row = cur.fetchone()
            if diag_row:
                diag_id = diag_row['Diagnostico_ID']
            else:
                cur.execute(
                    "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)", (diagnostico,)
                )
                diag_id = cur.lastrowid

            # Limpiar diagnósticos anteriores de este historial y reinsertar
            cur.execute(
                "DELETE FROM historial_diagnostico WHERE Historial_ID = ?", (historial_id,)
            )
            cur.execute(
                "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diag_id)
            )

        # ── Evolución + Tratamiento (combinados en descripción) ───────────────
        descripcion_combinada = ''
        if evolucion and tratamiento:
            descripcion_combinada = f"{evolucion}\n---\n{tratamiento}"
        elif evolucion:
            descripcion_combinada = evolucion
        elif tratamiento:
            descripcion_combinada = tratamiento

        if descripcion_combinada:
            # Eliminar tratamiento anterior y crear uno nuevo con timestamp
            cur.execute(
                "DELETE FROM tratamiento WHERE Historial_ID = ?", (historial_id,)
            )
            # Verificar si existe columna FechaRegistro
            cur.execute("PRAGMA table_info(tratamiento)")
            cols = [c[1] for c in cur.fetchall()]
            fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if 'FechaRegistro' in cols:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion, FechaRegistro) VALUES (?, ?, ?)",
                    (historial_id, descripcion_combinada, fecha_ahora)
                )
            else:
                cur.execute(
                    "INSERT INTO tratamiento (Historial_ID, Descripcion) VALUES (?, ?)",
                    (historial_id, descripcion_combinada)
                )

        # ── Mapa dental y hallazgos (columnas opcionales en historial_clinico) ─
        # Añadir columnas si no existen
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


# ─────────────────────────────────────────────────────────────────────────────
# API — FINALIZAR CONSULTA DESDE HISTORIA CLÍNICA
# POST /api/historial/finalizar
# Guarda los datos y marca la cita como atendida.
# ─────────────────────────────────────────────────────────────────────────────

@historial_bp.route('/api/historial/finalizar', methods=['POST'])
def finalizar_desde_historial():
    datos       = request.get_json(silent=True) or {}
    cita_id     = datos.get('Cita_ID')
    diagnostico = (datos.get('Diagnostico')  or '').strip()
    evolucion   = (datos.get('Evolucion')    or '').strip()
    tratamiento = (datos.get('Tratamiento')  or '').strip()
    mapa_dental = datos.get('MapaDental')    or '{}'
    hallazgos   = datos.get('Hallazgos')     or '[]'
    motivo      = (datos.get('MotivoConsulta') or '').strip()

    if not cita_id:
        return _json_error('Cita_ID es obligatorio.')

    con = None
    try:
        con = _get_conn()
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        # Verificar cita
        cur.execute(
            "SELECT c.Cita_ID, a.Agenda_ID, a.EstadoAgenda_ID FROM cita c "
            "JOIN agenda a ON a.Agenda_ID = c.Agenda_ID WHERE c.Cita_ID = ?",
            (cita_id,)
        )
        cita_row = cur.fetchone()
        if not cita_row:
            cur.execute("ROLLBACK")
            return _json_error('Cita no encontrada.', 404)

        # Actualizar motivo
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

        # FechaAtencion en cita
        fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("PRAGMA table_info(cita)")
        cita_cols = [c[1] for c in cur.fetchall()]
        if 'FechaAtencion' not in cita_cols:
            cur.execute("ALTER TABLE cita ADD COLUMN FechaAtencion TEXT")
        cur.execute(
            "UPDATE cita SET FechaAtencion = ? WHERE Cita_ID = ?",
            (fecha_ahora, cita_id)
        )

        # Historial clínico
        cur.execute(
            "SELECT Historial_ID FROM historial_clinico WHERE Cita_ID = ?", (cita_id,)
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
            if dr:
                diag_id = dr['Diagnostico_ID']
            else:
                cur.execute(
                    "INSERT INTO diagnostico (Nombre_Diagnostico) VALUES (?)", (diagnostico,)
                )
                diag_id = cur.lastrowid
            cur.execute(
                "DELETE FROM historial_diagnostico WHERE Historial_ID = ?", (historial_id,)
            )
            cur.execute(
                "INSERT INTO historial_diagnostico (Historial_ID, Diagnostico_ID) VALUES (?, ?)",
                (historial_id, diag_id)
            )

        # Descripción combinada
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

        # Mapa dental y hallazgos
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
            "FechaAtencion": fecha_ahora,
            "mensaje": "Consulta finalizada y registrada correctamente."
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