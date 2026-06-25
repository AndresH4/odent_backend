'use strict';

// ─── CONFIG ────────────────────────────────────────────────────────────────────
// PACIENTE_ID y CITA_ID se leen desde los atributos data-* del <body>
// inyectados por Jinja2 en historia_clinica.html:
//   <body data-paciente-id="{{ paciente_id | default(0) | int }}"
//         data-cita-id="{{ cita_id | default(0) | int }}">
//
// Fallback: sessionStorage (puente desde especialista.js → irAHistoriaClinica())

const _HC_PACIENTE_ID = (() => {
    const fromBody = parseInt(document.body.dataset.pacienteId || '0', 10);
    if (fromBody) return fromBody;
    return parseInt(sessionStorage.getItem('hc_paciente_id') || '0', 10);
})();

const _HC_CITA_ID = (() => {
    const fromBody = parseInt(document.body.dataset.citaId || '0', 10);
    if (fromBody) return fromBody;
    return parseInt(sessionStorage.getItem('hc_cita_id') || '0', 10);
})();

let mapaDental         = {};   // { "18": "rojo", "21": "azul", ... }
let dienteSeleccionado = null; // elemento DOM del diente activo
let hallazgosData      = [];   // [{ procedimiento, detalle }]

// ─── TOAST ─────────────────────────────────────────────────────────────────────
function hcToast(msg, tipo = 'info') {
    const c = document.getElementById('hc-toast-container');
    if (!c) return;
    const el      = document.createElement('div');
    el.className  = `hc-toast ${tipo}`;
    const iconos  = {
        success: 'fa-check-circle',
        error:   'fa-times-circle',
        info:    'fa-info-circle'
    };
    el.innerHTML  = `<i class="fas ${iconos[tipo] || iconos.info}"></i><span>${msg}</span>`;
    c.appendChild(el);
    setTimeout(() => {
        el.style.opacity    = '0';
        el.style.transition = 'opacity .4s';
        setTimeout(() => el.remove(), 400);
    }, 3500);
}

// ─── HELPERS DOM ───────────────────────────────────────────────────────────────
function _setEl(id, valor) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = (el.className || '').replace(/skeleton[\w\s-]*/g, '').trim();
    el.style     = '';
    el.textContent = valor || '—';
}

function _setInput(id, valor) {
    const el = document.getElementById(id);
    if (el) el.value = valor || '';
}

// ─── FETCH: DATOS DEL PACIENTE ─────────────────────────────────────────────────
// Ruta de datos: GET /api/historial/paciente/<id>/info  → jsonify exclusivo
// Esta función solo hace fetch + pinta DOM. NUNCA navega.
async function cargarDatosPaciente() {
    if (!_HC_PACIENTE_ID) {
        hcToast('ID de paciente no disponible.', 'error');
        return;
    }
    try {
        const res  = await fetch(`/api/historial/paciente/${_HC_PACIENTE_ID}/info`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.ok || !data.data) {
            hcToast('No se pudieron cargar los datos del paciente.', 'error');
            return;
        }

        const p = data.data;
        _setEl('p-nombre',  p.NombreCompleto);
        _setEl('p-doc',     `${p.TipoDocumento || ''} ${p.NumeroDocumento || ''}`.trim());
        _setEl('p-edad',    p.Edad ? `${p.Edad} años` : '—');
        _setEl('p-eps',     p.NombreEPS
            ? `${p.NombreEPS}${p.Regimen ? ' (' + p.Regimen + ')' : ''}`
            : '—');
        _setEl('p-tel',     p.Telefono);
        _setEl('p-correo',  p.Correo);

    } catch (err) {
        console.error('[HC] cargarDatosPaciente:', err);
        hcToast('Error al cargar datos del paciente.', 'error');
    }
}

