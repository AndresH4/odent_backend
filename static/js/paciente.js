// static/js/paciente.js
// Archivo: paciente.js  — Stylo Dental Pro
'use strict';

// ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────
let _sesionPaciente        = null;
let _pacienteId            = null;
let _usuarioId             = null;
let _citasData             = [];
let _citaParaCancelar      = null;
let _cancelarConMulta      = false;
let _accionPendienteSimple = null;
let _dropdownOpen          = false;

let _encuestaCitaId        = null;
let _encuestaPreguntas     = [];
let _encuestaExitoTimer    = null;

// ─── POLLING DE ESTADOS ───────────────────────────────────────────────────────
let _pollingIntervalId     = null;
const POLLING_INTERVAL_MS  = 15000; // 15 segundos

// ─── MAPA DE VISTAS ───────────────────────────────────────────────────────────
const VISTAS_PACIENTE = {
    inicio   : { el: 'vista-inicio',    btn: 'btn-inicio',    titulo: 'Paciente'           },
    historial: { el: 'vista-historial', btn: 'btn-historial', titulo: 'Historial de Citas' },
    multas   : { el: 'vista-multas',    btn: 'btn-multas',    titulo: 'Mis Multas'         },
    config   : { el: 'vista-config',    btn: 'btn-config',    titulo: 'Mi Perfil'          },
};

// ─── MODALES ──────────────────────────────────────────────────────────────────
function _mostrarNotificacion(titulo, mensaje, tipo) {
    const modal   = document.getElementById('modalNotificacion');
    const content = document.getElementById('modalNotificacion-content');
    const iconEl  = document.getElementById('notif-icon');
    const titEl   = document.getElementById('notif-titulo');
    const msgEl   = document.getElementById('notif-mensaje');

    if (tipo === 'error') {
        content.className = 'modal-content p-10 text-center border-t-8 border-red-400';
        iconEl.innerHTML  = '<i class="fas fa-circle-exclamation text-red-400"></i>';
    } else if (tipo === 'success') {
        content.className = 'modal-content p-10 text-center border-t-8 border-green-500';
        iconEl.innerHTML  = '<i class="fas fa-circle-check text-green-500"></i>';
    } else {
        content.className = 'modal-content p-10 text-center border-t-8 border-sky-500';
        iconEl.innerHTML  = '<i class="fas fa-circle-info text-sky-500"></i>';
    }

    titEl.textContent   = titulo;
    msgEl.textContent   = mensaje;
    modal.style.display = 'flex';
}

window.cerrarModalNotificacion = function () {
    document.getElementById('modalNotificacion').style.display = 'none';
};

