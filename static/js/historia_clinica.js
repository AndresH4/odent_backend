'use strict';

// ─── CONFIG ────────────────────────────────────────────────────────────────────
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

console.log('[HC][INIT] data-paciente-id=', document.body.dataset.pacienteId,
            'data-cita-id=', document.body.dataset.citaId,
            '=> _HC_PACIENTE_ID=', _HC_PACIENTE_ID, '_HC_CITA_ID=', _HC_CITA_ID);

let mapaDental           = {};
let dienteSeleccionado   = null;
let hallazgosData        = [];
let _diagSelectedID      = null;
let _diagSelectedNombre  = '';
let _cie10ActiveIdx      = -1;
let _diagBDLoaded        = false;
let _diagBDCache         = [];

// ─── CATÁLOGO CIE-10 DENTAL (estático de respaldo) ────────────────────────────
const CIE10_DENTAL = [
    { id: null, codigo: 'K00.0', desc: 'Anodoncia' },
    { id: null, codigo: 'K00.1', desc: 'Dientes supernumerarios' },
    { id: null, codigo: 'K00.2', desc: 'Anomalías del tamaño y forma de los dientes' },
    { id: null, codigo: 'K00.3', desc: 'Dientes moteados (fluorosis dental)' },
    { id: null, codigo: 'K00.4', desc: 'Perturbaciones en la formación de los dientes' },
    { id: null, codigo: 'K00.5', desc: 'Anomalías hereditarias de la estructura dentaria' },
    { id: null, codigo: 'K00.6', desc: 'Perturbaciones en la erupción de los dientes' },
    { id: null, codigo: 'K00.8', desc: 'Otros trastornos del desarrollo de los dientes' },
    { id: null, codigo: 'K01.0', desc: 'Dientes incluidos' },
    { id: null, codigo: 'K01.1', desc: 'Dientes impactados' },
    { id: null, codigo: 'K02.0', desc: 'Caries del esmalte (mancha blanca)' },
    { id: null, codigo: 'K02.1', desc: 'Caries de la dentina' },
    { id: null, codigo: 'K02.2', desc: 'Caries del cemento' },
    { id: null, codigo: 'K02.3', desc: 'Caries dental detenida' },
    { id: null, codigo: 'K02.4', desc: 'Odontoclasia' },
    { id: null, codigo: 'K02.5', desc: 'Caries con exposición pulpar' },
    { id: null, codigo: 'K02.8', desc: 'Otras caries dentales' },
    { id: null, codigo: 'K02.9', desc: 'Caries dental no especificada' },
    { id: null, codigo: 'K03.0', desc: 'Atrición excesiva de los dientes' },
    { id: null, codigo: 'K03.1', desc: 'Abrasión de los dientes' },
    { id: null, codigo: 'K03.2', desc: 'Erosión de los dientes' },
    { id: null, codigo: 'K03.3', desc: 'Reabsorción patológica de los dientes' },
    { id: null, codigo: 'K03.4', desc: 'Hipercementosis' },
    { id: null, codigo: 'K03.5', desc: 'Anquilosis dental' },
    { id: null, codigo: 'K03.6', desc: 'Depósitos en los dientes (cálculo, sarro)' },
    { id: null, codigo: 'K03.7', desc: 'Cambios posteruptivos del color del esmalte' },
    { id: null, codigo: 'K04.0', desc: 'Pulpitis' },
    { id: null, codigo: 'K04.1', desc: 'Necrosis de la pulpa' },
    { id: null, codigo: 'K04.2', desc: 'Degeneración de la pulpa' },
    { id: null, codigo: 'K04.3', desc: 'Formación anormal de tejido duro en la pulpa' },
    { id: null, codigo: 'K04.4', desc: 'Periodontitis apical aguda de origen pulpar' },
    { id: null, codigo: 'K04.5', desc: 'Periodontitis apical crónica' },
    { id: null, codigo: 'K04.6', desc: 'Absceso periapical con fístula' },
    { id: null, codigo: 'K04.7', desc: 'Absceso periapical sin fístula' },
    { id: null, codigo: 'K04.8', desc: 'Quiste radicular' },
    { id: null, codigo: 'K04.9', desc: 'Otras enfermedades de la pulpa y tejidos periapicales' },
    { id: null, codigo: 'K05.0', desc: 'Gingivitis aguda' },
    { id: null, codigo: 'K05.1', desc: 'Gingivitis crónica' },
    { id: null, codigo: 'K05.2', desc: 'Periodontitis aguda' },
    { id: null, codigo: 'K05.3', desc: 'Periodontitis crónica' },
    { id: null, codigo: 'K05.4', desc: 'Periodontosis (periodontitis juvenil)' },
    { id: null, codigo: 'K05.5', desc: 'Otras enfermedades periodontales' },
    { id: null, codigo: 'K06.0', desc: 'Recesión gingival' },
    { id: null, codigo: 'K06.1', desc: 'Agrandamiento gingival (hipertrofia)' },
    { id: null, codigo: 'K06.2', desc: 'Lesiones gingivales y periodontales por trauma' },
    { id: null, codigo: 'K07.0', desc: 'Anomalías del tamaño de los maxilares' },
    { id: null, codigo: 'K07.1', desc: 'Anomalías de la relación entre los maxilares' },
    { id: null, codigo: 'K07.2', desc: 'Anomalías de la relación de los arcos dentarios' },
    { id: null, codigo: 'K07.3', desc: 'Anomalías de la posición del diente' },
    { id: null, codigo: 'K07.4', desc: 'Maloclusión no especificada' },
    { id: null, codigo: 'K07.5', desc: 'Anomalías dentofaciales funcionales' },
    { id: null, codigo: 'K07.6', desc: 'Trastornos de la articulación temporomandibular (ATM)' },
    { id: null, codigo: 'K08.0', desc: 'Exfoliación de dientes por causas sistémicas' },
    { id: null, codigo: 'K08.1', desc: 'Pérdida de dientes por accidente o extracción' },
    { id: null, codigo: 'K08.2', desc: 'Atrofia del reborde alveolar desdentado' },
    { id: null, codigo: 'K08.3', desc: 'Raíz dental retenida' },
    { id: null, codigo: 'K08.8', desc: 'Otros trastornos de los dientes y sus estructuras' },
    { id: null, codigo: 'K09.0', desc: 'Quistes odontogénicos del desarrollo' },
    { id: null, codigo: 'K09.1', desc: 'Quistes de las fisuras (no odontogénicos)' },
    { id: null, codigo: 'K09.2', desc: 'Otros quistes de los maxilares' },
    { id: null, codigo: 'K10.0', desc: 'Trastornos del desarrollo de los maxilares' },
    { id: null, codigo: 'K10.1', desc: 'Granuloma central de células gigantes' },
    { id: null, codigo: 'K10.2', desc: 'Enfermedades inflamatorias de los maxilares' },
    { id: null, codigo: 'K10.3', desc: 'Alveolitis del maxilar (alveolo seco)' },
    { id: null, codigo: 'K11.0', desc: 'Atrofia de glándula salival' },
    { id: null, codigo: 'K11.2', desc: 'Sialoadenitis' },
    { id: null, codigo: 'K11.3', desc: 'Absceso de glándula salival' },
    { id: null, codigo: 'K11.5', desc: 'Sialolitiasis (cálculo salival)' },
    { id: null, codigo: 'K11.6', desc: 'Mucocele de glándula salival' },
    { id: null, codigo: 'K11.7', desc: 'Trastornos de la secreción salival (xerostomía)' },
    { id: null, codigo: 'K12.0', desc: 'Estomatitis aftosa recurrente (aftas)' },
    { id: null, codigo: 'K12.1', desc: 'Otras formas de estomatitis' },
    { id: null, codigo: 'K12.2', desc: 'Celulitis y absceso de boca' },
    { id: null, codigo: 'K13.0', desc: 'Enfermedades de los labios (queilitis)' },
    { id: null, codigo: 'K13.2', desc: 'Leucoplasia y otras alteraciones del epitelio bucal' },
    { id: null, codigo: 'K13.4', desc: 'Granuloma y lesiones similares de la mucosa bucal' },
    { id: null, codigo: 'K13.6', desc: 'Hiperplasia irritativa de la mucosa bucal' },
    { id: null, codigo: 'K14.0', desc: 'Glositis' },
    { id: null, codigo: 'K14.1', desc: 'Lengua geográfica (glositis migratoria benigna)' },
    { id: null, codigo: 'K14.3', desc: 'Hipertrofia de papilas linguales (lengua vellosa)' },
    { id: null, codigo: 'K14.5', desc: 'Lengua fisurada (plegada)' },
    { id: null, codigo: 'K14.6', desc: 'Glosodinia (ardor de lengua)' },
    { id: null, codigo: 'S02.5', desc: 'Fractura del diente' },
    { id: null, codigo: 'S02.6', desc: 'Fractura del maxilar inferior' },
    { id: null, codigo: 'S03.2', desc: 'Luxación del diente' },
    { id: null, codigo: 'Z29.0', desc: 'Profilaxis dental (limpieza / control periódico)' },
    { id: null, codigo: 'Z46.3', desc: 'Adaptación y ajuste de aparato dental (ortodoncia)' },
];