// ─── FETCH: EVOLUCIONES ────────────────────────────────────────────────────────
// Ruta de datos: GET /api/historial/paciente/<id>/evoluciones  → jsonify exclusivo
// Esta función solo hace fetch + pinta DOM. NUNCA navega.
async function cargarEvoluciones() {
    if (!_HC_PACIENTE_ID) return;

    const cont = document.getElementById('evoluciones-container');
    if (!cont) return;

    try {
        let url = `/api/historial/paciente/${_HC_PACIENTE_ID}/evoluciones`;
        if (_HC_CITA_ID) url += `?cita_id=${_HC_CITA_ID}`;

        const res  = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.ok || !data.data || data.data.length === 0) {
            cont.innerHTML = `
                <div style="text-align:center;padding:32px 0;">
                    <i class="fas fa-folder-open"
                       style="font-size:36px;color:#cbd5e1;margin-bottom:12px;display:block;"></i>
                    <p style="color:#94a3b8;font-weight:700;font-size:13px;
                               text-transform:uppercase;letter-spacing:.1em;">
                        Sin evoluciones previas registradas
                    </p>
                </div>`;
            return;
        }

        // Pre-llenar formulario con la cita activa (o la más reciente)
        const citaActual = _HC_CITA_ID
            ? data.data.find(d => d.Cita_ID === _HC_CITA_ID)
            : data.data[0];

        if (citaActual) {
            if (citaActual.Motivo_Consulta)
                _setInput('hc-motivo',    citaActual.Motivo_Consulta);
            if (citaActual.Diagnostico && citaActual.Diagnostico !== 'Sin diagnóstico')
                _setInput('hc-diag',      citaActual.Diagnostico);
            if (citaActual.Evolucion)
                _setInput('hc-evolucion', citaActual.Evolucion);
            if (citaActual.Tratamiento)
                _setInput('hc-plan',      citaActual.Tratamiento);
        }

        // Mapa de clases para badge de estado
        const estadoClase = {
            'Cumplida':  'badge-cumplida',
            'Cancelado': 'badge-cancelada',
            'Cancelada': 'badge-cancelada',
        };

        // Renderizar lista de evoluciones
        cont.innerHTML = data.data.map(ev => `
            <div class="evolucion-item">
                <div class="evolucion-meta">
                    <span class="evolucion-fecha">
                        <i class="fas fa-calendar-alt" style="margin-right:4px;"></i>
                        ${ev.Fecha || '—'} · ${ev.Hora_Inicio || ''}
                    </span>
                    <span class="evolucion-esp">${ev.NombreEspecialista || '—'}</span>
                    <span class="badge ${estadoClase[ev.EstadoAgenda] || 'badge-ocupado'}">
                        ${ev.EstadoAgenda || '—'}
                    </span>
                    ${ev.Nombre_Especialidad
                        ? `<span class="evolucion-especialidad">${ev.Nombre_Especialidad}</span>`
                        : ''}
                </div>
                <div class="evolucion-body">
                    ${ev.Motivo_Consulta
                        ? `<p><strong>Motivo:</strong> ${ev.Motivo_Consulta}</p>`
                        : ''}
                    ${ev.Diagnostico && ev.Diagnostico !== 'Sin diagnóstico'
                        ? `<p><strong>Diagnóstico:</strong> ${ev.Diagnostico}</p>`
                        : ''}
                    ${ev.Evolucion
                        ? `<p><strong>Evolución:</strong> ${ev.Evolucion}</p>`
                        : ''}
                    ${ev.Tratamiento
                        ? `<p><strong>Plan:</strong> ${ev.Tratamiento}</p>`
                        : ''}
                    ${!ev.Diagnostico && !ev.Evolucion && !ev.Tratamiento
                        ? `<p class="evolucion-vacia">Sin historial clínico registrado aún.</p>`
                        : ''}
                </div>
            </div>`
        ).join('');

    } catch (err) {
        console.error('[HC] cargarEvoluciones:', err);
        if (cont) {
            cont.innerHTML = `
                <p style="color:#ef4444;font-size:13px;font-weight:600;">
                    Error al cargar el historial.
                </p>`;
        }
    }
}