// ─── SESIÓN ───────────────────────────────────────────────────────────────────
function _cargarSesion() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) { window.location.replace('/login'); return; }

    const u = JSON.parse(raw);
    if (u.Rol_ID !== 3) { window.location.replace('/login'); return; }

    _sesionPaciente = u;
    _usuarioId      = u.Usuario_ID;

    const nombreCompleto = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
    const inicial        = (u.Nombres || '').trim().charAt(0).toUpperCase() || 'P';

    _setText('avatar-letras',         inicial);
    _setText('nombre-usuario-header', nombreCompleto);
    _setText('perfil-avatar-grande',  inicial);
    _setText('nombre-menu',           nombreCompleto.toUpperCase());
    _setText('doc-menu',              u.NumeroDocumento || '');
    _setText('nombre-usuario',        nombreCompleto);
    _setText('perfil-nombres',        u.Nombres    || '');
    _setText('perfil-apellidos',      u.Apellidos  || '');
    _setText('perfil-correo',         u.Correo     || '');
    _setText('perfil-numDoc',         u.NumeroDocumento || '');
    _setText('perfil-telefono',       u.Telefono   || '');
    _setText('perfil-nacimiento',     u.FechaNacimiento || '');
    _setText('email-menu',            u.Correo     || '—');
    _setText('telefono-menu',         u.Telefono   || '—');

    _cargarTipoDocumento(u.TipoDoc_ID, u.NumeroDocumento);

    fetch(`/api/paciente/por-usuario/${_usuarioId}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.Paciente_ID) {
                _pacienteId = data.Paciente_ID;
                _cargarCitasPaciente();
                _cargarAfiliacionCompleta();
                _iniciarPolling();
            }
        })
        .catch(err => console.error('[paciente] Error obteniendo Paciente_ID:', err));
}

// ─── TIPO DE DOCUMENTO ────────────────────────────────────────────────────────
async function _cargarTipoDocumento(tipoDocId, numeroDoc) {
    try {
        const res   = await fetch('/api/tipos_documento');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const lista = await res.json();

        const tipo       = lista.find(t => String(t.TipoDoc_ID) === String(tipoDocId));
        const nombreTipo = tipo
            ? (tipo.Nombre_Tipo_Documento || tipo.Descripcion || tipo.Nombre_Tipo || 'Doc.')
            : 'Doc.';

        _setText('doc-detalle-menu', `${nombreTipo}: ${numeroDoc || '—'}`);
    } catch (err) {
        console.warn('[paciente] No se pudo cargar tipo de documento:', err);
        _setText('doc-detalle-menu', numeroDoc || '—');
    }
}

// ─── EPS COMPLETA ─────────────────────────────────────────────────────────────
async function _cargarAfiliacionCompleta() {
    if (!_usuarioId) return;
    try {
        const [resAfil, resEps, resRegimen, resTipo] = await Promise.all([
            fetch('/api/afiliacion'),
            fetch('/api/eps'),
            fetch('/api/regimen-eps'),
            fetch('/api/tipo-eps'),
        ]);

        if (!resAfil.ok) return;

        const dataAfil    = await resAfil.json();
        const dataEps     = resEps.ok     ? await resEps.json()     : [];
        const dataRegimen = resRegimen.ok ? await resRegimen.json() : [];
        const dataTipo    = resTipo.ok    ? await resTipo.json()    : [];

        const listaAfil    = _normalizar(dataAfil);
        const listaEps     = _normalizar(dataEps);
        const listaRegimen = _normalizar(dataRegimen);
        const listaTipos   = _normalizar(dataTipo);

        const afil = listaAfil.find(
            a => String(a.Usuario_ID || a.ID_Usuario) === String(_usuarioId)
        );
        if (!afil) return;

        const epsId     = afil.EPS_ID     || afil.Id_EPS     || afil.eps_id     || null;
        const tipoEpsId = afil.TipoEPS_ID || afil.ID_Tipo_EPS || afil.tipoeps_id || null;

        let nombreEPS = '';
        if (epsId) {
            const epsObj = listaEps.find(e =>
                String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId)
            );
            nombreEPS = epsObj ? (epsObj.Nombre_EPS || epsObj.nombre_eps || '—') : '—';
        }
        _setText('eps-menu',   nombreEPS || '—');
        _setText('perfil-eps', nombreEPS || '—');

        let nombreRegimen = '';
        let regimenId = afil.Regimen_ID || afil.ID_Regimen_EPS || afil.regimen_id || null;
        if (!regimenId && epsId) {
            const epsObj = listaEps.find(e =>
                String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId)
            );
            regimenId = epsObj ? (epsObj.Regimen_ID || epsObj.regimen_id || null) : null;
        }
        if (regimenId) {
            const regObj = listaRegimen.find(r =>
                String(r.Regimen_ID || r.ID_Regimen_EPS || r.regimen_id) === String(regimenId)
            );
            nombreRegimen = regObj
                ? (regObj.Descripcion || regObj.Nombre_Regimen || regObj.nombre_regimen || '—')
                : '—';
        }
        _setText('regimen-menu', nombreRegimen || '—');

        let nombreTipoEPS = '';
        if (tipoEpsId) {
            const tipoObj = listaTipos.find(t =>
                String(t.TipoEPS_ID || t.ID_Tipo_EPS || t.tipoeps_id) === String(tipoEpsId)
            );
            nombreTipoEPS = tipoObj
                ? (tipoObj.Nombre_Tipo || tipoObj.nombre_tipo || tipoObj.Nombre || '—')
                : '—';
        }
        _setText('tipoeps-menu', nombreTipoEPS || '—');

    } catch (err) {
        console.warn('[paciente] Error en _cargarAfiliacionCompleta:', err);
    }
}

function _normalizar(data) {
    if (Array.isArray(data))               return data;
    if (data && Array.isArray(data.data))  return data.data;
    if (data && Array.isArray(data.items)) return data.items;
    return [];
}

// ─── UTILIDADES DOM ───────────────────────────────────────────────────────────
function _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function _setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val ?? '';
}

// ─── RELOJ ────────────────────────────────────────────────────────────────────
function _actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();
    const horas = ahora.getHours();

    const el = document.getElementById('reloj');
    if (el) {
        const h   = ahora.getHours();
        const m   = String(ahora.getMinutes()).padStart(2, '0');
        const s   = String(ahora.getSeconds()).padStart(2, '0');
        const h12 = h % 12 || 12;
        const ampm = h < 12 ? 'A.M.' : 'P.M.';
        el.innerText = `${String(h12).padStart(2, '0')}:${m}:${s} ${ampm}`;
    }

    const esHorarioLaboral =
        (dia >= 1 && dia <= 5 && horas >= 8 && horas < 18) ||
        (dia === 6 && horas >= 8 && horas < 13);

    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot && txt) {
        dot.className   = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
        txt.innerText   = esHorarioLaboral ? 'Estado: En Jornada' : 'Estado: Fuera de Horario';
        txt.style.color = esHorarioLaboral ? '#10b981' : '#ef4444';
    }
}

// ─── DROPDOWN DE PERFIL ───────────────────────────────────────────────────────
window.toggleProfileDropdown = function () {
    _dropdownOpen ? _closeProfileDropdown() : _openProfileDropdown();
};

function _openProfileDropdown() {
    document.getElementById('profile-dropdown')?.classList.add('show');
    _dropdownOpen = true;
}

window.closeProfileDropdown = function () { _closeProfileDropdown(); };

function _closeProfileDropdown() {
    document.getElementById('profile-dropdown')?.classList.remove('show');
    _dropdownOpen = false;
}

// ─── ACTIVAR VISTA ────────────────────────────────────────────────────────────
window.cambiarVista = function (vista) {
    _closeProfileDropdown();

    Object.values(VISTAS_PACIENTE).forEach(({ el }) =>
        document.getElementById(el)?.classList.add('hidden')
    );
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const cfg = VISTAS_PACIENTE[vista];
    if (!cfg) return;

    document.getElementById(cfg.el)?.classList.remove('hidden');
    document.getElementById(cfg.btn)?.classList.add('active');

    const tituloEl = document.getElementById('titulo-principal');
    if (tituloEl) tituloEl.textContent = cfg.titulo;

    if (vista === 'historial') _renderHistorial();
    if (vista === 'multas')    _renderMultasPaciente();
    if (vista === 'config')    _precargarPerfil();
};

// ─── CARGA DE CITAS ───────────────────────────────────────────────────────────
async function _cargarCitasPaciente() {
    if (!_pacienteId) return;
    try {
        const res  = await fetch(`/api/paciente/${_pacienteId}/citas`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        _citasData = Array.isArray(data) ? data : [];
        _renderTablaCitas();
    } catch (err) {
        console.error('[paciente] Error cargando citas:', err);
        _citasData = [];
        _renderTablaCitas();
    }
}

// ─── POLLING DE ESTADOS EN TIEMPO REAL ───────────────────────────────────────
function _iniciarPolling() {
    if (_pollingIntervalId) clearInterval(_pollingIntervalId);
    _pollingIntervalId = setInterval(_pollEstadosCitas, POLLING_INTERVAL_MS);
}

function _detenerPolling() {
    if (_pollingIntervalId) {
        clearInterval(_pollingIntervalId);
        _pollingIntervalId = null;
    }
}

async function _pollEstadosCitas() {
    if (!_pacienteId || !_citasData.length) return;
    try {
        const res = await fetch(`/api/paciente/${_pacienteId}/citas`, { cache: 'no-store' });
        if (!res.ok) return;
        const nuevasCitas = await res.json();
        if (!Array.isArray(nuevasCitas)) return;

        let huboCambio = false;

        nuevasCitas.forEach(citaNueva => {
            const idx = _citasData.findIndex(c => c.Cita_ID === citaNueva.Cita_ID);
            if (idx === -1) {
                _citasData.push(citaNueva);
                huboCambio = true;
                return;
            }
            const citaVieja = _citasData[idx];
            if (citaVieja.EstadoAgenda !== citaNueva.EstadoAgenda ||
                citaVieja.EstadoMulta  !== citaNueva.EstadoMulta) {
                _citasData[idx] = citaNueva;
                huboCambio = true;
                _actualizarFilaEstadoEnDOM(citaNueva);
            }
        });

        if (huboCambio) {
            _renderTablaCitas();
            const vistaHistorial = document.getElementById('vista-historial');
            if (vistaHistorial && !vistaHistorial.classList.contains('hidden')) {
                _renderHistorial();
            }
        }
    } catch (err) {
        console.warn('[paciente][polling] Error consultando estados:', err);
    }
}

function _actualizarFilaEstadoEnDOM(cita) {
    const estadoInfo = _resolverEstado(cita);

    // Actualizar en tabla inicio
    const filaInicio = document.querySelector(`tr[data-cita-id="${cita.Cita_ID}"]`);
    if (filaInicio) {
        const badgeEl = filaInicio.querySelector('.badge-estado-cita');
        if (badgeEl) {
            badgeEl.className = `badge-estado-cita text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}`;
            badgeEl.textContent = estadoInfo.label;
        }
    }

    // Actualizar en tabla historial
    const filaHistorial = document.getElementById(`historial-row-${cita.Cita_ID}`);
    if (filaHistorial) {
        const badgeEl = filaHistorial.querySelector('.badge-estado-cita');
        if (badgeEl) {
            badgeEl.className = `badge-estado-cita text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}`;
            badgeEl.textContent = estadoInfo.label;
        }
        // Mostrar/ocultar botón reporte según nuevo estado
        if ((cita.EstadoAgenda || '').toLowerCase() === 'cumplida') {
            const celdaReporte = filaHistorial.querySelector('.celda-reporte');
            if (celdaReporte && !celdaReporte.querySelector('button[data-reporte]')) {
                celdaReporte.innerHTML = _htmlBotonReporte(cita.Cita_ID);
            }
        }
    }
}

// ─── HELPERS DE ESTADO ───────────────────────────────────────────────────────
function _resolverEstado(c) {
    const hoy    = new Date().toISOString().split('T')[0];
    const estado = (c.EstadoAgenda || '').toLowerCase();

    if (estado === 'cancelado') {
        if (c.EstadoMulta && c.EstadoMulta !== 'Sin multa') {
            return { label: 'Cancelada con multa', clase: 'bg-amber-100 text-amber-700' };
        }
        return { label: 'Cancelada', clase: 'bg-red-100 text-red-600' };
    }
    if (estado === 'cumplida') {
        return { label: 'Cumplida', clase: 'bg-green-100 text-green-700' };
    }
    if (estado === 'ocupado' && c.Fecha < hoy) {
        return { label: 'Cancelada con multa', clase: 'bg-amber-100 text-amber-700' };
    }
    if (estado === 'ocupado' || estado === 'disponible') {
        return { label: 'Pendiente', clase: 'bg-sky-100 text-sky-700' };
    }
    return { label: c.EstadoAgenda || '—', clase: 'bg-slate-100 text-slate-500' };
}

const ESTADOS_EXCLUIDOS_DE_INICIO = ['Cancelada', 'Cancelada con multa'];

function _esCitaActiva(c) {
    const estadoInfo = _resolverEstado(c);
    if (ESTADOS_EXCLUIDOS_DE_INICIO.includes(estadoInfo.label)) return false;
    const hoy    = new Date().toISOString().split('T')[0];
    const estado = (c.EstadoAgenda || '').toLowerCase();
    return (estado === 'ocupado' || estado === 'disponible') && c.Fecha >= hoy;
}

function _esCitaHistorial(c) {
    return !_esCitaActiva(c);
}

function _citaEncuestaCompletada(c) {
    return c.Encuesta_Completada === 1
        || c.Encuesta_Completada === true
        || c.Encuesta_Enviada === 1
        || c.Encuesta_Enviada === true;
}

function _citaEsCumplida(c) {
    return (c.EstadoAgenda || '').toLowerCase() === 'cumplida';
}

// ─── HTML BOTÓN REPORTE ───────────────────────────────────────────────────────
function _htmlBotonReporte(citaId) {
    return `<button data-reporte onclick="abrirReportePaciente(${citaId})"
        class="text-[10px] bg-sky-50 text-sky-600 border border-sky-200 px-4 py-2 rounded-xl font-black hover:bg-sky-600 hover:text-white transition-all uppercase inline-flex items-center gap-1">
        <i class="fas fa-file-medical text-sm"></i> Reporte
    </button>`;
}

// ─── RENDER TABLA PRINCIPAL (INICIO) ─────────────────────────────────────────
function _renderTablaCitas() {
    const tbody   = document.getElementById('tabla-citas-body');
    const noMsg   = document.getElementById('no-citas-msg');
    const countEl = document.getElementById('count-citas');
    if (!tbody) return;

    const activas = _citasData.filter(_esCitaActiva);
    if (countEl) countEl.textContent = activas.length;

    tbody.innerHTML = '';
    if (activas.length === 0) {
        noMsg?.classList.remove('hidden');
        return;
    }
    noMsg?.classList.add('hidden');

    activas.forEach(c => {
        const estadoInfo = _resolverEstado(c);
        const tr = document.createElement('tr');
        tr.setAttribute('data-cita-id', c.Cita_ID);
        tr.innerHTML = `
            <td class="p-5 font-black text-slate-700 uppercase text-xs">${c.NombrePaciente || '—'}</td>
            <td class="p-5 text-xs text-slate-500">${c.NumeroDocumento || '—'}</td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5 text-center">
                <span class="font-mono font-black text-slate-700 bg-slate-100 px-3 py-1.5 rounded-lg text-xs tracking-[0.2em] border border-slate-200 inline-block">
                    ${c.Codigo_Verificacion || '------'}
                </span>
            </td>
            <td class="p-5">
                <span class="badge-estado-cita text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}">
                    ${estadoInfo.label}
                </span>
            </td>
            <td class="p-5 text-center">
                ${(c.EstadoAgenda || '').toLowerCase() === 'ocupado'
                    ? `<button onclick="abrirModalCancelar(${c.Cita_ID})"
                           class="text-[10px] bg-red-50 text-red-500 border border-red-200 px-4 py-2 rounded-xl font-black hover:bg-red-100 transition-all uppercase">
                           <i class="fas fa-ban mr-1"></i> Cancelar
                       </button>`
                    : '<span class="text-slate-300 text-[10px] font-bold">—</span>'
                }
            </td>`;
        tbody.appendChild(tr);
    });
}

// ─── RENDER HISTORIAL ─────────────────────────────────────────────────────────
function _renderHistorial() {
    const tbody = document.getElementById('tabla-historial-completo');
    if (!tbody) return;
    tbody.innerHTML = '';

    const historial = _citasData.filter(_esCitaHistorial);

    if (historial.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-10 text-center text-slate-400 font-bold italic text-xs uppercase">Sin historial registrado.</td></tr>`;
        return;
    }

    historial.forEach(c => {
        const estadoInfo   = _resolverEstado(c);
        const esCumplida   = _citaEsCumplida(c);
        const yaCompletada = _citaEncuestaCompletada(c);

        // Celda Reporte: solo si la cita fue cumplida
        let reporteCelda = '<span class="text-slate-300 text-[10px] font-bold">—</span>';
        if (esCumplida) {
            reporteCelda = _htmlBotonReporte(c.Cita_ID);
        }

        // Celda Encuesta
        let encuestaCelda = '<span class="text-slate-300 text-[10px] font-bold">—</span>';
        if (esCumplida) {
            if (yaCompletada) {
                encuestaCelda = `
                    <button disabled
                        class="btn-encuesta-completada text-[10px] bg-green-50 text-green-600 border border-green-200 px-4 py-2 rounded-xl font-black uppercase cursor-not-allowed opacity-80">
                        <i class="fas fa-check-circle mr-1"></i> Completada
                    </button>`;
            } else {
                encuestaCelda = `
                    <button onclick="abrirModalEncuesta(${c.Cita_ID})"
                        class="btn-encuesta-pendiente text-[10px] bg-orange-50 text-orange-500 border border-orange-200 px-4 py-2 rounded-xl font-black hover:bg-orange-100 transition-all uppercase">
                        <i class="fas fa-star mr-1"></i> Encuesta
                    </button>`;
            }
        }

        const tr = document.createElement('tr');
        tr.id = `historial-row-${c.Cita_ID}`;
        tr.setAttribute('data-cita-id', c.Cita_ID);
        tr.innerHTML = `
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs text-slate-600">Dr(a). ${c.NombreEspecialista || '—'}</td>
            <td class="p-5">
                <span class="badge-estado-cita text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}">
                    ${estadoInfo.label}
                </span>
            </td>
            <td class="p-5 text-center">
                <span class="text-[10px] font-bold text-slate-400">${c.Motivo_Consulta || '—'}</span>
            </td>
            <td class="p-5 text-center celda-reporte">${reporteCelda}</td>
            <td class="p-5 text-center">${encuestaCelda}</td>`;
        tbody.appendChild(tr);
    });
}