// ─── TOAST ─────────────────────────────────────────────────────────────────────
function hcToast(msg, tipo = 'info') {
    const c = document.getElementById('hc-toast-container');
    if (!c) return;
    const el      = document.createElement('div');
    el.className  = `hc-toast ${tipo}`;
    const iconos  = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle' };
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
    el.removeAttribute('style');
    el.textContent = valor || '—';
}

function _setInput(id, valor) {
    const el = document.getElementById(id);
    if (el) el.value = valor || '';
}

function _actualizarLogoInicial(nombreCompleto) {
    const logoEl = document.getElementById('hc-logo-inicial');
    if (!logoEl) return;
    const inicial = (nombreCompleto || '').trim().charAt(0).toUpperCase();
    logoEl.textContent = inicial || '?';
}

// ─── PESTAÑAS ──────────────────────────────────────────────────────────────────
function cambiarTab(tabId) {
    document.querySelectorAll('.hc-tab-panel').forEach(p => p.classList.add('hc-tab-hidden'));
    document.querySelectorAll('.hc-tab-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
    });
    const panel = document.getElementById(`tab-${tabId}`);
    if (panel) panel.classList.remove('hc-tab-hidden');
    const btn = document.querySelector(`.hc-tab-btn[data-tab="${tabId}"]`);
    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }
    if (tabId === 'historial') {
        cargarEvoluciones();
    }
}

