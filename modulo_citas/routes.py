"""
modulo_citas/routes.py — Stylo Dental
======================================
Endpoints REST para:
  • /api/citas            — listar y crear citas
  • /api/citas/<id>       — detalle, actualizar estado y cancelar
  • /api/agenda           — slots disponibles (por especialista / fecha)
  • /api/especialistas    — lista de especialistas con su especialidad
  • /api/multas           — listar y actualizar multas
  • /api/paciente/<id>/citas — citas de un paciente específico
"""

from flask import Blueprint, request, jsonify
from db import get_db_connection

citas_bp = Blueprint('citas_bp', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES INTERNAS
# ─────────────────────────────────────────────────────────────────────────────

def _rows_to_list(cursor):
    """Convierte los resultados de un cursor en lista de dicts."""
    return [dict(row) for row in cursor.fetchall()]


def _json_ok(data, code=200):
    return jsonify(data), code


def _json_error(mensaje, code=400):
    return jsonify({"ok": False, "error": mensaje}), code


# ─────────────────────────────────────────────────────────────────────────────
# ESPECIALISTAS  —  GET /api/especialistas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialistas', methods=['GET'])
def get_especialistas():
    """
    Devuelve todos los especialistas con nombre completo y especialidad.
    Útil para el selector de agendar.html.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                e.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos   AS NombreCompleto,
                GROUP_CONCAT(esp.Nombre_Especialidad, ', ') AS Especialidades,
                e.Tarjeta_Profesional
            FROM especialistas e
            JOIN usuarios u        ON u.Usuario_ID      = e.Usuario_ID
            JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            JOIN especialidad esp  ON esp.Especialidad_ID = ee.Especialidad_ID
            WHERE u.Estado_ID = 1
            GROUP BY e.Especialista_ID
            ORDER BY u.Apellidos
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# AGENDA  —  GET /api/agenda?especialista_id=&fecha=
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/agenda', methods=['GET'])
def get_agenda():
    """
    Devuelve los slots de agenda disponibles.
    Parámetros opcionales:  especialista_id, fecha
    """
    esp_id = request.args.get('especialista_id')
    fecha  = request.args.get('fecha')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        sql = """
            SELECT
                a.Agenda_ID,
                a.Especialista_ID,
                u.Nombres || ' ' || u.Apellidos  AS NombreEspecialista,
                esp.Nombre_Especialidad,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,
                ea.Nombre_Estado                 AS EstadoAgenda
            FROM agenda a
            JOIN especialistas e   ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios u       ON u.Usuario_ID      = e.Usuario_ID
            JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            JOIN estado_agenda ea ON ea.Estado_ID = a.Estado_ID
            WHERE a.Estado_ID = 1          -- solo 'Disponible'
        """
        params = []

        if esp_id:
            sql += " AND a.Especialista_ID = ?"
            params.append(esp_id)
        if fecha:
            sql += " AND a.Fecha = ?"
            params.append(fecha)

        sql += " ORDER BY a.Fecha, a.Hora_Inicio"
        cur.execute(sql, params)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS  —  GET /api/citas   |   POST /api/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas', methods=['GET'])
def get_citas():
    """
    Lista todas las citas con datos completos del paciente, especialista y agenda.
    Query param opcional:  paciente_id, especialista_id
    """
    paciente_id   = request.args.get('paciente_id')
    especialista_id = request.args.get('especialista_id')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        sql = """
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                -- Paciente
                p.Paciente_ID,
                up.Nombres || ' ' || up.Apellidos  AS NombrePaciente,
                up.NumeroDocumento,
                up.Telefono                        AS TelefonoPaciente,
                up.Correo                          AS CorreoPaciente,
                -- Agenda / Especialistas
                a.Agenda_ID,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,
                ea.Nombre_Estado                   AS EstadoAgenda,
                e.Especialista_ID,
                ue.Nombres || ' ' || ue.Apellidos  AS NombreEspecialista,
                esp.Nombre_Especialidad
            FROM cita c
            JOIN paciente p   ON p.Paciente_ID     = c.Paciente_ID
            JOIN usuarios up  ON up.Usuario_ID     = p.Usuario_ID
            JOIN agenda a     ON a.Agenda_ID       = c.Agenda_ID
            JOIN estado_agenda ea ON ea.Estado_ID = a.Estado_ID
            JOIN especialistas e   ON e.Especialista_ID  = a.Especialista_ID
            JOIN usuarios ue  ON ue.Usuario_ID     = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            WHERE 1=1
        """
        params = []
        if paciente_id:
            sql += " AND p.Paciente_ID = ?"
            params.append(paciente_id)
        if especialista_id:
            sql += " AND e.Especialista_ID = ?"
            params.append(especialista_id)

        sql += " ORDER BY a.Fecha DESC, a.Hora_Inicio DESC"
        cur.execute(sql, params)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/citas', methods=['POST'])
def crear_cita():
    """
    Crea una nueva cita.
    Body JSON: { Paciente_ID, Agenda_ID, Motivo_Consulta }

    Reglas de negocio:
      - El paciente no puede tener otra cita activa (estado Disponible/Ocupado).
      - El slot de agenda debe estar Disponible.
      - Al crear la cita, el slot pasa a 'Ocupado'.
    """
    datos = request.get_json(silent=True) or {}
    paciente_id    = datos.get('Paciente_ID')
    agenda_id      = datos.get('Agenda_ID')
    motivo         = (datos.get('Motivo_Consulta') or '').strip()

    if not all([paciente_id, agenda_id, motivo]):
        return _json_error('Paciente_ID, Agenda_ID y Motivo_Consulta son obligatorios.')

    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # ── 1. Verificar que el slot exista y esté disponible ────────────────
        cur.execute(
            "SELECT Estado_ID FROM agenda WHERE Agenda_ID = ?", (agenda_id,)
        )
        slot = cur.fetchone()
        if not slot:
            return _json_error('El slot de agenda no existe.', 404)
        if slot['Estado_ID'] != 1:
            return _json_error('Ese horario ya no está disponible.')

        # ── 2. Verificar que el paciente no tenga cita activa ────────────────
        cur.execute("""
            SELECT c.Cita_ID
            FROM cita c
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            WHERE c.Paciente_ID = ?
              AND a.Estado_ID IN (1, 2)   -- Disponible u Ocupado
        """, (paciente_id,))
        if cur.fetchone():
            return _json_error('El paciente ya tiene una cita activa pendiente.')

        # ── 3. Insertar la cita ───────────────────────────────────────────────
        cur.execute(
            "INSERT INTO cita (Paciente_ID, Agenda_ID, Motivo_Consulta) VALUES (?, ?, ?)",
            (paciente_id, agenda_id, motivo)
        )
        cita_id = cur.lastrowid

        # ── 4. Marcar el slot como 'Ocupado' (Estado_ID = 2) ───────────
        cur.execute(
            "UPDATE agenda SET Estado_ID = 2 WHERE Agenda_ID = ?", (agenda_id,)
        )

        con.commit()
        return _json_ok({"ok": True, "Cita_ID": cita_id, "status": "Cita registrada con éxito."}, 201)

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITA INDIVIDUAL  —  GET|PUT|DELETE /api/citas/<id>
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/citas/<int:cita_id>', methods=['GET'])
def get_cita(cita_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID, c.Motivo_Consulta,
                p.Paciente_ID,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                up.NumeroDocumento, up.Correo,
                a.Fecha, a.Hora_Inicio, a.Hora_Fin,
                ea.Nombre_Estado AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista
            FROM cita c
            JOIN paciente p   ON p.Paciente_ID = c.Paciente_ID
            JOIN usuarios up  ON up.Usuario_ID = p.Usuario_ID
            JOIN agenda a     ON a.Agenda_ID   = c.Agenda_ID
            JOIN estado_agenda ea ON ea.Estado_ID = a.Estado_ID
            JOIN especialistas e ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios ue ON ue.Usuario_ID = e.Usuario_ID
            WHERE c.Cita_ID = ?
        """, (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)
        return _json_ok(dict(row))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/citas/<int:cita_id>/cancelar', methods=['PUT'])
def cancelar_cita(cita_id):
    """
    Cancela una cita:
      - Libera el slot de agenda (Estado_ID = 3 'Cancelado').
      - Crea una multa en estado 'Pendiente' (EstadoMulta_ID = 1).
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()

        # Obtener el Agenda_ID de la cita
        cur.execute("SELECT Agenda_ID FROM cita WHERE Cita_ID = ?", (cita_id,))
        row = cur.fetchone()
        if not row:
            return _json_error('Cita no encontrada.', 404)

        agenda_id = row['Agenda_ID']

        # Marcar agenda como Cancelada (ID = 3)
        cur.execute(
            "UPDATE agenda SET Estado_ID = 3 WHERE Agenda_ID = ?", (agenda_id,)
        )

        # Crear multa pendiente (EstadoMulta_ID = 1)
        cur.execute(
            "INSERT INTO multa (Cita_ID, EstadoMulta_ID) VALUES (?, 1)", (cita_id,)
        )

        con.commit()
        return _json_ok({"ok": True, "status": "Cita cancelada y multa generada."})

    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR PACIENTE  —  GET /api/paciente/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/citas', methods=['GET'])
def get_citas_paciente(paciente_id):
    """
    Devuelve todas las citas de un paciente con estado de agenda y multa.
    Consumido por paciente.js.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,
                ea.Nombre_Estado              AS EstadoAgenda,
                ue.Nombres || ' ' || ue.Apellidos AS NombreEspecialista,
                esp.Nombre_Especialidad,
                COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta
            FROM cita c
            JOIN agenda a     ON a.Agenda_ID   = c.Agenda_ID
            JOIN estado_agenda ea ON ea.Estado_ID = a.Estado_ID
            JOIN especialistas e ON e.Especialista_ID = a.Especialista_ID
            JOIN usuarios ue ON ue.Usuario_ID = e.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = e.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m  ON m.Cita_ID  = c.Cita_ID
            LEFT JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            WHERE c.Paciente_ID = ?
            ORDER BY a.Fecha DESC, a.Hora_Inicio DESC
        """, (paciente_id,))
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# CITAS POR ESPECIALISTA  —  GET /api/especialista/<id>/citas
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/especialista/<int:especialista_id>/citas', methods=['GET'])
def get_citas_especialista(especialista_id):
    """
    Devuelve las citas asignadas a un especialista.
    Consumido por especialista.js.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                c.Cita_ID,
                c.Motivo_Consulta,
                a.Fecha,
                a.Hora_Inicio,
                a.Hora_Fin,
                ea.Nombre_Estado              AS EstadoAgenda,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                up.NumeroDocumento,
                up.Telefono                   AS TelefonoPaciente,
                esp.Nombre_Especialidad,
                COALESCE(em.Nombre_Estado, 'Sin multa') AS EstadoMulta
            FROM cita c
            JOIN agenda a    ON a.Agenda_ID   = c.Agenda_ID
            JOIN estado_agenda ea ON ea.Estado_ID = a.Estado_ID
            JOIN paciente p  ON p.Paciente_ID = c.Paciente_ID
            JOIN usuarios up ON up.Usuario_ID = p.Usuario_ID
            LEFT JOIN especialista_especialidad ee ON ee.Especialista_ID = a.Especialista_ID
            LEFT JOIN especialidad esp ON esp.Especialidad_ID = ee.Especialidad_ID
            LEFT JOIN multa m ON m.Cita_ID = c.Cita_ID
            LEFT JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            WHERE a.Especialista_ID = ?
            ORDER BY a.Fecha, a.Hora_Inicio
        """, (especialista_id,))
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# MULTAS  —  GET /api/multas   |   PUT /api/multas/<id>/pagar
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/multas', methods=['GET'])
def get_multas():
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT
                m.Multa_ID,
                m.Cita_ID,
                em.Nombre_Estado            AS EstadoMulta,
                up.Nombres || ' ' || up.Apellidos AS NombrePaciente,
                a.Fecha,
                a.Hora_Inicio
            FROM multa m
            JOIN estado_multa em ON em.EstadoMulta_ID = m.EstadoMulta_ID
            JOIN cita c   ON c.Cita_ID    = m.Cita_ID
            JOIN paciente p ON p.Paciente_ID = c.Paciente_ID
            JOIN usuarios up ON up.Usuario_ID = p.Usuario_ID
            JOIN agenda a ON a.Agenda_ID = c.Agenda_ID
            ORDER BY m.Multa_ID DESC
        """)
        return _json_ok(_rows_to_list(cur))
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