// ─── MODAL REPORTE CLÍNICO (SOLO LECTURA PARA PACIENTE) ──────────────────────
function _formatearHoraAmPm(horaStr) {
    if (!horaStr || horaStr === '—') return horaStr || '—';
    const partes = horaStr.split(':');
    let h = parseInt(partes[0], 10);
    const m = partes[1] || '00';
    const ampm = h >= 12 ? 'P.M.' : 'A.M.';
    h = h % 12 || 12;
    return `${String(h).padStart(2, '0')}:${m} ${ampm}`;
}

function _setBox(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (val !== undefined && val !== null && String(val).trim() !== '') ? String(val).trim() : '—';
}

function _setArea(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    const FALLBACKS = {
        'rp-diagnostico': 'Sin diagnóstico registrado',
        'rp-evolucion':   'Sin evolución registrada',
        'rp-tratamiento': 'Sin plan de tratamiento registrado',
    };
    el.value = (val !== undefined && val !== null && String(val).trim() !== '')
        ? String(val).trim()
        : (FALLBACKS[id] || '—');
}

function _descomprimirEvolucionTratamiento(desc) {
    desc = (desc || '').trim();
    if (!desc) return ['', ''];
    if (desc.includes('---')) {
        const partes = desc.split('---');
        return [partes[0].trim(), partes.slice(1).join('---').trim()];
    }
    return [desc, desc];
}