// ─── DIAGNÓSTICO: CARGA DESDE BD + FUSIÓN CON CIE-10 ──────────────────────────
async function _cargarDiagnosticosBD() {
    if (_diagBDLoaded) return;
    try {
        const res  = await fetch('/api/diagnosticos');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.ok && Array.isArray(data.data)) {
            _diagBDCache = data.data.map(d => ({
                id:     d.id,
                codigo: '',
                desc:   d.nombre,
            }));
        }
    } catch (err) {
        console.warn('[HC] No se pudieron cargar diagnósticos desde BD:', err);
        _diagBDCache = [];
    }
    _diagBDLoaded = true;
}

function _fusionarCatalogoDiag() {
    const fusionado = [..._diagBDCache];
    const nombresEnBD = new Set(_diagBDCache.map(d => d.desc.toLowerCase()));
    CIE10_DENTAL.forEach(item => {
        const etiqueta = item.codigo ? `${item.codigo} — ${item.desc}` : item.desc;
        if (!nombresEnBD.has(item.desc.toLowerCase())) {
            fusionado.push({ id: null, codigo: item.codigo, desc: item.desc, etiqueta });
        }
    });
    return fusionado;
}

// ─── CIE-10 / DIAGNÓSTICO: AUTOCOMPLETE ───────────────────────────────────────
async function buscarCIE10(query) {
    const dropdown = document.getElementById('cie10-dropdown');
    if (!dropdown) return;
    _cie10ActiveIdx = -1;

    const q = query.trim().toLowerCase();
    if (q.length < 1) {
        dropdown.classList.remove('open');
        _diagSelectedID     = null;
        _diagSelectedNombre = '';
        return;
    }

    await _cargarDiagnosticosBD();
    const catalogo = _fusionarCatalogoDiag();

    const resultados = catalogo.filter(item => {
        const haystack = `${item.codigo} ${item.desc}`.toLowerCase();
        return haystack.includes(q);
    }).slice(0, 15);

    if (resultados.length === 0) {
        dropdown.innerHTML = `<div class="cie10-empty"><i class="fas fa-search" style="margin-right:6px;opacity:.5;"></i>Sin coincidencias para "${query}"</div>`;
    } else {
        dropdown.innerHTML = resultados.map((item, i) => {
            const etiqueta = item.codigo ? `${item.codigo} — ${item.desc}` : item.desc;
            const idAttr   = item.id !== null ? item.id : 'null';
            return `
            <div class="cie10-option" data-idx="${i}"
                 onmousedown="seleccionarCIE10(${idAttr}, '${item.codigo}', '${item.desc.replace(/'/g, "\\'")}')">
                ${item.codigo ? `<span class="cie10-code">${item.codigo}</span>` : ''}
                <span class="cie10-desc">${item.desc}</span>
            </div>`;
        }).join('');
    }
    dropdown.classList.add('open');
}