@citas_bp.route('/multas/<int:multa_id>/pagar', methods=['PUT'])
def pagar_multa(multa_id):
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE multa SET EstadoMulta_ID = 2 WHERE Multa_ID = ?", (multa_id,)
        )
        if cur.rowcount == 0:
            return _json_error('Multa no encontrada.', 404)
        con.commit()
        return _json_ok({"ok": True, "status": "Multa marcada como Pagada."})
    except Exception as exc:
        if con: con.rollback()
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR MULTA DE UN PACIENTE  —  GET /api/paciente/<id>/multa-activa
# ─────────────────────────────────────────────────────────────────────────────

@citas_bp.route('/paciente/<int:paciente_id>/multa-activa', methods=['GET'])
def multa_activa(paciente_id):
    """
    Devuelve si el paciente tiene alguna multa pendiente.
    agendar.html lo usa para mostrar la alerta de multa antes de confirmar.
    """
    con = None
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT m.Multa_ID
            FROM multa m
            JOIN cita c ON c.Cita_ID = m.Cita_ID
            WHERE c.Paciente_ID = ? AND m.EstadoMulta_ID = 1
            LIMIT 1
        """, (paciente_id,))
        row = cur.fetchone()
        return _json_ok({"tiene_multa": row is not None})
    except Exception as exc:
        return _json_error(str(exc), 500)
    finally:
        if con: con.close()