function _leerCampoFlexible(obj, ...claves) {
    if (!obj) return undefined;
    for (const clave of claves) {
        if (obj[clave] !== undefined && obj[clave] !== null) return obj[clave];
    }
    return undefined;
}

window.abrirReportePaciente = async function (citaId) {
    const modal = document.getElementById('modalReportePaciente');
    if (!modal) return;

    // Limpiar y mostrar estado de carga
    _setBox('rp-nombre',       '');
    _setBox('rp-tipo-doc',     '');
    _setBox('rp-num-doc',      '');
    _setBox('rp-motivo',       '');
    _setBox('rp-fecha',        '');
    _setBox('rp-hora',         '');
    _setBox('rp-especialista', '');
    _setArea('rp-diagnostico', null);
    _setArea('rp-evolucion',   null);
    _setArea('rp-tratamiento', null);

    const msgCargando = document.getElementById('rp-msg-cargando');
    const msgVacio    = document.getElementById('rp-msg-vacio');
    if (msgCargando) msgCargando.style.display = 'block';
    if (msgVacio)    msgVacio.style.display    = 'none';

    modal.style.display = 'flex';

    // Datos de caché local
    const citaLocal = _citasData.find(c => c.Cita_ID === citaId);
    if (citaLocal) {
        _setBox('rp-nombre',       citaLocal.NombrePaciente   || '—');
        _setBox('rp-num-doc',      citaLocal.NumeroDocumento  || '—');
        _setBox('rp-motivo',       citaLocal.Motivo_Consulta  || '—');
        _setBox('rp-fecha',        citaLocal.Fecha            || '—');
        _setBox('rp-hora',         _formatearHoraAmPm(citaLocal.Hora_Inicio));
        _setBox('rp-especialista', citaLocal.NombreEspecialista ? `Dr(a). ${citaLocal.NombreEspecialista}` : '—');
    }

    try {
        // Fuente primaria
        const res = await fetch(`/api/historial/cita/${citaId}?_=${Date.now()}`, { cache: 'no-store' });
        if (msgCargando) msgCargando.style.display = 'none';

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.ok || !data.data) {
            if (msgVacio) msgVacio.style.display = 'block';
            return;
        }

        const d = data.data;

        // Datos del paciente desde el backend
        const nombre      = _leerCampoFlexible(d, 'NombrePaciente', 'nombre_paciente') || (citaLocal && citaLocal.NombrePaciente) || '—';
        const tipoDoc     = _leerCampoFlexible(d, 'TipoDocumento')  || (citaLocal && citaLocal.TipoDocumento)  || '';
        const numDoc      = _leerCampoFlexible(d, 'NumeroDocumento') || (citaLocal && citaLocal.NumeroDocumento) || '—';
        const motivo      = _leerCampoFlexible(d, 'Motivo_Consulta', 'MotivoHC') || (citaLocal && citaLocal.Motivo_Consulta) || '—';
        const fecha       = _leerCampoFlexible(d, 'Fecha')       || (citaLocal && citaLocal.Fecha)       || '—';
        const horaCruda   = _leerCampoFlexible(d, 'Hora_Inicio') || (citaLocal && citaLocal.Hora_Inicio) || '—';
        const especialista = _leerCampoFlexible(d, 'NombreEspecialista') || (citaLocal && citaLocal.NombreEspecialista) || '—';

        _setBox('rp-nombre',       nombre);
        _setBox('rp-tipo-doc',     tipoDoc);
        _setBox('rp-num-doc',      numDoc);
        _setBox('rp-motivo',       motivo);
        _setBox('rp-fecha',        fecha);
        _setBox('rp-hora',         _formatearHoraAmPm(horaCruda));
        _setBox('rp-especialista', especialista && especialista !== '—' ? `Dr(a). ${especialista}` : '—');

        // Campos clínicos
        const diagVal   = _leerCampoFlexible(d, 'diagnostico', 'Diagnostico', 'diagnostico_texto');
        const tratRaw   = _leerCampoFlexible(d, 'tratamiento', 'Tratamiento', 'tratamiento_texto') || '';
        const evoVal    = _leerCampoFlexible(d, 'evolucion', 'Evolucion', 'evolucion_clinica', 'evolucion_texto');

        const [evolucionFinal, tratamientoFinal] = _descomprimirEvolucionTratamiento(tratRaw);
        const diagnosticoFinal = diagVal !== undefined ? diagVal : '';
        const evolucionReal    = (evoVal !== undefined && evoVal !== null && String(evoVal).trim()) ? evoVal : evolucionFinal;
        const tratamientoReal  = tratamientoFinal;

        _setArea('rp-diagnostico', diagnosticoFinal);
        _setArea('rp-evolucion',   evolucionReal);
        _setArea('rp-tratamiento', tratamientoReal);

        // Mostrar mensaje si no hay datos clínicos
        const hayDatos = diagnosticoFinal || evolucionReal || tratamientoReal;
        if (!hayDatos && msgVacio) msgVacio.style.display = 'block';

    } catch (err) {
        console.error('[paciente] Error cargando reporte:', err);
        if (msgCargando) msgCargando.style.display = 'none';
        if (msgVacio)    msgVacio.style.display    = 'block';
    }
};

window.cerrarModalReportePaciente = function () {
    const modal = document.getElementById('modalReportePaciente');
    if (modal) modal.style.display = 'none';
};

