// especialista.js v14.3
// REQ 1: Fix maquetación inputs agenda — clase .has-value se sincroniza con CSS para ocultar texto nativo duplicado
// REQ 2: Automatización de multas por incumplimiento de horario (ping al backend)
// REQ 3: Conexión en tiempo real de agenda médica con vista de agendar (ya servida vía /api/agenda)
// REQ 4: Validación estricta de disponibilidades duplicadas — manejo de respuesta 409 del backend
// REQ 5: Conexión total de Historia Clínica — fix de endpoint roto (/en-proceso -> /atender) y redirección robusta
// REQ 6: Fix de registro de historial_bp sin url_prefix en app.py — la ruta /historial/paciente/<id>
//        ahora es alcanzable directamente. irAHistoriaClinica() resuelve Paciente_ID desde memoria
//        y como fallback desde /api/citas/<id> (servido por citas_bp con url_prefix='/api').
// REQ 7: Fix crítico de renderizado — irAHistoriaClinica() navega a /historial/paciente/<id>
//        que devuelve render_template HTML. Eliminada toda llamada fetch() que causaba
//        que el navegador mostrara JSON crudo en lugar de la vista visual.
// REQ 8 (v14.3): Separación total Vista / API en irAHistoriaClinica():
//        ▸ window.location.href → /historial/paciente/<id>?cita_id=<id>  (VISTA HTML)
//        ▸ fetch()              → /api/historial/...  o  /api/citas/...  (JSON solamente)
//        El navegador NUNCA visita un endpoint de API directamente.
'use strict';

let indexActualGlobal     = null;
let citaActualEmpezar     = null;
let historialTotal        = [];
let agendaEspecialista    = [];
let seccionActiva         = 'inicio';
let filtroActivoInicio    = 'todos';
let usuarioSesionActual   = null;
let slotPendienteEliminar = null;

// ─── TOAST ────────────────────────────────────────────────────────────────────
function mostrarToast(mensaje, tipo = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const colores = { success: 'bg-emerald-600', error: 'bg-red-600', info: 'bg-sky-600', warning: 'bg-amber-500' };
    const iconos  = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
    const toast   = document.createElement('div');
    toast.className = `flex items-center gap-4 px-6 py-4 rounded-2xl text-white text-sm font-bold shadow-2xl ${colores[tipo] || colores.info} animate-in`;
    toast.innerHTML = `<i class="fas ${iconos[tipo] || iconos.info} text-xl"></i><span>${mensaje}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(() => toast.remove(), 500);
    }, 3500);
}

// ─── UTILIDADES ───────────────────────────────────────────────────────────────
function mostrarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-oculta');
    el.classList.add('seccion-visible');
}
function ocultarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-visible');
    el.classList.add('seccion-oculta');
}

function filtrarTablaSeccion(tbodyId, query) {
    const q     = (query || '').toUpperCase().trim();
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    let visibles = 0;
    Array.from(tbody.getElementsByTagName('tr')).forEach(fila => {
        const coincide = fila.innerText.toUpperCase().includes(q);
        fila.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const mapNoData = { 'tabla-inicio': 'no-datos-inicio', 'tabla-agenda': 'no-datos-agenda', 'tabla-pacientes': 'no-datos-pacientes' };
    const noDataId  = mapNoData[tbodyId];
    if (noDataId) {
        const noDataEl = document.getElementById(noDataId);
        if (noDataEl) noDataEl.style.display = visibles > 0 ? 'none' : 'block';
    }
}

function _obtenerInicial(primerNombre) {
    const limpio = (primerNombre || '').trim();
    return limpio ? limpio.charAt(0).toUpperCase() : 'E';
}

// ─── SMART PICKERS ────────────────────────────────────────────────────────────
function dispararPicker(wrapper) {
    const input = wrapper.querySelector('input');
    if (!input) return;
    try { input.showPicker(); } catch (e) { input.focus(); input.click(); }
}

function actualizarPlaceholderVisual(input) {
    if (!input) return;
    const placeholder = document.getElementById(`${input.id}-placeholder`);
    const wrapper      = input.closest('.smart-picker-wrapper');
    if (input.value) {
        input.classList.add('has-value');
        if (placeholder) placeholder.style.display = 'none';
        if (wrapper) wrapper.classList.remove('input-error');
    } else {
        input.classList.remove('has-value');
        if (placeholder) placeholder.style.display = 'flex';
    }
}

function inicializarPlaceholdersAgenda() {
    ['agenda-fecha', 'agenda-hora-inicio', 'agenda-hora-fin'].forEach(id => {
        const input = document.getElementById(id);
        if (input) actualizarPlaceholderVisual(input);
    });
}

// ─── DROPDOWN DE PERFIL ───────────────────────────────────────────────────────
const toggleProfileDropdown = () => {
    const dp = document.getElementById('profile-dropdown');
    if (dp) dp.classList.toggle('show');
};
window.onclick = (e) => {
    const trig = document.getElementById('profile-trigger');
    const drop = document.getElementById('profile-dropdown');
    if (trig && drop && !trig.contains(e.target) && !drop.contains(e.target)) {
        drop.classList.remove('show');
    }
};

// ─── RELOJ ────────────────────────────────────────────────────────────────────
function actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();
    const horas = ahora.getHours();

    const el = document.getElementById('reloj');
    if (el) {
        const h    = ahora.getHours();
        const m    = String(ahora.getMinutes()).padStart(2, '0');
        const s    = String(ahora.getSeconds()).padStart(2, '0');
        const h12  = h % 12 || 12;
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

function formatearHoraAmPm(horaStr) {
    if (!horaStr || horaStr === '—') return horaStr || '—';
    const partes = horaStr.split(':');
    let h = parseInt(partes[0], 10);
    const m = partes[1] || '00';
    const ampm = h >= 12 ? 'P.M.' : 'A.M.';
    h = h % 12 || 12;
    return `${String(h).padStart(2,'0')}:${m} ${ampm}`;
}

// ─── SESIÓN ───────────────────────────────────────────────────────────────────
const cargarInfoSesion = () => {
    try {
        const raw = sessionStorage.getItem('odent_usuario');
        if (!raw) { window.location.replace('/login'); return; }
        const u = JSON.parse(raw);
        if (u.Rol_ID !== 2) { window.location.replace('/login'); return; }
        usuarioSesionActual = u;

        const nombreCompleto = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
        const inicial        = _obtenerInicial(u.Nombres);
        _inyectarCampo('doctor-nombre-display', nombreCompleto || 'Especialista');
        _inyectarCampo('doctor-avatar',         inicial);
        _inyectarCampo('avatar-grande',         inicial);
        _inyectarCampo('nombre-menu',           nombreCompleto || 'Especialista');

        if (u.Usuario_ID) _cargarPerfilRealDesdeBD(u.Usuario_ID);
    } catch (err) {
        console.error('[especialista] Error cargando sesión:', err);
        window.location.replace('/login');
    }
};

function _inyectarCampo(id, val, esInput = false) {
    const el = document.getElementById(id);
    if (!el) return;
    (esInput || el.tagName === 'INPUT' || el.tagName === 'SELECT')
        ? (el.value = val)
        : (el.innerText = val);
}

// ─── PERFIL REAL DESDE BD ─────────────────────────────────────────────────────
async function _cargarPerfilRealDesdeBD(usuarioId) {
    try {
        const res = await fetch(`/api/especialista/perfil/${usuarioId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data.ok || !data.perfil) throw new Error('Perfil no disponible');

        const p = data.perfil;

        if (usuarioSesionActual) {
            Object.assign(usuarioSesionActual, {
                Especialista_ID:     p.Especialista_ID     || usuarioSesionActual.Especialista_ID,
                Tarjeta_Profesional: p.Tarjeta_Profesional,
                Especialidad:        p.Especialidad,
                Correo:              p.Correo,
                Telefono:            p.Telefono,
                NumeroDocumento:     p.NumeroDocumento,
                TipoDocumento:       p.TipoDocumento,
                Nombres:             p.Nombres,
                Apellidos:           p.Apellidos,
            });
            sessionStorage.setItem('odent_usuario', JSON.stringify(usuarioSesionActual));
        }

        _inyectarCampo('doctor-nombre-display', p.NombreCompleto);
        _inyectarCampo('doctor-avatar',         _obtenerInicial(p.Nombres));
        _inyectarCampo('avatar-grande',         _obtenerInicial(p.Nombres));
        _inyectarCampo('nombre-menu',           p.NombreCompleto);
        _inyectarCampo('esp-menu',              p.Especialidad);
        _inyectarCampo('email-menu',            p.Correo);
        _inyectarCampo('tel-menu',              p.Telefono);
        _inyectarCampo('especialidad-menu',     p.Especialidad);
        _inyectarCampo('tarjeta-menu',          p.Tarjeta_Profesional);

        const docConcatenado = (p.TipoDocumento && p.NumeroDocumento && p.TipoDocumento !== '—' && p.NumeroDocumento !== '—')
            ? `${p.TipoDocumento}: ${p.NumeroDocumento}`
            : (p.NumeroDocumento || '—');
        _inyectarCampo('doc-menu-concat', docConcatenado);

        _inyectarCampo('conf-nombres',   p.Nombres,   true);
        _inyectarCampo('conf-apellidos', p.Apellidos, true);
        _inyectarCampo('conf-email',     p.Correo,    true);
        _inyectarCampo('conf-tel',       p.Telefono,  true);

    } catch (err) {
        console.warn('[especialista] No se pudo cargar el perfil real desde la BD:', err);
        mostrarToast('No se pudo cargar tu perfil desde el servidor.', 'warning');
    }
}