function seleccionarCIE10(id, codigo, desc) {
    const input = document.getElementById('hc-diag');
    const etiqueta = codigo ? `${codigo} — ${desc}` : desc;
    if (input) {
        input.value = etiqueta;
        input.classList.remove('hc-field-error');
    }
    _diagSelectedID     = (id !== null && id !== undefined && String(id) !== 'null') ? parseInt(id, 10) : null;
    _diagSelectedNombre = etiqueta;
    const dropdown = document.getElementById('cie10-dropdown');
    if (dropdown) dropdown.classList.remove('open');
}

function ocultarDropdownCIE10() {
    setTimeout(() => {
        const dropdown = document.getElementById('cie10-dropdown');
        if (dropdown) dropdown.classList.remove('open');
    }, 200);
}

function _cie10KeyNav(e) {
    const dropdown = document.getElementById('cie10-dropdown');
    if (!dropdown || !dropdown.classList.contains('open')) return;
    const opciones = dropdown.querySelectorAll('.cie10-option');
    if (!opciones.length) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        _cie10ActiveIdx = Math.min(_cie10ActiveIdx + 1, opciones.length - 1);
        _cie10Highlight(opciones);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        _cie10ActiveIdx = Math.max(_cie10ActiveIdx - 1, 0);
        _cie10Highlight(opciones);
    } else if (e.key === 'Enter' && _cie10ActiveIdx >= 0) {
        e.preventDefault();
        opciones[_cie10ActiveIdx].dispatchEvent(new MouseEvent('mousedown'));
    } else if (e.key === 'Escape') {
        dropdown.classList.remove('open');
    }
}

function _cie10Highlight(opciones) {
    opciones.forEach((o, i) => o.classList.toggle('highlighted', i === _cie10ActiveIdx));
    if (_cie10ActiveIdx >= 0) opciones[_cie10ActiveIdx].scrollIntoView({ block: 'nearest' });
}