// ─── ODONTOGRAMA ───────────────────────────────────────────────────────────────
function initOdontograma() {
    const sup = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28];
    const inf = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38];

    const contenedorSup = document.getElementById('odo-sup');
    const contenedorInf = document.getElementById('odo-inf');
    if (!contenedorSup || !contenedorInf) return;

    const crearDiente = (num, contenedor) => {
        const div       = document.createElement('div');
        div.className   = 'diente';
        div.id          = `d-${num}`;
        div.textContent = num;
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            abrirSelector(div, num, e);
        });
        contenedor.appendChild(div);
    };

    sup.forEach(n => crearDiente(n, contenedorSup));
    inf.forEach(n => crearDiente(n, contenedorInf));
}

function abrirSelector(el, num, event) {
    event.stopPropagation();
    dienteSeleccionado = el;

    const numEl = document.getElementById('num-diente-sel');
    if (numEl) numEl.textContent = num;

    const sel  = document.getElementById('selector-estado');
    const wrap = document.getElementById('odontograma-wrap');
    if (!sel || !wrap) return;

    const wRect = wrap.getBoundingClientRect();
    const eRect = el.getBoundingClientRect();

    sel.style.display = 'block';
    sel.style.top  = (eRect.bottom - wRect.top + wrap.scrollTop + 6) + 'px';
    sel.style.left = Math.min(
        eRect.left - wRect.left - 20,
        wrap.clientWidth - 180
    ) + 'px';
}

function asignarEstado(clase) {
    if (!dienteSeleccionado) return;
    const num = dienteSeleccionado.textContent.trim();
    dienteSeleccionado.classList.remove('rojo', 'azul', 'verde', 'amarillo');
    if (clase) {
        dienteSeleccionado.classList.add(clase);
        mapaDental[num] = clase;
    } else {
        delete mapaDental[num];
    }
    const sel = document.getElementById('selector-estado');
    if (sel) sel.style.display = 'none';
    dienteSeleccionado = null;
}

function cerrarSelector() {
    const sel = document.getElementById('selector-estado');
    if (sel) sel.style.display = 'none';
}

// ─── HALLAZGOS ─────────────────────────────────────────────────────────────────
const PROCEDIMIENTOS = [
    'Caries Detectada',
    'Ausente / Perdido',
    'Cirugía Pendiente',
    'Endodoncia',
    'Limpieza Profunda',
    'Restauración',
    'Extracción',
    'Blanqueamiento',
    'Brackets',
    'Control Periódico',
    'Otro...'
];

function agregarHallazgo() {
    const cont = document.getElementById('lista-hallazgos');
    if (!cont) return;

    const idx = hallazgosData.length;
    const div = document.createElement('div');
    div.className   = 'hallazgo-row';
    div.dataset.idx = idx;

    div.innerHTML = `
        <select class="hc-select h-sel"
                onchange="syncHallazgo(${idx}, 'proc', this.value)">
            <option value="">-- Procedimiento --</option>
            ${PROCEDIMIENTOS.map(p => `<option value="${p}">${p}</option>`).join('')}
        </select>
        <input type="text"
               class="hc-input h-inp"
               placeholder="Detalles específicos..."
               oninput="syncHallazgo(${idx}, 'detalle', this.value)">
        <button class="hallazgo-del"
                onclick="eliminarHallazgo(this)"
                type="button"
                title="Eliminar hallazgo">
            <i class="fas fa-times"></i>
        </button>`;

    cont.appendChild(div);
    hallazgosData.push({ procedimiento: '', detalle: '' });
}

function syncHallazgo(idx, campo, val) {
    if (!hallazgosData[idx]) hallazgosData[idx] = {};
    hallazgosData[idx][campo === 'proc' ? 'procedimiento' : 'detalle'] = val;
}

function eliminarHallazgo(btn) {
    const row = btn.closest('.hallazgo-row');
    if (!row) return;
    const idx = parseInt(row.dataset.idx, 10);
    hallazgosData.splice(idx, 1);
    row.remove();

    // Re-indexar filas restantes
    const cont = document.getElementById('lista-hallazgos');
    if (!cont) return;
    Array.from(cont.children).forEach((r, i) => {
        r.dataset.idx = i;
        const sel = r.querySelector('.h-sel');
        const inp = r.querySelector('.h-inp');
        if (sel) sel.onchange = (e) => syncHallazgo(i, 'proc',    e.target.value);
        if (inp) inp.oninput  = (e) => syncHallazgo(i, 'detalle', e.target.value);
    });
}