// ─── RESOLUCIÓN DE ESTADO ─────────────────────────────────────────────────────
function _resolverEstadoCita(c) {
    const ea = (c.EstadoAgenda || '').toLowerCase();
    if (ea === 'cancelado' || ea === 'cancelada') return 'Cancelada';
    if (ea === 'en proceso' || ea === 'atendiendo') return 'En proceso';
    if (ea === 'cumplida' || ea === 'atendido') return 'Atendido';
    if (c.FechaAtencion) return 'Atendido';
    return 'Pendiente';
}

function _esAtendidoHoy(cita) {
    if (cita.estado !== 'Atendido') return false;
    const hoy = new Date().toISOString().split('T')[0];
    if (cita.FechaAtencion) {
        const fechaAtencion = cita.FechaAtencion.split(' ')[0];
        return fechaAtencion === hoy;
    }
    return cita.fecha === hoy;
}

// ─── CARGA DE CITAS ───────────────────────────────────────────────────────────
const cargarDatosEspecialista = async () => {
    if (!usuarioSesionActual) return;
    const especialistaId = usuarioSesionActual.Especialista_ID || null;
    if (!especialistaId) { historialTotal = []; _renderTodas(); return; }

    try {
        const res = await fetch(`/api/especialista/${especialistaId}/citas`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (Array.isArray(data)) {
            historialTotal = data.map(c => ({
                Cita_ID:       c.Cita_ID,
                Paciente_ID:   c.Paciente_ID   || null,
                nombre:        c.NombrePaciente || '—',
                tipoDoc:       c.TipoDocumento  || 'DOC',
                numDoc:        c.NumeroDocumento || '—',
                telefono:      c.TelefonoPaciente || '—',
                especialidad:  c.Nombre_Especialidad || '—',
                hora:          c.Hora_Inicio    || '—',
                fecha:         c.Fecha          || '—',
                motivo:        c.Motivo_Consulta || '—',
                estado:        _resolverEstadoCita(c),
                EstadoAgenda:  c.EstadoAgenda,
                FechaAtencion: c.FechaAtencion  || null,
                evolucion:     c.evolucion      || '',
                prescripcion:  c.prescripcion   || '',
                cie10:         c.cie10          || '',
            }));
            _renderTodas();
            await _cargarAgendaEspecialista(especialistaId);
            return;
        }
    } catch (err) {
        console.warn('[especialista] Error cargando citas:', err);
        mostrarToast('No se pudo conectar con el servidor para cargar citas.', 'warning');
    }

    historialTotal = [];
    _renderTodas();
};

// ─── CARGA DE AGENDA ──────────────────────────────────────────────────────────
async function _cargarAgendaEspecialista(especialistaId) {
    try {
        const res = await fetch(`/api/agenda?especialista_id=${especialistaId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        agendaEspecialista = Array.isArray(data) ? data : [];
    } catch (err) {
        console.warn('[especialista] Error cargando agenda:', err);
        agendaEspecialista = [];
    }
    _renderTablaAgenda();
}

// ─── RENDER GLOBAL ────────────────────────────────────────────────────────────
function _renderTodas() {
    _actualizarStats();
    _renderTablaInicio(filtroActivoInicio);
    _renderTablaPacientes();
}

// ─── STATS ────────────────────────────────────────────────────────────────────
function _actualizarStats() {
    const hoy          = new Date().toISOString().split('T')[0];
    const noCanceladas = historialTotal.filter(c => c.estado !== 'Cancelada');
    const total        = noCanceladas.length;
    const pendientes   = noCanceladas.filter(c => c.estado === 'Pendiente').length;
    const atendidosHoy = noCanceladas.filter(c => _esAtendidoHoy(c)).length;

    const futuras = noCanceladas
        .filter(c => (c.estado === 'Pendiente' || c.estado === 'En proceso') && c.fecha >= hoy)
        .sort((a, b) => (a.fecha + a.hora).localeCompare(b.fecha + b.hora));
    const proxima = futuras[0] || null;

    const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.innerText = val; };
    setEl('stat-total',         total);
    setEl('stat-pendientes',    pendientes);
    setEl('stat-atendidos',     atendidosHoy);
    setEl('stat-proxima-hora',  proxima ? formatearHoraAmPm(proxima.hora) : '--:--');
    setEl('stat-proxima-fecha', proxima ? proxima.fecha : 'Sin citas');
}

// ─── RENDER TABLA INICIO ──────────────────────────────────────────────────────
function _renderTablaInicio(filtro) {
    filtroActivoInicio = filtro;
    const hoy    = new Date().toISOString().split('T')[0];
    const tbody  = document.getElementById('tabla-inicio');
    const titulo = document.getElementById('tabla-titulo-inicio');
    if (!tbody) return;

    const mapa = {
        todos:     { lista: historialTotal.filter(c => c.estado !== 'Cancelada'), titulo: 'Total Pacientes' },
        Pendiente: { lista: historialTotal.filter(c => c.estado === 'Pendiente'), titulo: 'Por Atender' },
        Atendido:  { lista: historialTotal.filter(c => _esAtendidoHoy(c)), titulo: 'Atendidos Hoy' },
        proxima:   {
            lista: (() => {
                const f = historialTotal.filter(c => (c.estado === 'Pendiente' || c.estado === 'En proceso') && c.fecha >= hoy)
                    .sort((a, b) => (a.fecha + a.hora).localeCompare(b.fecha + b.hora));
                return f.length > 0 ? [f[0]] : [];
            })(),
            titulo: 'Siguiente Cita'
        },
        'En proceso': { lista: historialTotal.filter(c => c.estado === 'En proceso'), titulo: 'En Proceso — Atendiendo' },
    };

    const cfg = mapa[filtro] || mapa.todos;
    if (titulo) titulo.innerText = cfg.titulo;

    tbody.innerHTML = '';
    cfg.lista.forEach(cita => {
        const idxReal = historialTotal.indexOf(cita);
        const row = document.createElement('tr');
        row.className = 'transition-all duration-300 hover:bg-sky-50/30';
        row.innerHTML = `
            <td class="px-8 py-6">
                <p class="font-black text-slate-800 text-sm">${formatearHoraAmPm(cita.hora)}</p>
                <p class="text-[10px] text-slate-400 font-bold uppercase mt-1">${cita.fecha || 'Hoy'}</p>
            </td>
            <td class="px-8 py-6">
                <p class="font-black text-slate-700 uppercase text-xs tracking-tight">${cita.nombre}</p>
                <p class="text-[11px] text-slate-400 font-bold mt-1">${cita.tipoDoc}: ${cita.numDoc}</p>
            </td>
            <td class="px-8 py-6 font-black text-sky-600 uppercase text-[11px] tracking-widest">${cita.especialidad}</td>
            <td class="px-8 py-6">${_badgeEstado(cita.estado)}</td>
            <td class="px-8 py-6 text-[11px] text-slate-500 font-bold" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:0;">${cita.motivo}</td>
            <td class="px-8 py-6" style="text-align:right;">${_botonesAccion(cita, idxReal)}</td>`;
        tbody.appendChild(row);
    });

    const noData = document.getElementById('no-datos-inicio');
    if (noData) noData.style.display = cfg.lista.length > 0 ? 'none' : 'block';
}

// ─── RENDER TABLA AGENDA ──────────────────────────────────────────────────────
function _renderTablaAgenda() {
    const tbody = document.getElementById('tabla-agenda');
    if (!tbody) return;
    tbody.innerHTML = '';

    agendaEspecialista.forEach(slot => {
        const estadoLabel = slot.EstadoAgenda || slot.Nombre_Estado || '—';
        const estadoClass = { 'Disponible': 'status-atendido', 'Ocupado': 'status-pendiente', 'Cancelado': 'status-cancelada-esp' }[estadoLabel] || 'status-pendiente';
        const agendaId    = slot.Agenda_ID || '';
        const soloDisp    = estadoLabel === 'Disponible';
        const row = document.createElement('tr');
        row.className = 'transition-all duration-300 hover:bg-sky-50/30';
        row.innerHTML = `
            <td class="px-8 py-6"><p class="font-black text-slate-800 text-xs uppercase">${slot.Fecha || '—'}</p></td>
            <td class="px-8 py-6"><p class="font-black text-slate-700 text-sm">${formatearHoraAmPm(slot.Hora_Inicio || '—')}</p></td>
            <td class="px-8 py-6"><p class="font-black text-slate-700 text-sm">${formatearHoraAmPm(slot.Hora_Fin || slot.Hora_Final || '—')}</p></td>
            <td class="px-8 py-6"><span class="${estadoClass} uppercase"><i class="fas fa-circle mr-2 text-[8px]"></i>${estadoLabel}</span></td>
            <td class="px-8 py-6" style="text-align:right;">
                ${soloDisp && agendaId ? `
                <button onclick="solicitarEliminarSlot(${agendaId})"
                    class="text-red-500 bg-red-50 hover:bg-red-500 hover:text-white px-6 py-3 rounded-2xl transition-all shadow-sm active:scale-95 inline-flex items-center gap-2 font-black text-[10px] uppercase btn-action">
                    <i class="fas fa-trash-alt text-sm"></i> Eliminar
                </button>` : '<span class="text-slate-300 text-[10px] font-bold uppercase">—</span>'}
            </td>`;
        tbody.appendChild(row);
    });

    const noData = document.getElementById('no-datos-agenda');
    if (noData) noData.style.display = agendaEspecialista.length > 0 ? 'none' : 'block';
}

// ─── RENDER TABLA MIS PACIENTES ───────────────────────────────────────────────
function _renderTablaPacientes() {
    const tbody = document.getElementById('tabla-pacientes');
    if (!tbody) return;
    tbody.innerHTML = '';

    const pacientesHistorial = historialTotal.filter(c => c.estado === 'Atendido' || c.estado === 'Cancelada');
    pacientesHistorial.forEach(cita => {
        const idxReal = historialTotal.indexOf(cita);
        const row = document.createElement('tr');
        row.className = 'transition-all duration-300 hover:bg-sky-50/30';
        row.innerHTML = `
            <td class="px-8 py-6">
                <p class="font-black text-slate-800 text-sm">${formatearHoraAmPm(cita.hora)}</p>
                <p class="text-[10px] text-slate-400 font-bold uppercase mt-1">${cita.fecha || '—'}</p>
            </td>
            <td class="px-8 py-6">
                <p class="font-black text-slate-700 uppercase text-xs tracking-tight">${cita.nombre}</p>
                <p class="text-[11px] text-slate-400 font-bold mt-1">${cita.tipoDoc}: ${cita.numDoc}</p>
            </td>
            <td class="px-8 py-6 font-black text-sky-600 uppercase text-[11px] tracking-widest">${cita.especialidad}</td>
            <td class="px-8 py-6">${_badgeEstado(cita.estado)}</td>
            <td class="px-8 py-6" style="text-align:right;">${_botonesAccion(cita, idxReal)}</td>`;
        tbody.appendChild(row);
    });

    const noData = document.getElementById('no-datos-pacientes');
    if (noData) noData.style.display = pacientesHistorial.length > 0 ? 'none' : 'block';
}

// ─── BADGE DE ESTADO ──────────────────────────────────────────────────────────
function _badgeEstado(estado) {
    const mapa = {
        'Pendiente':  { cls: 'status-pendiente',    icon: 'fa-clock' },
        'Atendido':   { cls: 'status-atendido',      icon: 'fa-check-circle' },
        'En proceso': { cls: 'status-en-proceso',    icon: 'fa-spinner fa-spin' },
        'Cancelada':  { cls: 'status-cancelada-esp', icon: 'fa-ban' },
    };
    const cfg = mapa[estado] || { cls: 'status-pendiente', icon: 'fa-circle' };
    return `<span class="${cfg.cls} uppercase"><i class="fas ${cfg.icon} mr-2"></i>${estado}</span>`;
}

// ─── BOTONES DE ACCIÓN ────────────────────────────────────────────────────────
function _botonesAccion(cita, idx) {
    const estado = cita.estado;
    if (estado === 'Pendiente') {
        return `<button onclick="abrirEmpezarCita(${idx})"
            class="btn-empezar-cita px-8 py-4 rounded-2xl font-black text-[10px] transition-all uppercase shadow-lg btn-action">
            <i class="fas fa-play mr-1"></i>Empezar Cita</button>`;
    }
    if (estado === 'En proceso') {
        return `<button onclick="abrirEmpezarCita(${idx})"
            class="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black text-[10px] hover:bg-sky-600 transition-all uppercase shadow-lg btn-action">
            <i class="fas fa-stethoscope mr-1"></i>Atender</button>`;
    }
    if (estado === 'Atendido') {
        return `<button onclick="verReporteProfesional(${idx})"
            class="text-sky-600 bg-sky-50 hover:bg-sky-600 hover:text-white px-6 py-3 rounded-2xl transition-all shadow-sm active:scale-95 inline-flex items-center gap-2 font-black text-[10px] uppercase btn-action">
            <i class="fas fa-file-medical text-sm"></i> Reporte</button>`;
    }
    if (estado === 'Cancelada') {
        return `<span class="text-slate-300 text-[10px] font-bold uppercase">—</span>`;
    }
    return '';
}

// ─── FILTRAR POR ESTADO ───────────────────────────────────────────────────────
function filtrarPorEstado(estado) {
    cambiarSeccion('inicio');
    _renderTablaInicio(estado);
}

// ─── NAVEGACIÓN ───────────────────────────────────────────────────────────────
const cambiarSeccion = (nombreSeccion) => {
    seccionActiva = nombreSeccion;
    const dpMenu = document.getElementById('profile-dropdown');
    if (dpMenu) dpMenu.classList.remove('show');

    const titulos = { inicio: 'Especialista', agenda: 'Agenda Médica', pacientes: 'Mis Pacientes', config: 'Mi Perfil' };

    ['inicio', 'agenda', 'pacientes', 'config'].forEach(s => {
        const el = document.getElementById(`sec-${s}`);
        if (el) s === nombreSeccion ? mostrarSeccion(`sec-${s}`) : ocultarSeccion(`sec-${s}`);
    });

    const mainTitle = document.getElementById('main-title');
    if (mainTitle) mainTitle.innerText = titulos[nombreSeccion] || 'Especialista';

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.id === `btn-${nombreSeccion}`);
    });

    if (nombreSeccion === 'config') {
        _resetearFlujoPasswordEsp();
        if (usuarioSesionActual && usuarioSesionActual.Usuario_ID) _cargarPerfilRealDesdeBD(usuarioSesionActual.Usuario_ID);
    } else {
        cargarDatosEspecialista();
    }
    if (nombreSeccion === 'agenda') inicializarPlaceholdersAgenda();
};

// ─── EMPEZAR CITA ─────────────────────────────────────────────────────────────
const abrirEmpezarCita = async (indice) => {
    try {
        const cita = historialTotal[indice];
        if (!cita) return;
        citaActualEmpezar = indice;

        const set = (id, val) => { const e = document.getElementById(id); if (e) e.innerText = val || '—'; };
        set('empezar-nombre-modal', cita.nombre);
        set('empezar-nombre-dato',  cita.nombre);
        set('empezar-doc-dato',     `${cita.tipoDoc}: ${cita.numDoc}`);
        set('empezar-estado-dato',  'En Proceso — Atendiendo');
        set('empezar-motivo-dato',  cita.motivo);

        const avatarPaciente = document.getElementById('empezar-avatar-paciente');
        if (avatarPaciente) avatarPaciente.textContent = _obtenerInicial(cita.nombre);

        document.getElementById('modalEmpezarCita').style.display = 'flex';

        if (cita.Cita_ID && cita.estado === 'Pendiente') {
            try {
                const resp = await fetch(`/api/citas/${cita.Cita_ID}/atender`, { method: 'PUT' });
                if (!resp.ok) {
                    const errData = await resp.json().catch(() => ({}));
                    console.warn('[especialista] No se pudo marcar en proceso:', resp.status, errData.error || '');
                }
            } catch (err) {
                console.warn('[especialista] Error marcando en proceso:', err);
            }
            historialTotal[indice].estado       = 'En proceso';
            historialTotal[indice].EstadoAgenda = 'Ocupado';
            _renderTodas();
        }
    } catch (err) {
        console.error('[especialista] Error abriendo cita:', err);
        mostrarToast('Error al abrir la cita.', 'error');
    }
};

const cerrarEmpezarCita = () => {
    const modal = document.getElementById('modalEmpezarCita');
    if (modal) modal.style.display = 'none';
};

// ─── FINALIZAR CONSULTA ───────────────────────────────────────────────────────
const finalizarConsultaDirecto = async () => {
    const indice = citaActualEmpezar;
    if (indice === null || indice === undefined) return;
    const cita = historialTotal[indice];
    if (!cita) return;

    if (!cita.Cita_ID) {
        mostrarToast('No se pudo identificar la cita a finalizar.', 'error');
        return;
    }

    try {
        const payloadHistorial = {
            Diagnosticos: cita.cie10 ? [cita.cie10] : [],
            Evolucion:    cita.evolucion    || '',
            Tratamiento:  cita.prescripcion || '',
        };

        const resp = await fetch(`/api/citas/${cita.Cita_ID}/atendido`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payloadHistorial),
        });
        const data = await resp.json().catch(() => ({}));

        if (!resp.ok || !data.ok) {
            mostrarToast(data.error || 'No se pudo finalizar la consulta en el servidor.', 'error');
            return;
        }

        const fechaAtencionReal = data.FechaAtencion || new Date().toISOString().replace('T', ' ').split('.')[0];

        if (data.Historial_ID) historialTotal[indice].Historial_ID = data.Historial_ID;
        historialTotal[indice].estado        = 'Atendido';
        historialTotal[indice].EstadoAgenda  = 'Cumplida';
        historialTotal[indice].FechaAtencion = fechaAtencionReal;

        _lanzarFinalizarConsulta(cita.Cita_ID);

        cerrarEmpezarCita();
        _renderTodas();
        mostrarToast('Consulta finalizada y registrada. Se notificará al paciente.', 'success');

    } catch (err) {
        console.error('[especialista] Error finalizando consulta:', err);
        mostrarToast('Error al finalizar la consulta.', 'error');
    }
};

async function _lanzarFinalizarConsulta(citaId) {
    try {
        const resp = await fetch(`/api/citas/${citaId}/finalizar-consulta`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
        });
        const data = await resp.json().catch(() => ({}));
        if (data.ok) logger_info(`[ENCUESTA] Encuesta pendiente creada para cita ${citaId}`);
    } catch (err) {
        console.warn('[especialista] No se pudo crear encuesta pendiente:', err);
    }
}

function logger_info(msg) {
    if (typeof console !== 'undefined') console.info(msg);
}

// ─── REQ 2: AUTOMATIZACIÓN DE MULTAS POR INCUMPLIMIENTO DE HORARIO ───────────
async function _procesarVencimientosMultas() {
    try {
        const resp = await fetch('/api/multas/procesar-vencimientos', { method: 'POST' });
        if (!resp.ok) return;
        const data = await resp.json().catch(() => ({}));
        if (data && data.ok && data.procesadas > 0) {
            console.info(`[multas] ${data.procesadas} cita(s) vencida(s) procesada(s) automáticamente.`);
            if (seccionActiva === 'inicio' || seccionActiva === 'pacientes') {
                cargarDatosEspecialista();
            }
        }
    } catch (err) {
        console.warn('[especialista] No se pudo procesar vencimientos de multas:', err);
    }
}

// ─── REPORTE PROFESIONAL ──────────────────────────────────────────────────────
// NOTA: Esta función abre el MODAL de reporte en el panel del especialista.
// NO navega al HTML de Historia Clínica. No llama a irAHistoriaClinica().
// Si el botón del modal dice "Historia Clínica", debe llamar a irAHistoriaClinica(),
// NO a esta función.
const verReporteProfesional = async (indice) => {
    try {
        const cita = historialTotal[indice];
        if (!cita) return;

        let diagnostico   = 'Sin diagnóstico';
        let evolucion     = 'Sin registro';
        let prescripcion  = 'Sin prescripción';
        let fechaAtencion = 'N/A';
        let tipoDoc       = cita.tipoDoc || 'DOC';
        let numDoc        = cita.numDoc  || '—';

        if (cita.Cita_ID) {
            // Enriquecer con datos del historial clínico (fetch JSON, no navega)
            try {
                const res = await fetch(`/api/historial-clinico/${cita.Cita_ID}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.ok && data.data) {
                        diagnostico   = data.data.Diagnostico   || diagnostico;
                        evolucion     = data.data.Evolucion     || evolucion;
                        prescripcion  = data.data.Tratamiento   || prescripcion;
                        fechaAtencion = data.data.FechaRegistro || fechaAtencion;
                    }
                }
            } catch (err) {
                console.warn('[especialista] Usando caché local para reporte.', err);
            }

            if (cita.FechaAtencion && fechaAtencion === 'N/A') fechaAtencion = cita.FechaAtencion;

            // Enriquecer documento del paciente (fetch JSON, no navega)
            try {
                const resCita = await fetch(`/api/citas/${cita.Cita_ID}`);
                if (resCita.ok) {
                    const dataCita = await resCita.json();
                    if (dataCita.TipoDocumento)  tipoDoc = dataCita.TipoDocumento;
                    if (dataCita.NumeroDocumento) numDoc  = dataCita.NumeroDocumento;
                }
            } catch (err) {
                console.warn('[especialista] No se pudo enriquecer datos del paciente.', err);
            }
        }

        const setEl = (id, val) => { const el = document.getElementById(id); if (!el) return; el.innerText = val || '—'; };
        setEl('rep-paciente',       cita.nombre);
        setEl('rep-fecha-atencion', `Atendido: ${fechaAtencion}`);
        setEl('rep-cita-info',      `Cita #${cita.Cita_ID || '—'} — ${cita.fecha} ${formatearHoraAmPm(cita.hora)}`);
        setEl('rep-tipo-doc',       tipoDoc);
        setEl('rep-num-doc',        numDoc);
        setEl('rep-diagnostico',    diagnostico);
        setEl('rep-evolucion',      evolucion);
        setEl('rep-prescripcion',   prescripcion);

        document.getElementById('modalReporte').style.display = 'flex';
    } catch (err) {
        console.error('[especialista] Error cargando reporte:', err);
        mostrarToast('Error al cargar el reporte.', 'error');
    }
};