// ─── VALIDACIÓN CAMPOS OBLIGATORIOS ───────────────────────────────────────────
function _validarCamposObligatorios() {
    const diagEl      = document.getElementById('hc-diag');
    const evolucionEl = document.getElementById('hc-evolucion');
    const planEl      = document.getElementById('hc-plan');

    const diagVal   = diagEl      ? diagEl.value.trim()      : '';
    const evoVal    = evolucionEl ? evolucionEl.value.trim() : '';
    const planVal   = planEl      ? planEl.value.trim()      : '';

    const errores = [];

    [diagEl, evolucionEl, planEl].forEach(el => {
        if (el) el.classList.remove('hc-field-error');
    });

    const errContainer = document.getElementById('hc-validation-errors');
    if (errContainer) errContainer.style.display = 'none';

    if (!evoVal) {
        errores.push('Evolución / Procedimiento realizado');
        if (evolucionEl) evolucionEl.classList.add('hc-field-error');
    }
    if (!diagVal) {
        errores.push('Diagnóstico (CIE-10)');
        if (diagEl) diagEl.classList.add('hc-field-error');
    }
    if (!planVal) {
        errores.push('Plan a seguir / Tratamiento');
        if (planEl) planEl.classList.add('hc-field-error');
    }

    if (errores.length > 0) {
        if (errContainer) {
            errContainer.innerHTML = `
                <div class="hc-validation-banner">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div>
                        <p class="hc-val-title">Campos obligatorios incompletos</p>
                        <ul class="hc-val-list">
                            ${errores.map(e => `<li>${e}</li>`).join('')}
                        </ul>
                    </div>
                </div>`;
            errContainer.style.display = 'block';
            errContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return false;
    }
    return true;
}

// ─── FETCH: DATOS DEL PACIENTE ─────────────────────────────────────────────────
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

        _actualizarLogoInicial(p.NombreCompleto);
        _renderAlertas(p);

    } catch (err) {
        console.error('[HC] cargarDatosPaciente:', err);
        hcToast('Error al cargar datos del paciente.', 'error');
    }
}

function _renderAlertas(p) {
    const alergias    = (p.Alergias    || '').trim();
    const condiciones = (p.Condiciones || '').trim();

    const wrapAlertas   = document.getElementById('hc-critical-alerts');
    const wrapNoAlertas = document.getElementById('hc-no-alerts');
    const alergWrap     = document.getElementById('alert-alergias-wrap');
    const alergVal      = document.getElementById('alert-alergias-val');
    const condWrap      = document.getElementById('alert-condiciones-wrap');
    const condVal       = document.getElementById('alert-condiciones-val');

    if (alergias || condiciones) {
        if (wrapAlertas)   wrapAlertas.style.display = '';
        if (wrapNoAlertas) wrapNoAlertas.style.display = 'none';
        if (alergias && alergVal && alergWrap) {
            alergVal.textContent    = alergias;
            alergWrap.style.display = '';
        } else if (alergWrap) {
            alergWrap.style.display = 'none';
        }
        if (condiciones && condVal && condWrap) {
            condVal.textContent    = condiciones;
            condWrap.style.display = '';
        }
    } else {
        if (wrapAlertas)   wrapAlertas.style.display = 'none';
        if (wrapNoAlertas) wrapNoAlertas.style.display = '';
    }
}