// ─── RENDER MULTAS DEL PACIENTE (SOLO LECTURA) ───────────────────────────────
async function _renderMultasPaciente() {
    const tbody = document.getElementById('tabla-multas-paciente-body');
    const noMsg = document.getElementById('no-multas-msg');
    if (!tbody || !_pacienteId) return;

    tbody.innerHTML = '<tr><td colspan="6" class="p-6 text-center text-slate-400 text-xs">Cargando...</td></tr>';

    try {
        const res  = await fetch(`/api/multas/paciente/${_pacienteId}`);
        const data = await res.json();
        const lista = data.ok ? _normalizar(data) : [];

        tbody.innerHTML = '';

        if (lista.length === 0) {
            noMsg?.classList.remove('hidden');
            return;
        }
        noMsg?.classList.add('hidden');

        lista.forEach(m => {
            const pagada = m.EstadoMulta_ID === 2;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-5 text-xs font-black text-slate-500">#${m.Multa_ID}</td>
                <td class="p-5 text-xs text-slate-600">${m.Concepto || '—'}</td>
                <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${m.Nombre_Especialidad || '—'}</td>
                <td class="p-5 text-xs font-bold">${m.Fecha || '—'}<br><span class="text-slate-400">${m.Hora_Inicio || ''}</span></td>
                <td class="p-5 text-xs text-slate-600">Dr(a). ${m.NombreEspecialista || '—'}</td>
                <td class="p-5 text-center">
                    <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full ${pagada ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 'bg-amber-100 text-amber-700 border border-amber-200'}">
                        ${m.EstadoMulta || '—'}
                    </span>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('[paciente] Error cargando multas:', err);
        tbody.innerHTML = '<tr><td colspan="6" class="p-6 text-center text-red-400 text-xs font-bold">Error al cargar multas.</td></tr>';
    }
}

window.abrirModalPagarMulta = function (multaId) {
    const modal = document.getElementById('modalPagarMulta');
    if (!modal) return;
    modal.dataset.multaId  = multaId;
    modal.style.display    = 'flex';
};

window.cerrarModalPagarMulta = function () {
    const modal = document.getElementById('modalPagarMulta');
    if (modal) modal.style.display = 'none';
};

window.confirmarPagoMulta = async function () {
    const modal   = document.getElementById('modalPagarMulta');
    const multaId = modal?.dataset.multaId;
    if (!multaId) return;

    try {
        const res  = await fetch(`/api/multas/${multaId}/pagar`, { method: 'PUT' });
        const data = await res.json();
        cerrarModalPagarMulta();
        if (data.ok) {
            _mostrarNotificacion('Multa Pagada', 'La multa fue marcada como pagada correctamente.', 'success');
            _renderMultasPaciente();
        } else {
            _mostrarNotificacion('Error', data.error || 'No se pudo registrar el pago.', 'error');
        }
    } catch (err) {
        cerrarModalPagarMulta();
        _mostrarNotificacion('Error de Conexión', 'No se pudo conectar al servidor.', 'error');
    }
};

// ─── MODAL ENCUESTA ───────────────────────────────────────────────────────────
window.abrirModalEncuesta = async function (citaId) {
    _encuestaCitaId    = citaId;
    _encuestaPreguntas = [];

    const container = document.getElementById('encuesta-preguntas-container');
    const errEl     = document.getElementById('encuesta-error');
    if (container) container.innerHTML = '<p class="text-center text-slate-400 text-xs font-bold py-6">Cargando preguntas...</p>';
    if (errEl)     errEl.style.display = 'none';

    document.getElementById('modalEncuesta').style.display = 'flex';

    try {
        const res  = await fetch('/api/pregunta?activas=true');
        const data = await res.json();

        if (!data.ok || !Array.isArray(data.data) || data.data.length === 0) {
            if (container) container.innerHTML = '<p class="text-center text-slate-400 text-xs font-bold py-6">No hay preguntas de evaluación configuradas.</p>';
            return;
        }

        _encuestaPreguntas = data.data;
        _renderPreguntasEncuesta(container, _encuestaPreguntas);

    } catch (err) {
        console.error('[encuesta] Error cargando preguntas:', err);
        if (container) container.innerHTML = '<p class="text-center text-red-400 text-xs font-bold py-6">Error al cargar preguntas. Intente de nuevo.</p>';
    }
};

function _renderPreguntasEncuesta(container, preguntas) {
    container.innerHTML = '';
    preguntas.forEach((p, idx) => {
        const bloque = document.createElement('div');
        bloque.className          = 'encuesta-pregunta-bloque';
        bloque.dataset.preguntaId = p.ID_Pregunta;

        bloque.innerHTML = `
            <p class="text-[11px] font-black text-slate-700 uppercase tracking-wider mb-3">
                <span class="text-orange-400 mr-1">${idx + 1}.</span>${p.Texto_Pregunta}
            </p>
            <div class="encuesta-estrellas flex gap-2 items-center" data-pregunta="${p.ID_Pregunta}">
                ${[1,2,3,4,5].map(v => `
                    <button type="button"
                        class="estrella-btn text-3xl text-slate-300 hover:text-orange-400 transition-colors focus:outline-none"
                        data-valor="${v}" aria-label="Calificación ${v} de 5" title="${v} estrella${v > 1 ? 's' : ''}">
                        ☆
                    </button>`).join('')}
                <span class="text-[10px] text-slate-400 font-bold ml-2 estrella-label">Sin calificar</span>
            </div>`;

        const estrellasWrap = bloque.querySelector('.encuesta-estrellas');
        const botones       = estrellasWrap.querySelectorAll('.estrella-btn');
        const label         = estrellasWrap.querySelector('.estrella-label');

        botones.forEach(btn => {
            btn.addEventListener('click', function () {
                const val = parseInt(this.dataset.valor);
                estrellasWrap.dataset.seleccionado = val;
                botones.forEach((b, i) => {
                    b.textContent = i < val ? '★' : '☆';
                    b.classList.toggle('text-orange-400', i < val);
                    b.classList.toggle('text-slate-300',  i >= val);
                });
                const textos = ['Muy malo', 'Malo', 'Regular', 'Bueno', 'Excelente'];
                if (label) label.textContent = textos[val - 1] || '';
            });
        });

        container.appendChild(bloque);
    });
}

window.cerrarModalEncuesta = function () {
    document.getElementById('modalEncuesta').style.display = 'none';
    _encuestaCitaId    = null;
    _encuestaPreguntas = [];
};

window.enviarEncuesta = async function () {
    const container = document.getElementById('encuesta-preguntas-container');
    const errEl     = document.getElementById('encuesta-error');
    if (errEl) errEl.style.display = 'none';

    const bloques      = container ? container.querySelectorAll('.encuesta-pregunta-bloque') : [];
    const respuestas   = [];
    let todoRespondido = true;

    bloques.forEach(bloque => {
        const pid  = parseInt(bloque.dataset.preguntaId);
        const wrap = bloque.querySelector('.encuesta-estrellas');
        const val  = wrap ? parseInt(wrap.dataset.seleccionado || '0') : 0;
        if (!val || val < 1 || val > 5) {
            todoRespondido = false;
        } else {
            respuestas.push({ ID_Pregunta: pid, Texto_Respuesta: String(val) });
        }
    });

    if (!todoRespondido) {
        if (errEl) {
            errEl.textContent   = '⚠ Por favor califica todas las preguntas antes de enviar.';
            errEl.style.display = 'block';
        }
        return;
    }

    const btnEnviar = document.getElementById('btn-enviar-encuesta');
    if (btnEnviar) { btnEnviar.disabled = true; btnEnviar.textContent = 'Enviando...'; }

    const citaIdEnviada = _encuestaCitaId;

    try {
        for (const r of respuestas) {
            const res = await fetch('/api/respuesta', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    ID_Pregunta:     r.ID_Pregunta,
                    ID_Paciente:     _pacienteId,
                    Texto_Respuesta: r.Texto_Respuesta,
                    Cita_ID:         citaIdEnviada,
                }),
            });
            const data = await res.json();
            if (!data.ok) throw new Error(data.error || 'Error al enviar una respuesta.');
        }

        const citaLocal = _citasData.find(c => c.Cita_ID === citaIdEnviada);
        if (citaLocal) {
            citaLocal.Encuesta_Completada = 1;
            citaLocal.Encuesta_Enviada    = 1;
        }

        _actualizarBotonEncuestaEnDOM(citaIdEnviada);
        cerrarModalEncuesta();
        _mostrarModalExitoEncuesta();

    } catch (err) {
        console.error('[encuesta] Error enviando respuestas:', err);
        if (errEl) {
            errEl.textContent   = err.message || 'Error de conexión. Intente de nuevo.';
            errEl.style.display = 'block';
        }
    } finally {
        if (btnEnviar) {
            btnEnviar.disabled  = false;
            btnEnviar.innerHTML = '<i class="fas fa-paper-plane mr-2"></i> Enviar Encuesta';
        }
    }
};