// ══════════════════════════════════════════════════════════════════════════════
// REQ 5 + REQ 6 + REQ 7 + REQ 8
// irAHistoriaClinica() — NAVEGACIÓN A LA VISTA HTML DE HISTORIA CLÍNICA
//
// REGLA DE ORO:
//   window.location.href → /historial/paciente/<id>?cita_id=<id>
//   └─ Esta URL apunta a historial_bp → vista_historia_clinica()
//   └─ Flask devuelve render_template('historia_clinica.html')   ← HTML
//   └─ El navegador carga la interfaz visual normalmente
//
// NUNCA hacer:
//   fetch('/historial/paciente/...') ← devolvería HTML al fetch y se ignora
//   window.location.href = '/api/historial/...'  ← mostraría JSON crudo
//
// El único fetch() permitido aquí es el fallback para resolver Paciente_ID
// desde /api/citas/<id> cuando no está en caché — ese endpoint devuelve JSON
// limpio y no navega; solo alimenta el dato para construir la URL de vista.
// ══════════════════════════════════════════════════════════════════════════════
const irAHistoriaClinica = () => {
    try {
        const indice = citaActualEmpezar;
        if (indice === null || indice === undefined) {
            mostrarToast('No hay cita activa.', 'warning');
            return;
        }

        const cita = historialTotal[indice];
        if (!cita) {
            mostrarToast('No se encontró la cita.', 'error');
            return;
        }
        if (!cita.Cita_ID) {
            mostrarToast('La cita no tiene un ID válido.', 'error');
            return;
        }

        // Guardar respaldo en sessionStorage para resistir recargas de página
        sessionStorage.setItem('hc_cita_id',     String(cita.Cita_ID));
        sessionStorage.setItem('hc_paciente_id', String(cita.Paciente_ID || ''));

        /**
         * navegarAHistoriaClinica(pacienteId)
         * ─────────────────────────────────────
         * Construye la URL de VISTA y navega con window.location.href.
         * La ruta destino es:
         *   GET /historial/paciente/<pacienteId>?cita_id=<citaId>
         *   └─ historial_bp → vista_historia_clinica() → render_template HTML
         *
         * NO es una ruta de API. El navegador recibirá HTML, no JSON.
         */
        const navegarAHistoriaClinica = (pacienteId) => {
            const params = new URLSearchParams({ cita_id: cita.Cita_ID });
            // ✅ RUTA DE VISTA — render_template, siempre devuelve HTML
            window.location.href = `/historial/paciente/${pacienteId}?${params.toString()}`;
        };

        const pacienteId = cita.Paciente_ID || 0;

        if (pacienteId) {
            // Caso directo: Paciente_ID ya está en caché → navegamos de inmediato
            navegarAHistoriaClinica(pacienteId);
            return;
        }

        // Fallback: Paciente_ID no está en caché.
        // Hacemos fetch a /api/citas/<id> (JSON puro, citas_bp) para obtenerlo.
        // Este fetch NO navega — solo extrae el dato y llama a navegarAHistoriaClinica().
        fetch(`/api/citas/${cita.Cita_ID}`)
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then(d => {
                const pid = d.Paciente_ID;
                if (!pid) {
                    mostrarToast('No se pudo resolver el paciente de esta cita.', 'error');
                    return;
                }
                // Actualizar caché en memoria para la próxima vez
                historialTotal[indice].Paciente_ID = pid;
                sessionStorage.setItem('hc_paciente_id', String(pid));
                navegarAHistoriaClinica(pid);
            })
            .catch((err) => {
                console.error('[especialista] No se pudo resolver Paciente_ID:', err);
                mostrarToast('Error al obtener datos de la cita.', 'error');
            });

    } catch (err) {
        console.error('[especialista] Error redirigiendo a historia clínica:', err);
        mostrarToast('Error al abrir la historia clínica.', 'error');
    }
};