// ─── FETCH: EVOLUCIONES ────────────────────────────────────────────────────────
async function cargarEvoluciones() {
    if (!_HC_PACIENTE_ID) return;

    const cont = document.getElementById('evoluciones-container');
    if (!cont) return;

    cont.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
            <div class="skeleton skeleton-line" style="height:56px;border-radius:12px;"></div>
            <div class="skeleton skeleton-line" style="height:56px;border-radius:12px;"></div>
            <div class="skeleton skeleton-line w-60" style="height:56px;border-radius:12px;"></div>
        </div>`;

    try {
        const url = `/api/historial/paciente/${_HC_PACIENTE_ID}/evoluciones`;
        const res  = await fetch(url, { cache: 'no-store' });
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

        const citaActual = _HC_CITA_ID
            ? data.data.find(d => d.Cita_ID === _HC_CITA_ID)
            : null;

        if (citaActual) {
            if (citaActual.Motivo_Consulta)
                _setInput('hc-motivo',    citaActual.Motivo_Consulta);
            if (citaActual.Diagnostico && citaActual.Diagnostico.trim())
                _setInput('hc-diag',      citaActual.Diagnostico);
            if (citaActual.Evolucion)
                _setInput('hc-evolucion', citaActual.Evolucion);
            if (citaActual.Tratamiento)
                _setInput('hc-plan',      citaActual.Tratamiento);
        }

        const badge = document.getElementById('hist-count-badge');
        if (badge) {
            badge.textContent   = data.data.length;
            badge.style.display = 'inline-flex';
        }

        const estadoClase = {
            'Cumplida':  'badge-cumplida',
            'Cancelado': 'badge-cancelada',
            'Cancelada': 'badge-cancelada',
        };

        cont.innerHTML = data.data.map((ev, idx) => `
            <div class="evolucion-item${idx === 0 ? '' : ' collapsed'}" id="ev-item-${idx}">
                <div class="evolucion-header" onclick="toggleEvolucion(${idx})">
                    <div class="evolucion-meta">
                        <span class="evolucion-fecha">
                            <i class="fas fa-calendar-alt" style="margin-right:4px;"></i>
                            ${ev.Fecha || '—'}${ev.Hora_Inicio ? ' · ' + ev.Hora_Inicio : ''}
                        </span>
                        <span class="evolucion-esp">${ev.NombreEspecialista || '—'}</span>
                        <span class="badge ${estadoClase[ev.EstadoAgenda] || 'badge-ocupado'}">
                            ${ev.EstadoAgenda || '—'}
                        </span>
                        ${ev.Nombre_Especialidad
                            ? `<span class="evolucion-especialidad">${ev.Nombre_Especialidad}</span>`
                            : ''}
                        ${ev.Motivo_Consulta
                            ? `<span class="evolucion-motivo-chip">${ev.Motivo_Consulta}</span>`
                            : ''}
                    </div>
                    <i class="fas fa-chevron-down evolucion-toggle-icon"></i>
                </div>
                <div class="evolucion-body">
                    ${ev.Motivo_Consulta
                        ? `<div class="evolucion-campo"><span class="evolucion-campo-label">Motivo:</span><span class="evolucion-campo-val">${ev.Motivo_Consulta}</span></div>`
                        : ''}
                    ${ev.Diagnostico && ev.Diagnostico.trim()
                        ? `<div class="evolucion-campo"><span class="evolucion-campo-label">Diagnóstico:</span><span class="evolucion-campo-val evolucion-diag">${ev.Diagnostico}</span></div>`
                        : ''}
                    ${ev.Evolucion && ev.Evolucion.trim()
                        ? `<div class="evolucion-campo"><span class="evolucion-campo-label">Evolución:</span><span class="evolucion-campo-val">${ev.Evolucion}</span></div>`
                        : ''}
                    ${ev.Tratamiento && ev.Tratamiento.trim()
                        ? `<div class="evolucion-campo"><span class="evolucion-campo-label">Plan:</span><span class="evolucion-campo-val">${ev.Tratamiento}</span></div>`
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
                <div class="hc-error-alert">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>No se pudo cargar el historial de evoluciones.</p>
                    <button class="btn-retry" onclick="cargarEvoluciones()">
                        <i class="fas fa-redo"></i> Reintentar carga
                    </button>
                </div>`;
        }
    }
}

// ─── COLLAPSIBLE EVOLUCIONES ────────────────────────────────────────────────────
function toggleEvolucion(idx) {
    const item = document.getElementById(`ev-item-${idx}`);
    if (item) item.classList.toggle('collapsed');
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

// ─── FINALIZAR CONSULTA ────────────────────────────────────────────────────────
async function finalizarConsulta() {
    if (!_HC_CITA_ID) {
        console.error('[HC][FINALIZAR] ABORTADO: _HC_CITA_ID es', _HC_CITA_ID);
        hcToast('No hay cita activa vinculada. No se puede finalizar.', 'error');
        return;
    }

    if (!_validarCamposObligatorios()) {
        return;
    }

    const btnF = document.getElementById('btn-finalizar');
    if (btnF) {
        btnF.disabled  = true;
        btnF.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    }

    const motivoEl    = document.getElementById('hc-motivo');
    const diagEl      = document.getElementById('hc-diag');
    const evolucionEl = document.getElementById('hc-evolucion');
    const planEl      = document.getElementById('hc-plan');

    const diagnosticoVal = diagEl      ? diagEl.value.trim()      : '';
    const evolucionVal   = evolucionEl ? evolucionEl.value.trim() : '';
    const tratamientoVal = planEl      ? planEl.value.trim()      : '';
    const motivoVal      = motivoEl    ? motivoEl.value.trim()    : '';

    const payload = {
        Cita_ID:        _HC_CITA_ID,
        MotivoConsulta: motivoVal,
        Diagnostico:    diagnosticoVal,
        DiagnosticoID:  _diagSelectedID,
        Evolucion:      evolucionVal,
        Tratamiento:    tratamientoVal,
        MapaDental:     JSON.stringify(mapaDental),
        Hallazgos:      JSON.stringify(
            hallazgosData.filter(h => h.procedimiento || h.detalle)
        ),
    };

    console.log('[HC][FINALIZAR] Payload ->', payload);

    try {
        const res  = await fetch('/api/historial/finalizar', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));

        console.log('[HC][FINALIZAR] Respuesta ->', res.status, data);

        if (!res.ok || !data.ok) {
            hcToast(data.error || 'Error al finalizar la consulta.', 'error');
            return;
        }

        hcToast('Consulta finalizada y registrada exitosamente.', 'success');
        setTimeout(() => volverAlPanel(), 1800);

    } catch (err) {
        console.error('[HC] finalizarConsulta:', err);
        hcToast('Error de conexión al finalizar la consulta.', 'error');
    } finally {
        if (btnF) {
            btnF.disabled  = false;
            btnF.innerHTML = '<i class="fas fa-check-circle"></i> Finalizar Consulta';
        }
    }
}

// ─── GUARDAR HISTORIA ──────────────────────────────────────────────────────────
async function guardarHistoria(finalizar = false) {
    if (finalizar) {
        return finalizarConsulta();
    }

    if (!_HC_CITA_ID) {
        hcToast('No se puede guardar: no hay cita activa vinculada.', 'error');
        return;
    }

    const motivoEl    = document.getElementById('hc-motivo');
    const diagEl      = document.getElementById('hc-diag');
    const evolucionEl = document.getElementById('hc-evolucion');
    const planEl      = document.getElementById('hc-plan');

    const payload = {
        Cita_ID:        _HC_CITA_ID,
        MotivoConsulta: motivoEl    ? motivoEl.value.trim()    : '',
        Diagnostico:    diagEl      ? diagEl.value.trim()      : '',
        DiagnosticoID:  _diagSelectedID,
        Evolucion:      evolucionEl ? evolucionEl.value.trim() : '',
        Tratamiento:    planEl      ? planEl.value.trim()      : '',
        MapaDental:     JSON.stringify(mapaDental),
        Hallazgos:      JSON.stringify(
            hallazgosData.filter(h => h.procedimiento || h.detalle)
        ),
    };

    try {
        const res  = await fetch('/api/historial/guardar', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || !data.ok) {
            hcToast(data.error || 'Error al guardar la historia clínica.', 'error');
            return;
        }

        hcToast('Historia clínica guardada correctamente.', 'success');
        await cargarEvoluciones();

    } catch (err) {
        console.error('[HC] guardarHistoria:', err);
        hcToast('Error de conexión al guardar.', 'error');
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
    if (_HC_PACIENTE_ID) sessionStorage.setItem('hc_paciente_id', String(_HC_PACIENTE_ID));
    if (_HC_CITA_ID)     sessionStorage.setItem('hc_cita_id',     String(_HC_CITA_ID));

    initOdontograma();
    agregarHallazgo();

    cargarDatosPaciente();
    cargarEvoluciones();
    _cargarDiagnosticosBD();

    document.addEventListener('click', (e) => {
        cerrarSelector();
        const cie10 = document.getElementById('cie10-dropdown');
        if (cie10 && !e.target.closest('.cie10-wrapper')) {
            cie10.classList.remove('open');
        }
    });

    const diagInput = document.getElementById('hc-diag');
    if (diagInput) {
        diagInput.addEventListener('keydown', _cie10KeyNav);
        diagInput.addEventListener('input', (e) => {
            _diagSelectedID     = null;
            _diagSelectedNombre = '';
            buscarCIE10(e.target.value);
        });
    }
});