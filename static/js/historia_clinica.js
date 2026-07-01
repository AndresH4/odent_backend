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
let _diagSelectedID      = null;   // Diagnostico_ID numérico (null si no es de la BD)
let _diagSelectedCodigo  = '';     // Código CIE-10 seleccionado (ej. "K020")
let _diagSelectedNombre  = '';     // Nombre completo seleccionado
let _cie10ActiveIdx      = -1;
let _diagBDLoaded        = false;
let _diagBDCache         = [];     // [ {id, codigo, nombre}, ... ]  ← catálogo de la BD

// ─── CATÁLOGO CIE-10 ESTÁTICO (respaldo offline / fusión si BD falla) ─────────
// Se usa solo cuando el fetch a /api/diagnosticos no devuelve datos.
const CIE10_DENTAL_FALLBACK = [
    { id: null, codigo: 'K00.0', nombre: 'Anodoncia' },
    { id: null, codigo: 'K00.1', nombre: 'Dientes supernumerarios' },
    { id: null, codigo: 'K00.2', nombre: 'Anomalías del tamaño y forma de los dientes' },
    { id: null, codigo: 'K00.3', nombre: 'Dientes moteados (fluorosis dental)' },
    { id: null, codigo: 'K00.4', nombre: 'Perturbaciones en la formación de los dientes' },
    { id: null, codigo: 'K00.5', nombre: 'Anomalías hereditarias de la estructura dentaria' },
    { id: null, codigo: 'K00.6', nombre: 'Perturbaciones en la erupción de los dientes' },
    { id: null, codigo: 'K00.8', nombre: 'Otros trastornos del desarrollo de los dientes' },
    { id: null, codigo: 'K01.0', nombre: 'Dientes incluidos' },
    { id: null, codigo: 'K01.1', nombre: 'Dientes impactados' },
    { id: null, codigo: 'K02.0', nombre: 'Caries limitada al esmalte' },
    { id: null, codigo: 'K02.1', nombre: 'Caries de la dentina' },
    { id: null, codigo: 'K02.2', nombre: 'Caries del cemento' },
    { id: null, codigo: 'K02.3', nombre: 'Caries dental detenida' },
    { id: null, codigo: 'K02.9', nombre: 'Caries dental no especificada' },
    { id: null, codigo: 'K04.0', nombre: 'Pulpitis' },
    { id: null, codigo: 'K04.1', nombre: 'Necrosis de la pulpa' },
    { id: null, codigo: 'K04.4', nombre: 'Periodontitis apical aguda originada en la pulpa' },
    { id: null, codigo: 'K04.5', nombre: 'Periodontitis apical crónica' },
    { id: null, codigo: 'K04.6', nombre: 'Absceso periapical con fístula' },
    { id: null, codigo: 'K04.7', nombre: 'Absceso periapical sin fístula' },
    { id: null, codigo: 'K05.0', nombre: 'Gingivitis aguda' },
    { id: null, codigo: 'K05.1', nombre: 'Gingivitis crónica' },
    { id: null, codigo: 'K05.2', nombre: 'Periodontitis aguda' },
    { id: null, codigo: 'K05.3', nombre: 'Periodontitis crónica' },
    { id: null, codigo: 'K06.0', nombre: 'Retracción gingival' },
    { id: null, codigo: 'K08.3', nombre: 'Raíz dental retenida' },
    { id: null, codigo: 'K10.3', nombre: 'Alveolitis del maxilar' },
    { id: null, codigo: 'K12.0', nombre: 'Estomatitis aftosa recurrente' },
    { id: null, codigo: 'S02.5', nombre: 'Fractura de los dientes' },
    { id: null, codigo: 'S03.2', nombre: 'Luxación de diente' },
    { id: null, codigo: 'Z01.2', nombre: 'Examen odontológico' },
    { id: null, codigo: 'Z46.3', nombre: 'Prueba y ajuste de prótesis dental' },
    { id: null, codigo: 'Z46.4', nombre: 'Prueba y ajuste de dispositivo ortodóncico' },
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

// ─── DIAGNÓSTICO: CARGA DESDE BD ──────────────────────────────────────────────
/**
 * Carga el catálogo CIE-10 desde el endpoint de la BD.
 * Se ejecuta en DOMContentLoaded (precarga en background) y también
 * bajo demanda la primera vez que el usuario empieza a escribir.
 *
 * El backend devuelve:
 *   { "ok": true, "data": [ {"id":1, "codigo":"Z012", "nombre":"EXAMEN ODONTOLOGICO"}, ... ] }
 *
 * Cada entrada queda en _diagBDCache con la forma normalizada:
 *   { id, codigo, codigoConPunto, nombre }
 * donde codigoConPunto convierte "K020" → "K02.0" para matching bidireccional.
 */
async function _cargarDiagnosticosBD() {
    if (_diagBDLoaded) return;
    try {
        const res  = await fetch('/api/diagnosticos', { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.ok && Array.isArray(data.data) && data.data.length > 0) {
            _diagBDCache = data.data.map(d => ({
                id:            d.id,
                codigo:        (d.codigo || '').toUpperCase(),
                codigoConPunto: _agregarPunto(d.codigo || ''),
                nombre:        d.nombre,
            }));
            console.log(`[HC][CIE-10] Catálogo BD cargado: ${_diagBDCache.length} diagnósticos`);
        } else {
            throw new Error('Respuesta vacía o inválida');
        }
    } catch (err) {
        console.warn('[HC][CIE-10] Fallback al catálogo estático:', err.message);
        // Poblar con el catálogo estático si la BD falla
        _diagBDCache = CIE10_DENTAL_FALLBACK.map(d => ({
            id:             d.id,
            codigo:         (d.codigo || '').toUpperCase().replace('.', ''),
            codigoConPunto: d.codigo,
            nombre:         d.nombre,
        }));
    }
    _diagBDLoaded = true;
}

/**
 * Convierte un código sin punto a su forma con punto decimal estándar.
 * Regla: el punto va después de la(s) letra(s) y los primeros 2 dígitos.
 * Ej: "K020" → "K02.0"  |  "Z012" → "Z01.2"  |  "S025" → "S02.5"
 * Si ya tiene punto o es muy corto, lo devuelve tal cual.
 */
function _agregarPunto(codigo) {
    if (!codigo) return '';
    const c = codigo.trim().toUpperCase();
    if (c.includes('.')) return c;
    // Formato esperado: 1-2 letras + dígitos
    const m = c.match(/^([A-Z]+\d{2})(\d+)$/);
    return m ? `${m[1]}.${m[2]}` : c;
}

/**
 * Normaliza una cadena de búsqueda para comparación bidireccional:
 * elimina puntos y convierte a minúsculas.
 */
function _normQ(str) {
    return (str || '').toLowerCase().replace(/\./g, '');
}

// ─── CIE-10 AUTOCOMPLETE ───────────────────────────────────────────────────────
/**
 * Filtra el catálogo en memoria buscando coincidencias en código Y nombre,
 * con tolerancia a punto decimal (K020 y K02.0 devuelven el mismo resultado).
 * Dispara desde 1 carácter.
 */
async function buscarCIE10(query) {
    const dropdown = document.getElementById('cie10-dropdown');
    if (!dropdown) return;
    _cie10ActiveIdx = -1;

    const q = query.trim();

    if (q.length < 1) {
        _cerrarDropdown(dropdown);
        _limpiarSeleccionDiag();
        return;
    }

    // Asegurar catálogo cargado antes de filtrar
    if (!_diagBDLoaded) {
        await _cargarDiagnosticosBD();
    }

    const qNorm = _normQ(q);  // sin punto, minúsculas

    const coincidentes = _diagBDCache.filter(item => {
        const codigoNorm  = _normQ(item.codigo);
        const nombreNorm  = (item.nombre || '').toLowerCase();
        return codigoNorm.includes(qNorm) || nombreNorm.includes(qNorm);
    });

    // Ordenar: coincidencia al inicio del código primero
    coincidentes.sort((a, b) => {
        const aStart = _normQ(a.codigo).startsWith(qNorm) ? 0 : 1;
        const bStart = _normQ(b.codigo).startsWith(qNorm) ? 0 : 1;
        return aStart - bStart;
    });

    const resultados = coincidentes.slice(0, 20);

    if (resultados.length === 0) {
        dropdown.innerHTML = `<div class="cie10-empty" style="padding:12px 14px;font-size:13px;color:#94a3b8;">
            <i class="fas fa-search" style="margin-right:6px;opacity:.5;"></i>
            Sin coincidencias para "<strong>${_escapeHtml(q)}</strong>"
        </div>`;
    } else {
        const qReg = new RegExp(`(${_escapeRegex(qNorm)})`, 'gi');

        dropdown.innerHTML = resultados.map((item, i) => {
            const codigoDisplay = item.codigoConPunto || item.codigo;
            const nombreEsc     = _escapeHtml(item.nombre);

            // Resaltar coincidencia en el nombre (sobre texto normalizado)
            const nombreHL = nombreEsc.replace(
                new RegExp(`(${_escapeRegex(q.replace(/\./g, ''))})`, 'gi'),
                '<mark>$1</mark>'
            );

            const idAttr    = item.id !== null ? item.id : 'null';
            const codigoStr = _escapeAttr(codigoDisplay);
            const nombreStr = item.nombre.replace(/'/g, "\\'").replace(/"/g, '&quot;');

            return `<div
                class="cie10-option"
                role="option"
                data-idx="${i}"
                style="padding:10px 14px;cursor:pointer;display:flex;align-items:center;gap:10px;border-bottom:1px solid #f1f5f9;"
                onmousedown="seleccionarCIE10(${idAttr}, '${codigoStr}', '${nombreStr}')">
                    ${codigoDisplay
                        ? `<span class="cie10-code" style="font-weight:700;font-size:12px;color:#0ea5e9;min-width:52px;">${_escapeHtml(codigoDisplay)}</span>`
                        : ''}
                    <span class="cie10-desc" style="font-size:13px;color:#334155;">${nombreHL}</span>
            </div>`;
        }).join('');
    }

    _abrirDropdown(dropdown);
}

function _abrirDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.style.display = 'block';
    dropdown.classList.add('open');
}

function _cerrarDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.style.display = 'none';
    dropdown.classList.remove('open');
}