// ─── GUARDAR FRANJA HORARIA ───────────────────────────────────────────────────
const guardarFranjaHoraria = async () => {
    const especialistaId = usuarioSesionActual?.Especialista_ID;
    if (!especialistaId) { mostrarToast('No se pudo identificar el especialista.', 'error'); return; }

    const fechaInput      = document.getElementById('agenda-fecha');
    const horaInicioInput = document.getElementById('agenda-hora-inicio');
    const horaFinInput    = document.getElementById('agenda-hora-fin');
    const errorEl         = document.getElementById('agenda-form-error');

    const fecha      = fechaInput?.value?.trim()      || '';
    const horaInicio = horaInicioInput?.value?.trim() || '';
    const horaFin    = horaFinInput?.value?.trim()    || '';

    if (errorEl) { errorEl.innerText = ''; errorEl.classList.add('hidden'); }
    [fechaInput, horaInicioInput, horaFinInput].forEach(inp => {
        const wrapper = inp?.closest('.smart-picker-wrapper');
        if (wrapper) wrapper.classList.remove('input-error');
    });

    if (!fecha || !horaInicio || !horaFin) {
        if (errorEl) { errorEl.innerText = 'Completa todos los campos: fecha, hora de inicio y hora de fin.'; errorEl.classList.remove('hidden'); }
        return;
    }
    const hoy = new Date().toISOString().split('T')[0];
    if (fecha < hoy) {
        if (errorEl) { errorEl.innerText = 'La fecha no puede ser anterior a hoy.'; errorEl.classList.remove('hidden'); }
        return;
    }
    if (horaFin <= horaInicio) {
        if (errorEl) { errorEl.innerText = 'La hora de fin debe ser posterior a la hora de inicio.'; errorEl.classList.remove('hidden'); }
        return;
    }

    try {
        const resp = await fetch('/api/agenda', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Especialista_ID: especialistaId, Fecha: fecha, Hora_Inicio: horaInicio, Hora_Fin: horaFin, Estado_ID: 1 })
        });
        const data = await resp.json().catch(() => ({}));

        if (resp.status === 409) {
            const msg = data.error || 'Ya existe una disponibilidad registrada para esta fecha y horario.';
            if (errorEl) { errorEl.innerText = `⚠ ${msg}`; errorEl.classList.remove('hidden'); }
            [fechaInput, horaInicioInput, horaFinInput].forEach(inp => {
                const wrapper = inp?.closest('.smart-picker-wrapper');
                if (wrapper) wrapper.classList.add('input-error');
            });
            mostrarToast(msg, 'warning');
            return;
        }

        if (!resp.ok || !data.ok) {
            if (errorEl) { errorEl.innerText = data.error || 'No se pudo guardar la disponibilidad.'; errorEl.classList.remove('hidden'); }
            return;
        }

        if (fechaInput)      { fechaInput.value      = ''; actualizarPlaceholderVisual(fechaInput); }
        if (horaInicioInput) { horaInicioInput.value = ''; actualizarPlaceholderVisual(horaInicioInput); }
        if (horaFinInput)    { horaFinInput.value     = ''; actualizarPlaceholderVisual(horaFinInput); }
        mostrarToast('Disponibilidad guardada correctamente.', 'success');
        await _cargarAgendaEspecialista(especialistaId);
    } catch (err) {
        console.error('[especialista] Error guardando franja:', err);
        if (errorEl) { errorEl.innerText = 'Error de conexión al guardar la disponibilidad.'; errorEl.classList.remove('hidden'); }
    }
};