function _actualizarBotonEncuestaEnDOM(citaId) {
    const row = document.getElementById(`historial-row-${citaId}`);
    if (!row) return;
    const celdaEncuesta = row.querySelector('td:last-child');
    if (!celdaEncuesta) return;
    celdaEncuesta.innerHTML = `
        <button disabled
            class="btn-encuesta-completada text-[10px] bg-green-50 text-green-600 border border-green-200 px-4 py-2 rounded-xl font-black uppercase cursor-not-allowed opacity-80">
            <i class="fas fa-check-circle mr-1"></i> Completada
        </button>`;
}

function _mostrarModalExitoEncuesta() {
    const modal = document.getElementById('modalEncuestaExito');
    const bar   = document.getElementById('encuesta-exito-bar');
    if (!modal) return;

    modal.style.display = 'flex';
    if (bar) {
        bar.style.transition = 'none';
        bar.style.width      = '100%';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                bar.style.transition = 'width 3s linear';
                bar.style.width      = '0%';
            });
        });
    }

    if (_encuestaExitoTimer) clearTimeout(_encuestaExitoTimer);
    _encuestaExitoTimer = setTimeout(() => {
        modal.style.display = 'none';
        _encuestaExitoTimer = null;
    }, 3000);
}

// ─── CANCELAR CITA ────────────────────────────────────────────────────────────
function _calcularMinutosRestantes(fecha, horaInicio) {
    try {
        const citaDateTime = new Date(`${fecha}T${horaInicio}`);
        return (citaDateTime - new Date()) / 60000;
    } catch {
        return Infinity;
    }
}

function _formatearTiempoRestante(minutos) {
    if (minutos <= 0) return '0 minutos';
    const h = Math.floor(minutos / 60);
    const m = Math.round(minutos % 60);
    if (h > 0) return `${h}h ${m}min`;
    return `${m} minutos`;
}

window.abrirModalCancelar = function (citaId) {
    _citaParaCancelar = citaId;
    const cita = _citasData.find(c => c.Cita_ID === citaId);
    if (!cita) return;

    const detalles = document.getElementById('detalles-completos');
    if (detalles) {
        detalles.innerHTML = `
            <div class="col-span-2 bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Especialidad</p>
                <p class="font-black text-slate-700 text-sm">${cita.Nombre_Especialidad || '—'}</p>
            </div>
            <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Fecha</p>
                <p class="font-bold text-slate-700 text-sm">${cita.Fecha}</p>
            </div>
            <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Hora</p>
                <p class="font-bold text-slate-700 text-sm">${cita.Hora_Inicio || '—'}</p>
            </div>
            <div class="col-span-2 bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Especialista</p>
                <p class="font-bold text-slate-700 text-sm">Dr(a). ${cita.NombreEspecialista || '—'}</p>
            </div>`;
    }

    document.getElementById('modalCancelarCita').style.display = 'flex';
};

window.cerrarModalCancelar = function () {
    document.getElementById('modalCancelarCita').style.display = 'none';
    _citaParaCancelar = null;
    _cancelarConMulta = false;
};

window.solicitarConfirmacionFinal = function () {
    document.getElementById('modalCancelarCita').style.display = 'none';
    const cita = _citasData.find(c => c.Cita_ID === _citaParaCancelar);
    if (!cita) return;

    const minutosRestantes = _calcularMinutosRestantes(cita.Fecha, cita.Hora_Inicio);

    if (minutosRestantes <= 120) {
        _cancelarConMulta = true;
        const tiempoEl = document.getElementById('tiempo-restante-multa');
        if (tiempoEl) tiempoEl.textContent = _formatearTiempoRestante(minutosRestantes);
        document.getElementById('modalAdvertenciaMulta').style.display = 'flex';
    } else {
        _cancelarConMulta = false;
        document.getElementById('modalConfirmacionFinal').style.display = 'flex';
    }
};

window.cerrarModalAdvertenciaMulta = function () {
    document.getElementById('modalAdvertenciaMulta').style.display = 'none';
    _citaParaCancelar = null;
    _cancelarConMulta = false;
};

window.confirmarCancelacionConMulta = function () {
    document.getElementById('modalAdvertenciaMulta').style.display = 'none';
    document.getElementById('modalConfirmacionFinal').style.display = 'flex';
};

window.cerrarConfirmacionFinal = function () {
    document.getElementById('modalConfirmacionFinal').style.display = 'none';
    _cancelarConMulta = false;
};

window.confirmarAccionCancelado = async function () {
    if (!_citaParaCancelar) return;
    try {
        const url  = _cancelarConMulta
            ? `/api/citas/${_citaParaCancelar}/cancelar-con-multa`
            : `/api/citas/${_citaParaCancelar}/cancelar-sin-multa`;

        const res  = await fetch(url, { method: 'PUT' });
        const data = await res.json();
        document.getElementById('modalConfirmacionFinal').style.display = 'none';

        const conMulta = _cancelarConMulta;
        _citaParaCancelar = null;
        _cancelarConMulta = false;

        if (data.ok) {
            await _cargarCitasPaciente();
            if (conMulta) {
                _mostrarNotificacion('Cita Cancelada con Multa', 'Su cita fue cancelada. Se generó una multa pendiente de pago.', 'info');
            } else {
                _mostrarNotificacion('Cita Cancelada', 'Su cita fue cancelada exitosamente sin penalización.', 'success');
            }
        } else {
            _mostrarNotificacion('Error', data.error || 'No se pudo cancelar la cita.', 'error');
        }
    } catch (err) {
        console.error('[paciente] Error cancelando cita:', err);
        _mostrarNotificacion('Error de Conexión', 'No se pudo conectar al servidor. Intente de nuevo.', 'error');
    }
};