// ─── GUARDAR / FINALIZAR ───────────────────────────────────────────────────────
// Ruta de datos: POST /api/historial/guardar  o  POST /api/historial/finalizar
// Esta función solo hace fetch + muestra resultado. Solo navega al finalizar.
async function guardarHistoria(finalizar = false) {
    if (!_HC_CITA_ID) {
        hcToast('No se puede guardar: no hay cita activa vinculada.', 'error');
        return;
    }

    const btnG = document.getElementById('btn-guardar');
    const btnF = document.getElementById('btn-finalizar');

    if (btnG) {
        btnG.disabled  = true;
        btnG.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    }
    if (btnF) btnF.disabled = true;

    const motivoEl    = document.getElementById('hc-motivo');
    const diagEl      = document.getElementById('hc-diag');
    const evolucionEl = document.getElementById('hc-evolucion');
    const planEl      = document.getElementById('hc-plan');

    const payload = {
        Cita_ID:        _HC_CITA_ID,
        MotivoConsulta: motivoEl    ? motivoEl.value.trim()    : '',
        Diagnostico:    diagEl      ? diagEl.value.trim()      : '',
        Evolucion:      evolucionEl ? evolucionEl.value.trim() : '',
        Tratamiento:    planEl      ? planEl.value.trim()      : '',
        MapaDental:     JSON.stringify(mapaDental),
        Hallazgos:      JSON.stringify(
            hallazgosData.filter(h => h.procedimiento || h.detalle)
        ),
    };

    const endpoint = finalizar
        ? '/api/historial/finalizar'
        : '/api/historial/guardar';

    try {
        const res  = await fetch(endpoint, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || !data.ok) {
            hcToast(data.error || 'Error al guardar la historia clínica.', 'error');
            return;
        }

        if (finalizar) {
            // Notificar encuesta/correo (best-effort, no bloqueante)
            fetch(`/api/citas/${_HC_CITA_ID}/finalizar-consulta`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
            }).catch(() => {});

            hcToast('Consulta finalizada y registrada exitosamente.', 'success');
            setTimeout(() => volverAlPanel(), 1800);
        } else {
            hcToast('Historia clínica guardada correctamente.', 'success');
            await cargarEvoluciones();
        }

    } catch (err) {
        console.error('[HC] guardarHistoria:', err);
        hcToast('Error de conexión al guardar.', 'error');
    } finally {
        if (btnG) {
            btnG.disabled  = false;
            btnG.innerHTML = '<i class="fas fa-save"></i> Guardar';
        }
        if (btnF) btnF.disabled = false;
    }
}

// ─── NAVEGACIÓN ────────────────────────────────────────────────────────────────
function volverAlPanel() {
    if (window.opener && !window.opener.closed) {
        window.close();
    } else {
        window.location.href = '/especialista';
    }
}

// ─── INIT ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    // Persistir IDs en sessionStorage por si hay recarga de página
    if (_HC_PACIENTE_ID) sessionStorage.setItem('hc_paciente_id', String(_HC_PACIENTE_ID));
    if (_HC_CITA_ID)     sessionStorage.setItem('hc_cita_id',     String(_HC_CITA_ID));

    initOdontograma();
    agregarHallazgo();       // fila inicial vacía en hallazgos

    // Ambas funciones hacen fetch a rutas de datos (API) y pintan el DOM.
    // NUNCA navegan. La navegación solo ocurre en guardarHistoria(true).
    cargarDatosPaciente();   // → GET /api/historial/paciente/<id>/info
    cargarEvoluciones();     // → GET /api/historial/paciente/<id>/evoluciones

    // Cerrar selector de diente al hacer clic fuera del odontograma
    document.addEventListener('click', cerrarSelector);
});