// ─── ELIMINAR FRANJA ──────────────────────────────────────────────────────────
function solicitarEliminarSlot(agendaId) {
    slotPendienteEliminar = agendaId;
    const modal = document.getElementById('modalEliminarSlot');
    if (modal) modal.style.display = 'flex';
}
async function confirmarEliminarSlot() {
    const modal = document.getElementById('modalEliminarSlot');
    if (modal) modal.style.display = 'none';
    if (!slotPendienteEliminar) return;
    try {
        const resp = await fetch(`/api/agenda/${slotPendienteEliminar}`, { method: 'DELETE' });
        if (!resp.ok && resp.status !== 405) {
            const data = await resp.json().catch(() => ({}));
            mostrarToast(data.error || 'No se pudo eliminar el horario.', 'error');
            slotPendienteEliminar = null;
            return;
        }
        mostrarToast('Horario eliminado correctamente.', 'success');
        agendaEspecialista = agendaEspecialista.filter(s => String(s.Agenda_ID) !== String(slotPendienteEliminar));
        _renderTablaAgenda();
    } catch (err) {
        console.error('[especialista] Error eliminando slot:', err);
        mostrarToast('Error de conexión al eliminar el horario.', 'error');
    }
    slotPendienteEliminar = null;
}

// ─── TOGGLE CONTRASEÑA ────────────────────────────────────────────────────────
window.togglePassVisibilidad = function(inputId, btn) {
    try {
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
    } catch (err) { console.warn('[especialista] Error toggle password:', err); }
};