function _limpiarSeleccionDiag() {
    _diagSelectedID     = null;
    _diagSelectedCodigo = '';
    _diagSelectedNombre = '';
    _setInput('hc-diag-id', '');
}

function _escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function _escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function _escapeAttr(str) {
    return String(str || '').replace(/'/g, "\\'");
}

/**
 * Al seleccionar una opción del dropdown:
 *  - Pinta en el input visual: "[K02.0] CARIES LIMITADA AL ESMALTE"
 *  - Asigna el Diagnostico_ID al campo oculto #hc-diag-id
 *  - Guarda codigo y nombre en las variables de estado
 *  - Cierra el dropdown
 *  - Limpia estado de error si lo había
 */
function seleccionarCIE10(id, codigo, nombre) {
    const input   = document.getElementById('hc-diag');
    const hidden  = document.getElementById('hc-diag-id');
    const dropdown = document.getElementById('cie10-dropdown');

    // Formato visual obligatorio: "[K02.0] NOMBRE"
    const etiquetaVisual = codigo ? `[${codigo}] ${nombre}` : nombre;

    if (input) {
        input.value = etiquetaVisual;
        _limpiarErrorCampo(input);
    }

    _diagSelectedID     = (id !== null && id !== undefined && String(id) !== 'null')
                          ? parseInt(id, 10)
                          : null;
    _diagSelectedCodigo = codigo || '';
    _diagSelectedNombre = etiquetaVisual;

    // El campo oculto recibe el ID numérico si existe, o el código como texto
    if (hidden) {
        hidden.value = _diagSelectedID !== null
            ? String(_diagSelectedID)
            : _diagSelectedCodigo;
    }

    _cerrarDropdown(dropdown);
}

function ocultarDropdownCIE10() {
    setTimeout(() => {
        _cerrarDropdown(document.getElementById('cie10-dropdown'));
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
        _cerrarDropdown(dropdown);
    }
}

function _cie10Highlight(opciones) {
    opciones.forEach((o, i) => o.classList.toggle('highlighted', i === _cie10ActiveIdx));
    if (_cie10ActiveIdx >= 0) opciones[_cie10ActiveIdx].scrollIntoView({ block: 'nearest' });
}

// ─── VALIDACIÓN CAMPOS OBLIGATORIOS ────────────────────────────────────────────
function _marcarErrorCampo(el) {
    if (!el) return;
    el.classList.add('hc-field-error');
    const errMsgId = el.getAttribute('aria-describedby');
    if (errMsgId) {
        const errEl = document.getElementById(errMsgId);
        if (errEl) errEl.classList.add('visible');
    }
}

function _limpiarErrorCampo(el) {
    if (!el) return;
    el.classList.remove('hc-field-error');
    const errMsgId = el.getAttribute('aria-describedby');
    if (errMsgId) {
        const errEl = document.getElementById(errMsgId);
        if (errEl) errEl.classList.remove('visible');
    }
}

function _validarCamposObligatorios() {
    const diagEl      = document.getElementById('hc-diag');
    const evolucionEl = document.getElementById('hc-evolucion');
    const planEl      = document.getElementById('hc-plan');

    const diagVal  = diagEl      ? diagEl.value.trim()      : '';
    const evoVal   = evolucionEl ? evolucionEl.value.trim() : '';
    const planVal  = planEl      ? planEl.value.trim()      : '';

    const errores = [];

    [diagEl, evolucionEl, planEl].forEach(el => _limpiarErrorCampo(el));

    const errContainer = document.getElementById('hc-validation-errors');
    if (errContainer) errContainer.style.display = 'none';

    if (!evoVal) {
        errores.push('Evolución / Procedimiento realizado');
        _marcarErrorCampo(evolucionEl);
    }
    if (!diagVal) {
        errores.push('Diagnóstico (CIE-10)');
        _marcarErrorCampo(diagEl);
    }
    if (!planVal) {
        errores.push('Plan a seguir / Tratamiento');
        _marcarErrorCampo(planEl);
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

function _limpiarErrorEnInput(el) {
    if (!el) return;
    el.addEventListener('input', () => {
        if (el.value.trim()) _limpiarErrorCampo(el);
    });
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

// ─── FETCH Y RENDER DE EVOLUCIONES (acordeón) ─────────────────────────────────
async function cargarEvoluciones() {
    if (!_HC_PACIENTE_ID) return;

    const cont = document.getElementById('evoluciones-container');
    if (!cont) return;

    cont.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
            <div class="skeleton skeleton-line" style="height:58px;border-radius:12px;"></div>
            <div class="skeleton skeleton-line" style="height:58px;border-radius:12px;"></div>
            <div class="skeleton skeleton-line w-60" style="height:58px;border-radius:12px;"></div>
        </div>`;

    try {
        const url  = `/api/historial/paciente/${_HC_PACIENTE_ID}/evoluciones`;
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

        cont.innerHTML = data.data.map((ev, idx) => {
            const esCitaActual = ev.Cita_ID === _HC_CITA_ID;
            const colapsado    = esCitaActual ? '' : ' collapsed';
            const tieneDatos   = ev.Diagnostico || ev.Evolucion || ev.Tratamiento;

            return `
            <div class="evolucion-item${colapsado}" id="ev-item-${idx}">
                <div class="evolucion-header" onclick="toggleEvolucion(${idx})"
                     role="button" aria-expanded="${esCitaActual}" tabindex="0"
                     onkeydown="if(event.key==='Enter'||event.key===' '){toggleEvolucion(${idx})}">
                    <div class="evolucion-meta">
                        <span class="evolucion-fecha">
                            <i class="fas fa-calendar-alt" style="margin-right:4px;"></i>
                            ${ev.Fecha || '—'}${ev.Hora_Inicio ? ' · ' + ev.Hora_Inicio : ''}
                        </span>
                        <span class="evolucion-esp">${_escapeHtml(ev.NombreEspecialista || '—')}</span>
                        <span class="badge ${estadoClase[ev.EstadoAgenda] || 'badge-ocupado'}">
                            ${_escapeHtml(ev.EstadoAgenda || '—')}
                        </span>
                        ${ev.Nombre_Especialidad
                            ? `<span class="evolucion-especialidad">${_escapeHtml(ev.Nombre_Especialidad)}</span>`
                            : ''}
                        ${ev.Motivo_Consulta
                            ? `<span class="evolucion-motivo-chip">${_escapeHtml(ev.Motivo_Consulta)}</span>`
                            : ''}
                        ${esCitaActual
                            ? `<span class="badge-actual"><i class="fas fa-circle" style="font-size:6px;margin-right:4px;"></i>Actual</span>`
                            : ''}
                    </div>
                    <i class="fas fa-chevron-down evolucion-toggle-icon" aria-hidden="true"></i>
                </div>

                <div class="evolucion-body">
                    ${ev.Motivo_Consulta ? `
                    <div class="evolucion-campo">
                        <span class="evolucion-campo-label">
                            <i class="fas fa-comment-medical"></i> Motivo
                        </span>
                        <span class="evolucion-campo-val">${_escapeHtml(ev.Motivo_Consulta)}</span>
                    </div>` : ''}

                    ${ev.Diagnostico && ev.Diagnostico.trim() ? `
                    <div class="evolucion-campo">
                        <span class="evolucion-campo-label">
                            <i class="fas fa-stethoscope"></i> Diagnóstico
                        </span>
                        <span class="evolucion-campo-val evolucion-diag">${_escapeHtml(ev.Diagnostico)}</span>
                    </div>` : ''}

                    ${ev.Evolucion && ev.Evolucion.trim() ? `
                    <div class="evolucion-campo">
                        <span class="evolucion-campo-label">
                            <i class="fas fa-clipboard-check"></i> Evolución
                        </span>
                        <span class="evolucion-campo-val">${_escapeHtml(ev.Evolucion)}</span>
                    </div>` : ''}

                    ${ev.Tratamiento && ev.Tratamiento.trim() ? `
                    <div class="evolucion-campo">
                        <span class="evolucion-campo-label">
                            <i class="fas fa-notes-medical"></i> Plan
                        </span>
                        <span class="evolucion-campo-val">${_escapeHtml(ev.Tratamiento)}</span>
                    </div>` : ''}

                    ${!tieneDatos ? `
                    <p class="evolucion-vacia">
                        <i class="fas fa-info-circle" style="margin-right:5px;"></i>
                        Sin historial clínico registrado para esta consulta.
                    </p>` : ''}
                </div>
            </div>`;
        }).join('');

    } catch (err) {
        console.error('[HC] cargarEvoluciones:', err);
        if (cont) {
            cont.innerHTML = `
                <div class="hc-error-alert">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>No se pudo cargar el historial de evoluciones.</p>
                    <button class="btn-retry" onclick="cargarEvoluciones()" type="button">
                        <i class="fas fa-redo"></i> Reintentar carga
                    </button>
                </div>`;
        }
    }
}

// ─── TOGGLE ACORDEÓN ───────────────────────────────────────────────────────────
function toggleEvolucion(idx) {
    const item = document.getElementById(`ev-item-${idx}`);
    if (!item) return;
    const estaColapsado = item.classList.toggle('collapsed');
    const header = item.querySelector('.evolucion-header');
    if (header) header.setAttribute('aria-expanded', String(!estaColapsado));
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

// ─── GUARDAR HISTORIA (borrador) ───────────────────────────────────────────────
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

    // Precarga del catálogo BD en background (sin bloquear la UI)
    _cargarDiagnosticosBD();

    // Cerrar selector odontograma y dropdown CIE-10 al hacer clic fuera
    document.addEventListener('click', (e) => {
        cerrarSelector();
        const cie10 = document.getElementById('cie10-dropdown');
        if (cie10 && !e.target.closest('.cie10-wrapper')) {
            _cerrarDropdown(cie10);
        }
    });

    // Input diagnóstico: navegación por teclado + búsqueda reactiva desde BD
    const diagInput = document.getElementById('hc-diag');
    if (diagInput) {
        diagInput.addEventListener('keydown', _cie10KeyNav);
        diagInput.addEventListener('input', (e) => {
            // Limpiar error visual al escribir
            if (e.target.value.trim()) _limpiarErrorCampo(e.target);
            // Resetear selección guardada: el usuario está editando manualmente
            _limpiarSeleccionDiag();
            // Lanzar búsqueda predictiva desde 1 carácter
            buscarCIE10(e.target.value);
        });
    }

    // Limpiar errores en tiempo real para Evolución y Plan
    _limpiarErrorEnInput(document.getElementById('hc-evolucion'));
    _limpiarErrorEnInput(document.getElementById('hc-plan'));
});