// ─── VISIBILIDAD DE CONTRASEÑA ────────────────────────────────────────────────
window.togglePassVisibility = function (inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) { icon.classList.remove('fa-eye'); icon.classList.add('fa-eye-slash'); }
    } else {
        input.type = 'password';
        if (icon) { icon.classList.remove('fa-eye-slash'); icon.classList.add('fa-eye'); }
    }
};

// ─── VALIDACIÓN POLÍTICA DE CONTRASEÑA ───────────────────────────────────────
function _cumpleRequisitos(pass) {
    return {
        length:  pass.length >= 8,
        upper:   /[A-Z]/.test(pass),
        lower:   /[a-z]/.test(pass),
        number:  /[0-9]/.test(pass),
        special: /[^A-Za-z0-9]/.test(pass),
    };
}

window.validarRequisitosEnTiempoReal = function () {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitos(pass);
    _aplicarEstadoRequisito('req-length',  res.length,  false);
    _aplicarEstadoRequisito('req-upper',   res.upper,   false);
    _aplicarEstadoRequisito('req-lower',   res.lower,   false);
    _aplicarEstadoRequisito('req-number',  res.number,  false);
    _aplicarEstadoRequisito('req-special', res.special, false);
};

function _aplicarEstadoRequisito(id, cumple, marcarRojo) {
    const el = document.getElementById(id);
    if (!el) return;
    const icon = el.querySelector('.req-icon');
    if (cumple) {
        el.className = 'req-item req-ok';
        if (icon) icon.textContent = '✓';
    } else if (marcarRojo) {
        el.className = 'req-item req-error';
        if (icon) icon.textContent = '-';
    } else {
        el.className = 'req-item req-pending';
        if (icon) icon.textContent = '-';
    }
}

function _marcarRequisitosIncumplidos() {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitos(pass);
    _aplicarEstadoRequisito('req-length',  res.length,  !res.length);
    _aplicarEstadoRequisito('req-upper',   res.upper,   !res.upper);
    _aplicarEstadoRequisito('req-lower',   res.lower,   !res.lower);
    _aplicarEstadoRequisito('req-number',  res.number,  !res.number);
    _aplicarEstadoRequisito('req-special', res.special, !res.special);
    return res.length && res.upper && res.lower && res.number && res.special;
}

// ─── MI PERFIL — CARGA DE SELECTS EPS ────────────────────────────────────────
let _listaEpsGlobal     = [];
let _listaRegimenGlobal = [];
let _listaTipoEpsGlobal = [];

async function _cargarSelectsEps() {
    try {
        const [resEps, resRegimen, resTipo] = await Promise.all([
            fetch('/api/eps'),
            fetch('/api/regimen-eps'),
            fetch('/api/tipo-eps'),
        ]);

        _listaEpsGlobal     = _normalizar(resEps.ok     ? await resEps.json()     : []);
        _listaRegimenGlobal = _normalizar(resRegimen.ok ? await resRegimen.json() : []);
        _listaTipoEpsGlobal = _normalizar(resTipo.ok    ? await resTipo.json()    : []);

        const selRegimen = document.getElementById('edit-regimen-eps');
        if (selRegimen) {
            selRegimen.innerHTML = '<option value="">Seleccione Régimen...</option>';
            _listaRegimenGlobal.forEach(r => {
                const id  = r.Regimen_ID || r.ID_Regimen_EPS || r.regimen_id;
                const nom = r.Descripcion || r.Nombre_Regimen || r.nombre_regimen || '';
                const opt = document.createElement('option');
                opt.value = id; opt.textContent = nom;
                selRegimen.appendChild(opt);
            });
        }

        const selTipo = document.getElementById('edit-tipo-eps');
        if (selTipo) {
            selTipo.innerHTML = '<option value="">Seleccione Tipo EPS...</option>';
            _listaTipoEpsGlobal.forEach(t => {
                const id  = t.TipoEPS_ID || t.ID_Tipo_EPS || t.tipoeps_id;
                const nom = t.Nombre_Tipo || t.nombre_tipo || t.Nombre || '';
                const opt = document.createElement('option');
                opt.value = id; opt.textContent = nom;
                selTipo.appendChild(opt);
            });
        }

        const selEps = document.getElementById('edit-eps');
        if (selEps) {
            selEps.innerHTML = '<option value="">Seleccione EPS...</option>';
            _listaEpsGlobal.forEach(e => {
                const id  = e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS;
                const nom = e.Nombre_EPS || e.nombre_eps || e.Nombre || '';
                const opt = document.createElement('option');
                opt.value = id; opt.textContent = nom;
                selEps.appendChild(opt);
            });
        }

    } catch (err) {
        console.warn('[perfil] Error cargando selects EPS:', err);
    }
}

// ─── MI PERFIL — PRECARGA ────────────────────────────────────────────────────
async function _precargarPerfil() {
    if (!_usuarioId) return;
    _resetearFlujoPassword();

    try {
        const resUser = await fetch(`/api/usuarios/${_usuarioId}`);
        if (resUser.ok) {
            const userData = await resUser.json();
            if (userData) {
                _sesionPaciente = { ..._sesionPaciente, ...userData };
                sessionStorage.setItem('odent_usuario', JSON.stringify(_sesionPaciente));
            }
        }
    } catch (err) {
        console.warn('[perfil] No se pudo refrescar datos de usuario:', err);
    }

    const u = _sesionPaciente;
    _setVal('edit-nombres',  `${u.Nombres || ''} ${u.Apellidos || ''}`.trim());
    _setVal('edit-correo',   u.Correo   || '');
    _setVal('edit-telefono', u.Telefono || '');

    await _cargarSelectsEps();

    try {
        const resAfil = await fetch('/api/afiliacion');
        if (resAfil.ok) {
            const rawAfil  = await resAfil.json();
            const dataAfil = _normalizar(rawAfil);
            const afil = dataAfil.find(
                a => String(a.Usuario_ID || a.ID_Usuario) === String(_usuarioId)
            );
            if (afil) {
                const epsId     = afil.EPS_ID     || afil.Id_EPS     || afil.eps_id     || '';
                const tipoEpsId = afil.TipoEPS_ID || afil.ID_Tipo_EPS || afil.tipoeps_id || '';

                let regimenIdActual = '';
                if (epsId) {
                    const epsObj = _listaEpsGlobal.find(e =>
                        String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId)
                    );
                    if (epsObj) {
                        regimenIdActual = String(
                            epsObj.Regimen_ID || epsObj.regimen_id || epsObj.ID_Regimen_EPS || ''
                        );
                    }
                }

                const selRegimen = document.getElementById('edit-regimen-eps');
                const selEps     = document.getElementById('edit-eps');
                const selTipo    = document.getElementById('edit-tipo-eps');
                if (selRegimen && regimenIdActual) selRegimen.value = regimenIdActual;
                if (selEps     && epsId)           selEps.value     = String(epsId);
                if (selTipo    && tipoEpsId)       selTipo.value    = String(tipoEpsId);
            }
        }
    } catch (err) {
        console.warn('[perfil] Error precargando afiliación:', err);
    }

    const selEps = document.getElementById('edit-eps');
    if (selEps) {
        const selEpsNuevo = selEps.cloneNode(true);
        selEps.parentNode.replaceChild(selEpsNuevo, selEps);
        selEpsNuevo.addEventListener('change', function () {
            _sugerirRegimenSegunEps(this.value);
        });
    }
}