// ─── VALIDACIÓN CONTRASEÑA ────────────────────────────────────────────────────
function _cumpleRequisitosEsp(pass) {
    return {
        length:  pass.length >= 8,
        upper:   /[A-Z]/.test(pass),
        lower:   /[a-z]/.test(pass),
        number:  /[0-9]/.test(pass),
        special: /[^A-Za-z0-9]/.test(pass),
    };
}

window.validarRequisitosEnTiempoRealEsp = function () {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitosEsp(pass);
    _aplicarEstadoRequisitoEsp('req-length-esp',  res.length,  false);
    _aplicarEstadoRequisitoEsp('req-upper-esp',   res.upper,   false);
    _aplicarEstadoRequisitoEsp('req-lower-esp',   res.lower,   false);
    _aplicarEstadoRequisitoEsp('req-number-esp',  res.number,  false);
    _aplicarEstadoRequisitoEsp('req-special-esp', res.special, false);
};

function _aplicarEstadoRequisitoEsp(id, cumple, marcarRojo) {
    const el   = document.getElementById(id);
    if (!el) return;
    const icon = el.querySelector('.req-icon');
    if (cumple) {
        el.className  = 'req-item req-ok';
        if (icon) icon.textContent = '✓';
    } else if (marcarRojo) {
        el.className  = 'req-item req-error';
        if (icon) icon.textContent = '-';
    } else {
        el.className  = 'req-item req-pending';
        if (icon) icon.textContent = '-';
    }
}

function _marcarRequisitosIncumplidosEsp() {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitosEsp(pass);
    _aplicarEstadoRequisitoEsp('req-length-esp',  res.length,  !res.length);
    _aplicarEstadoRequisitoEsp('req-upper-esp',   res.upper,   !res.upper);
    _aplicarEstadoRequisitoEsp('req-lower-esp',   res.lower,   !res.lower);
    _aplicarEstadoRequisitoEsp('req-number-esp',  res.number,  !res.number);
    _aplicarEstadoRequisitoEsp('req-special-esp', res.special, !res.special);
    return res.length && res.upper && res.lower && res.number && res.special;
}

const _resetearFlujoPasswordEsp = () => {
    try {
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
        ['req-length-esp', 'req-upper-esp', 'req-lower-esp', 'req-number-esp', 'req-special-esp'].forEach(id => {
            _aplicarEstadoRequisitoEsp(id, false, false);
        });
    } catch (err) { console.warn('[especialista] Error reseteando formulario password:', err); }
};

window.validarPasswordActualEsp = function () {
    const usuarioId   = usuarioSesionActual?.Usuario_ID;
    const inputActual = document.getElementById('pass-actual');
    const errActual   = document.getElementById('error-pass-actual');
    const step1       = document.getElementById('pass-step1');
    const step2       = document.getElementById('pass-step2');

    if (errActual) errActual.style.display = 'none';

    if (!inputActual?.value.trim()) {
        if (errActual) { errActual.textContent = 'Ingresa tu contraseña actual.'; errActual.style.display = 'block'; }
        return;
    }

    fetch('/api/verificar-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ password: inputActual.value, usuario_id: usuarioId }),
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
    .catch(() => mostrarToast('Error de conexión al verificar la contraseña.', 'error'));
};

const guardarPerfilCompleto = async () => {
    const usuarioId  = usuarioSesionActual?.Usuario_ID;
    const errActual  = document.getElementById('error-pass-actual');
    const errNueva   = document.getElementById('error-pass-nueva');
    const step2      = document.getElementById('pass-step2');

    if (errActual) errActual.style.display = 'none';
    if (errNueva)  errNueva.style.display  = 'none';

    if (!usuarioId) { mostrarToast('No se pudo identificar la sesión.', 'error'); return; }

    const nombres    = (document.getElementById('conf-nombres')?.value   || '').trim();
    const apellidos  = (document.getElementById('conf-apellidos')?.value || '').trim();
    const correo     = (document.getElementById('conf-email')?.value     || '').trim();
    const telefono   = (document.getElementById('conf-tel')?.value       || '').trim();
    const passActual = document.getElementById('pass-actual')?.value        || '';
    const passNueva  = document.getElementById('conf-pass-nueva')?.value    || '';
    const passConf   = document.getElementById('conf-pass-confirmar')?.value || '';

    if (!passActual.trim()) {
        if (errActual) { errActual.innerText = 'Ingresa tu contraseña actual para guardar cambios.'; errActual.style.display = 'block'; }
        return;
    }

    if (step2?.style.display !== 'none' && passNueva) {
        const todosOk = _marcarRequisitosIncumplidosEsp();
        if (!todosOk) return;
        if (passNueva !== passConf) {
            if (errNueva) errNueva.style.display = 'block';
            return;
        }
    }

    try {
        const resp = await fetch(`/api/usuarios/${usuarioId}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                ContrasenaActual: passActual,
                Nombres:   nombres,
                Apellidos: apellidos,
                Correo:    correo,
                Telefono:  telefono,
                nuevaPass: (step2?.style.display !== 'none' && passNueva) ? passNueva : null,
            })
        });
        const data = await resp.json().catch(() => ({}));

        if (!resp.ok || !data.ok) {
            if (resp.status === 401) {
                if (errActual) { errActual.innerText = data.error || 'Contraseña incorrecta.'; errActual.style.display = 'block'; }
            } else {
                mostrarToast(data.error || 'No se pudo actualizar el perfil.', 'error');
            }
            return;
        }

        if (usuarioSesionActual) {
            usuarioSesionActual.Nombres   = nombres   || usuarioSesionActual.Nombres;
            usuarioSesionActual.Apellidos = apellidos || usuarioSesionActual.Apellidos;
            usuarioSesionActual.Correo    = correo    || usuarioSesionActual.Correo;
            usuarioSesionActual.Telefono  = telefono  || usuarioSesionActual.Telefono;
            sessionStorage.setItem('odent_usuario', JSON.stringify(usuarioSesionActual));
        }

        mostrarToast('Perfil actualizado correctamente.', 'success');
        if (usuarioId) await _cargarPerfilRealDesdeBD(usuarioId);
        cambiarSeccion('inicio');
    } catch (err) {
        console.error('[especialista] Error guardando perfil:', err);
        mostrarToast('Error de conexión al guardar el perfil.', 'error');
    }
};

// ─── CONFIRMACIÓN SIMPLE ──────────────────────────────────────────────────────
let accionPendienteSimple = '';
function mostrarConfirmacionSimple(mensaje, accion) {
    try {
        const modal = document.getElementById('modalConfirmarSimple');
        const texto = document.getElementById('confirm-text-simple');
        if (modal && texto) { texto.innerText = mensaje; accionPendienteSimple = accion; modal.style.display = 'flex'; }
    } catch (err) { console.warn('[especialista] Error mostrando confirmación:', err); }
}
function cerrarModalSimple() {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
    accionPendienteSimple = '';
}
function ejecutarAccionSimple() {
    if (accionPendienteSimple === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
    cerrarModalSimple();
}

// ─── INIT ─────────────────────────────────────────────────────────────────────
window.onload = () => {
    try {
        ['inicio', 'agenda', 'pacientes', 'config'].forEach(s => {
            const el = document.getElementById(`sec-${s}`);
            if (el) {
                if (s === 'inicio') { el.classList.remove('seccion-oculta'); el.classList.add('seccion-visible'); }
                else                { el.classList.remove('seccion-visible'); el.classList.add('seccion-oculta'); }
            }
        });

        const fechaInput = document.getElementById('agenda-fecha');
        if (fechaInput) {
            fechaInput.min = new Date().toISOString().split('T')[0];
            fechaInput.addEventListener('change', () => actualizarPlaceholderVisual(fechaInput));
        }

        ['agenda-hora-inicio', 'agenda-hora-fin'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => actualizarPlaceholderVisual(el));
        });

        inicializarPlaceholdersAgenda();
        cargarInfoSesion();
        actualizarReloj();
        setInterval(actualizarReloj, 1000);
        cargarDatosEspecialista();

        // REQ 2: procesar vencimientos de multas al cargar y luego cada 60s
        _procesarVencimientosMultas();
        setInterval(_procesarVencimientosMultas, 60000);

        const fechaEl = document.getElementById('fecha-actual');
        if (fechaEl) {
            fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
            }).toUpperCase();
        }
    } catch (err) { console.error('[especialista] Error en window.onload:', err); }
};