function _sugerirRegimenSegunEps(epsId) {
    const selRegimen = document.getElementById('edit-regimen-eps');
    if (!selRegimen || !epsId) return;
    const epsObj = _listaEpsGlobal.find(e =>
        String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId)
    );
    if (!epsObj) return;
    const regimenId = epsObj.Regimen_ID || epsObj.regimen_id || epsObj.ID_Regimen_EPS || null;
    if (regimenId) selRegimen.value = String(regimenId);
}

function _resetearFlujoPassword() {
    ['pass-actual', 'conf-pass-nueva', 'conf-pass-confirmar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.value = ''; el.type = 'password'; }
    });
    document.querySelectorAll('.pass-toggle-btn i').forEach(icon => {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    });
    const step1 = document.getElementById('pass-step1');
    const step2 = document.getElementById('pass-step2');
    if (step1) step1.style.display = '';
    if (step2) step2.style.display = 'none';
    ['error-pass-actual', 'error-pass-nueva'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    ['req-length', 'req-upper', 'req-lower', 'req-number', 'req-special'].forEach(id => {
        _aplicarEstadoRequisito(id, false, false);
    });
}

window.validarPasswordActual = function () {
    const inputActual = document.getElementById('pass-actual');
    const errActual   = document.getElementById('error-pass-actual');
    const step1       = document.getElementById('pass-step1');
    const step2       = document.getElementById('pass-step2');

    if (!inputActual?.value.trim()) {
        if (errActual) { errActual.textContent = 'Ingresa tu contraseña actual.'; errActual.style.display = 'block'; }
        return;
    }

    fetch('/api/verificar-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ password: inputActual.value, usuario_id: _usuarioId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (errActual) errActual.style.display = 'none';
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = '';
        } else {
            document.getElementById('modalErrorPassword').style.display = 'flex';
        }
    })
    .catch(() => _mostrarNotificacion('Error de Conexión', 'No se pudo verificar la contraseña.', 'error'));
};

// ─── GUARDAR PERFIL ───────────────────────────────────────────────────────────
window.guardarPerfilPaciente = function () {
    const nombreCompleto = (document.getElementById('edit-nombres')?.value || '').trim();
    const partes         = nombreCompleto.split(/\s+/);
    const mitad          = Math.ceil(partes.length / 2);
    const nombres        = partes.slice(0, mitad).join(' ');
    const apellidos      = partes.slice(mitad).join(' ');

    const correo     = (document.getElementById('edit-correo')?.value   || '').trim();
    const telefono   = (document.getElementById('edit-telefono')?.value || '').trim();
    const passActual = document.getElementById('pass-actual')?.value         || '';
    const passNueva  = document.getElementById('conf-pass-nueva')?.value     || '';
    const passConf   = document.getElementById('conf-pass-confirmar')?.value || '';
    const errActual  = document.getElementById('error-pass-actual');
    const errNueva   = document.getElementById('error-pass-nueva');
    const step2      = document.getElementById('pass-step2');

    const selEps     = document.getElementById('edit-eps');
    const selTipoEps = document.getElementById('edit-tipo-eps');
    const regimenEl  = document.getElementById('edit-regimen-eps');

    const epsId     = selEps     ? (selEps.value     || null) : null;
    const tipoEpsId = selTipoEps ? (selTipoEps.value || null) : null;
    const regimenId = regimenEl  ? (regimenEl.value  || null) : null;

    const cambiandoPassword = step2?.style.display !== 'none' && !!passNueva;

    if (cambiandoPassword) {
        const todosOk = _marcarRequisitosIncumplidos();
        if (!todosOk) return;
        if (passNueva !== passConf) {
            if (errNueva) errNueva.style.display = 'block';
            return;
        }
        if (!passActual.trim()) {
            if (errActual) {
                errActual.textContent  = 'Ingresa tu contraseña actual para poder cambiarla.';
                errActual.style.display = 'block';
            }
            return;
        }
    }
    if (errNueva)  errNueva.style.display  = 'none';
    if (errActual) errActual.style.display = 'none';

    const payload = {
        usuario_id:        _usuarioId,
        nombres:           nombres   || undefined,
        apellidos:         apellidos || undefined,
        correo:            correo    || undefined,
        telefono:          telefono  || undefined,
        nuevaPass:         cambiandoPassword ? passNueva  : null,
        contrasena_actual: cambiandoPassword ? passActual : null,
        eps_id:            epsId     ? parseInt(epsId)     : null,
        tipo_eps_id:       tipoEpsId ? parseInt(tipoEpsId) : null,
        regimen_id:        regimenId ? parseInt(regimenId) : null,
    };

    fetch('/api/actualizar-perfil-paciente', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
    })
    .then(async r => {
        const data = await r.json().catch(() => ({}));
        if (data.ok) {
            if (_sesionPaciente) {
                if (nombres)   _sesionPaciente.Nombres   = nombres;
                if (apellidos) _sesionPaciente.Apellidos = apellidos;
                if (correo)    _sesionPaciente.Correo    = correo;
                if (telefono)  _sesionPaciente.Telefono  = telefono;
                sessionStorage.setItem('odent_usuario', JSON.stringify(_sesionPaciente));
            }
            _cargarSesion();
            cambiarVista('inicio');
            _mostrarNotificacion('Perfil Actualizado', 'Tus datos han sido guardados correctamente.', 'success');
        } else if (r.status === 401 && cambiandoPassword) {
            if (errActual) {
                errActual.textContent   = data.error || 'Contraseña actual incorrecta.';
                errActual.style.display = 'block';
            }
        } else {
            _mostrarNotificacion('Error', data.mensaje || data.error || 'No se pudo guardar. Intenta de nuevo.', 'error');
        }
    })
    .catch(() => _mostrarNotificacion('Error de Conexión', 'No se pudo guardar el perfil.', 'error'));
};

// ─── CONFIRMACIÓN SIMPLE ──────────────────────────────────────────────────────
window.mostrarConfirmacionSimple = function (mensaje, accion) {
    _accionPendienteSimple = accion;
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');
    if (texto) texto.textContent = mensaje;
    if (modal) modal.style.display = 'flex';
};

window.cerrarModalSimple = function () {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
    _accionPendienteSimple = '';
};

window.ejecutarAccionSimple = function () {
    if (_accionPendienteSimple === 'salir') {
        _detenerPolling();
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
    window.cerrarModalSimple();
};

// ─── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    _actualizarReloj();
    setInterval(_actualizarReloj, 1000);

    const fechaEl = document.getElementById('fecha-actual-paciente');
    if (fechaEl) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }).toUpperCase();
    }

    document.addEventListener('click', function (e) {
        const trigger  = document.getElementById('profile-trigger');
        const dropdown = document.getElementById('profile-dropdown');
        if (!trigger || !dropdown) return;
        if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
            _closeProfileDropdown();
        }
    });

    // Cerrar modal de reporte con clic fuera del contenido
    const modalReporte = document.getElementById('modalReportePaciente');
    if (modalReporte) {
        modalReporte.addEventListener('click', function (e) {
            if (e.target === modalReporte) cerrarModalReportePaciente();
        });
    }

    _cargarSesion();
    cambiarVista('inicio');
});