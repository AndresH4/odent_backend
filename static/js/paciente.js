// Archivo: paciente.js  — Stylo Dental Pro v3.0
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

// ─── MAPA DE VISTAS ───────────────────────────────────────────────────────────
const VISTAS_PACIENTE = {
    inicio   : { el: 'vista-inicio',    btn: 'btn-inicio',    titulo: 'Paciente'           },
    historial: { el: 'vista-historial', btn: 'btn-historial', titulo: 'Historial de Citas' },
    config   : { el: 'vista-config',    btn: 'btn-config',    titulo: 'Mi Perfil'          },
};

// ─── MODALES PERSONALIZADOS ───────────────────────────────────────────────────
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

    titEl.textContent = titulo;
    msgEl.textContent = mensaje;
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
    const inicial = (u.Nombres || '').trim().charAt(0).toUpperCase() || 'P';

    _setText('avatar-letras',         inicial);
    _setText('nombre-usuario-header', nombreCompleto);
    _setText('perfil-avatar-grande',  inicial);
    _setText('nombre-menu',           nombreCompleto.toUpperCase());
    _setText('doc-menu',              u.NumeroDocumento || '');

    _setText('nombre-usuario',    nombreCompleto);
    _setText('perfil-nombres',    u.Nombres    || '');
    _setText('perfil-apellidos',  u.Apellidos  || '');
    _setText('perfil-correo',     u.Correo     || '');
    _setText('perfil-numDoc',     u.NumeroDocumento || '');
    _setText('perfil-telefono',   u.Telefono   || '');
    _setText('perfil-nacimiento', u.FechaNacimiento || '');

    _setText('email-menu',    u.Correo   || '—');
    _setText('telefono-menu', u.Telefono || '—');

    _cargarTipoDocumento(u.TipoDoc_ID, u.NumeroDocumento);

    fetch(`/api/paciente/por-usuario/${_usuarioId}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.Paciente_ID) {
                _pacienteId = data.Paciente_ID;
                _cargarCitasPaciente();
                _cargarAfiliacionCompleta();
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

        const tipo = lista.find(t => String(t.TipoDoc_ID) === String(tipoDocId));
        const nombreTipo = tipo
            ? (tipo.Nombre_Tipo_Documento || tipo.Descripcion || tipo.Nombre_Tipo || 'Doc.')
            : 'Doc.';

        _setText('doc-detalle-menu', `${nombreTipo}: ${numeroDoc || '—'}`);
    } catch (err) {
        console.warn('[paciente] No se pudo cargar tipo de documento:', err);
        _setText('doc-detalle-menu', numeroDoc || '—');
    }
}

// ─── EPS COMPLETA (dropdown header) ──────────────────────────────────────────
async function _cargarAfiliacionCompleta() {
    if (!_usuarioId) return;
    try {
        const [resAfil, resEps, resRegimen, resTipo] = await Promise.all([
            fetch('/api/afiliacion'),
            fetch('/api/eps'),
            fetch('/api/regimen-eps'),
            fetch('/api/tipo-eps'),
        ]);

        if (!resAfil.ok) { console.warn('[paciente] /api/afiliacion no respondió OK'); return; }

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
        if (!afil) { console.warn('[paciente] No se encontró afiliación para Usuario_ID:', _usuarioId); return; }

        const epsId     = afil.EPS_ID     || afil.Id_EPS     || afil.eps_id     || null;
        const tipoEpsId = afil.TipoEPS_ID || afil.ID_Tipo_EPS || afil.tipoeps_id || null;

        let nombreEPS = afil.Nombre_EPS || afil.nombre_eps || '';
        if (!nombreEPS && epsId) {
            const epsObj = listaEps.find(e => String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId));
            nombreEPS = epsObj ? (epsObj.Nombre_EPS || epsObj.nombre_eps || epsObj.Nombre || '—') : '—';
        }
        _setText('eps-menu',   nombreEPS || '—');
        _setText('perfil-eps', nombreEPS || '—');

        let nombreRegimen = afil.Nombre_Regimen || afil.nombre_regimen || '';
        if (!nombreRegimen) {
            let regimenId = afil.Regimen_ID || afil.ID_Regimen_EPS || afil.regimen_id || null;
            if (!regimenId && epsId) {
                const epsObj = listaEps.find(e => String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId));
                regimenId = epsObj ? (epsObj.Regimen_ID || epsObj.regimen_id || epsObj.ID_Regimen_EPS || null) : null;
            }
            if (regimenId) {
                const regObj = listaRegimen.find(r => String(r.Regimen_ID || r.ID_Regimen_EPS || r.regimen_id) === String(regimenId));
                nombreRegimen = regObj ? (regObj.Descripcion || regObj.Nombre_Regimen || regObj.nombre_regimen || '—') : '—';
            } else {
                nombreRegimen = '—';
            }
        }
        _setText('regimen-menu', nombreRegimen);

        let nombreTipoEPS = afil.Nombre_Tipo || afil.nombre_tipo || '';
        if (!nombreTipoEPS && tipoEpsId) {
            const tipoObj = listaTipos.find(t => String(t.TipoEPS_ID || t.ID_Tipo_EPS || t.tipoeps_id) === String(tipoEpsId));
            nombreTipoEPS = tipoObj ? (tipoObj.Nombre_Tipo || tipoObj.nombre_tipo || tipoObj.Nombre || '—') : '—';
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

function _show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function _hide(id) { document.getElementById(id)?.classList.add('hidden');    }

// ─── RELOJ Y ESTADO LABORAL ───────────────────────────────────────────────────
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
        const ampm = h < 12 ? 'AM' : 'PM';
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

// ─── HELPERS DE ESTADO ───────────────────────────────────────────────────────
function _resolverEstado(c) {
    const hoy = new Date().toISOString().split('T')[0];
    const estado = (c.EstadoAgenda || '').toLowerCase();

    if (estado === 'cancelado') {
        if (c.EstadoMulta && c.EstadoMulta !== 'Sin multa') {
            return { label: 'Cancelada con multa', clase: 'bg-amber-100 text-amber-700' };
        }
        return { label: 'Cancelada', clase: 'bg-red-100 text-red-600' };
    }
    if (estado === 'cumplida' || estado === 'ocupado' && c.Fecha < hoy) {
        if (estado === 'ocupado' && c.Fecha < hoy) {
            return { label: 'Cancelada con multa', clase: 'bg-amber-100 text-amber-700' };
        }
        return { label: 'Cumplida', clase: 'bg-green-100 text-green-700' };
    }
    if (estado === 'ocupado') {
        return { label: 'Pendiente', clase: 'bg-sky-100 text-sky-700' };
    }
    if (estado === 'disponible') {
        return { label: 'Pendiente', clase: 'bg-sky-100 text-sky-700' };
    }
    return { label: c.EstadoAgenda || '—', clase: 'bg-slate-100 text-slate-500' };
}

// ── Conjunto de estados que NUNCA deben aparecer en la sección "Inicio".
// Toda cita cuya etiqueta resuelta (_resolverEstado) coincida con alguno de
// estos valores queda forzosamente excluida de las citas activas/vigentes,
// sin importar su EstadoAgenda crudo ni su Fecha. ────────────────────────────
const ESTADOS_EXCLUIDOS_DE_INICIO = ['Cancelada', 'Cancelada con multa'];

function _esCitaActiva(c) {
    // Filtro estricto: si la etiqueta resuelta es "Cancelada" o "Cancelada con
    // multa", la cita jamás se considera activa, independientemente de su
    // EstadoAgenda crudo o de su Fecha.
    const estadoInfo = _resolverEstado(c);
    if (ESTADOS_EXCLUIDOS_DE_INICIO.includes(estadoInfo.label)) {
        return false;
    }

    const hoy   = new Date().toISOString().split('T')[0];
    const estado = (c.EstadoAgenda || '').toLowerCase();
    return (estado === 'ocupado' || estado === 'disponible') && c.Fecha >= hoy;
}

function _esCitaHistorial(c) {
    // Toda cita "Cancelada" o "Cancelada con multa" queda garantizada aquí,
    // ya que _esCitaActiva las excluye explícitamente arriba.
    return !_esCitaActiva(c);
}

// ─── RENDER TABLA PRINCIPAL (INICIO) — Solo citas vigentes ──────────────────
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
        const esCumplida = (c.EstadoAgenda || '').toLowerCase() === 'cumplida';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="p-5 font-black text-slate-700 uppercase text-xs">${c.NombrePaciente || '—'}</td>
            <td class="p-5 text-xs text-slate-500">${c.NumeroDocumento || '—'}</td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5">
                <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}">
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
            </td>
            <td class="p-5 text-center">
                ${esCumplida
                    ? `<button onclick="_abrirRanking(${c.Cita_ID})"
                           class="text-[10px] bg-amber-50 text-amber-600 border border-amber-200 px-4 py-2 rounded-xl font-black hover:bg-amber-100 transition-all uppercase">
                           <i class="fas fa-star mr-1"></i> Evaluar
                       </button>`
                    : '<span class="text-slate-300 text-[10px] font-bold">—</span>'
                }
            </td>`;
        tbody.appendChild(tr);
    });
}

// ─── RENDER HISTORIAL — Solo citas no activas ─────────────────────────────────
function _renderHistorial() {
    const tbody = document.getElementById('tabla-historial-completo');
    if (!tbody) return;
    tbody.innerHTML = '';

    const historial = _citasData.filter(_esCitaHistorial);

    if (historial.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-10 text-center text-slate-400 font-bold italic text-xs uppercase">Sin historial registrado.</td></tr>`;
        return;
    }

    historial.forEach(c => {
        const estadoInfo = _resolverEstado(c);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs text-slate-600">Dr(a). ${c.NombreEspecialista || '—'}</td>
            <td class="p-5">
                <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full ${estadoInfo.clase}">
                    ${estadoInfo.label}
                </span>
            </td>
            <td class="p-5 text-center">
                <span class="text-[10px] font-bold text-slate-400">${c.Motivo_Consulta || '—'}</span>
            </td>`;
        tbody.appendChild(tr);
    });
}

// ─── LÓGICA DE CANCELACIÓN CON DETECCIÓN DE MULTA ────────────────────────────
function _calcularMinutosRestantes(fecha, horaInicio) {
    try {
        const citaDateTime = new Date(`${fecha}T${horaInicio}`);
        const ahora        = new Date();
        return (citaDateTime - ahora) / 60000;
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

// ─── CANCELAR CITA ────────────────────────────────────────────────────────────
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
        const tiempoTexto = _formatearTiempoRestante(minutosRestantes);
        const tiempoEl = document.getElementById('tiempo-restante-multa');
        if (tiempoEl) tiempoEl.textContent = tiempoTexto;
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
        const url = _cancelarConMulta
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

// ─── RANKING ──────────────────────────────────────────────────────────────────
window._abrirRanking = async function (citaId) {
    try {
        const resP  = await fetch('/api/pregunta');
        const dataP = await resP.json();
        if (!dataP.ok || !dataP.data.length) {
            _mostrarNotificacion('Sin Preguntas', 'No hay preguntas de evaluación configuradas.', 'info');
            return;
        }
        _mostrarFormRanking(citaId, dataP.data);
    } catch (err) {
        console.error('[ranking] Error cargando preguntas:', err);
        _mostrarNotificacion('Error', 'Error al cargar preguntas de evaluación.', 'error');
    }
};

function _mostrarFormRanking(citaId, preguntas) {
    const existente = document.getElementById('modal-ranking-dinamico');
    if (existente) existente.remove();

    const modal = document.createElement('div');
    modal.id        = 'modal-ranking-dinamico';
    modal.className = 'modal-overlay';
    modal.style.display = 'flex';

    const preguntasHTML = preguntas.map(p => `
        <div class="mb-4">
            <p class="text-[11px] font-black text-slate-600 uppercase tracking-widest mb-2">${p.Texto_Pregunta}</p>
            <div class="flex gap-3">
                ${[1,2,3,4,5].map(v => `
                    <label class="flex flex-col items-center cursor-pointer">
                        <input type="radio" name="pregunta_${p.ID_Pregunta}" value="${v}" class="sr-only">
                        <span class="text-2xl star-btn" data-val="${v}">☆</span>
                        <span class="text-[9px] font-bold text-slate-400">${v}</span>
                    </label>`).join('')}
            </div>
        </div>`).join('');

    modal.innerHTML = `
        <div class="modal-content" style="max-width:540px;">
            <div class="bg-slate-900 p-6 rounded-t-[45px] text-white text-center">
                <p class="text-slate-500 text-[9px] font-black uppercase tracking-widest mb-1">Evaluación</p>
                <h3 class="font-black uppercase tracking-widest text-sm">Califica tu experiencia</h3>
            </div>
            <div class="p-8">
                <form id="form-ranking">
                    ${preguntasHTML}
                    <div id="err-ranking" class="text-red-600 text-xs font-bold mt-2" style="display:none;"></div>
                    <div class="flex gap-4 mt-8 pt-6 border-t border-slate-100">
                        <button type="button" onclick="document.getElementById('modal-ranking-dinamico').remove()"
                            class="flex-1 bg-slate-100 text-slate-500 py-4 rounded-2xl font-bold hover:bg-slate-200 transition-all uppercase text-[10px] tracking-widest">
                            Cancelar
                        </button>
                        <button type="button" onclick="_enviarRanking(${citaId}, ${JSON.stringify(preguntas.map(p => p.ID_Pregunta))})"
                            class="flex-1 bg-sky-600 text-white py-4 rounded-2xl font-black hover:bg-sky-700 transition-all uppercase text-[10px] tracking-widest shadow-lg">
                            <i class="fas fa-paper-plane mr-2"></i> Enviar Evaluación
                        </button>
                    </div>
                </form>
            </div>
        </div>`;

    document.body.appendChild(modal);

    modal.querySelectorAll('.star-btn').forEach(star => {
        star.addEventListener('click', function () {
            const name = this.closest('div').querySelector('input[type=radio]').name;
            const val  = parseInt(this.dataset.val);
            modal.querySelectorAll(`input[name="${name}"]`).forEach(r => {
                if (parseInt(r.value) === val) r.checked = true;
            });
            const allStars = this.parentElement.parentElement.querySelectorAll('.star-btn');
            allStars.forEach((s, i) => { s.textContent = i < val ? '★' : '☆'; });
        });
    });
}

window._enviarRanking = async function (citaId, preguntaIds) {
    const errEl = document.getElementById('err-ranking');
    const respuestas = [];

    for (const pid of preguntaIds) {
        const selected = document.querySelector(`input[name="pregunta_${pid}"]:checked`);
        if (!selected) {
            if (errEl) { errEl.textContent = '⚠ Responde todas las preguntas.'; errEl.style.display = 'block'; }
            return;
        }
        respuestas.push({ ID_Pregunta: pid, Texto_Respuesta: selected.value });
    }

    try {
        for (const r of respuestas) {
            const res = await fetch('/api/respuesta', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    ID_Pregunta:     r.ID_Pregunta,
                    ID_Paciente:     _pacienteId,
                    Texto_Respuesta: r.Texto_Respuesta,
                    Cita_ID:         citaId
                })
            });
            const data = await res.json();
            if (!data.ok) {
                if (errEl) { errEl.textContent = data.error || 'Error al enviar evaluación.'; errEl.style.display = 'block'; }
                return;
            }
        }
        document.getElementById('modal-ranking-dinamico')?.remove();
        _mostrarNotificacion('¡Gracias!', 'Tu evaluación fue enviada correctamente.', 'success');
    } catch (err) {
        console.error('[ranking] Error enviando respuestas:', err);
        if (errEl) { errEl.textContent = 'Error de conexión. Intente de nuevo.'; errEl.style.display = 'block'; }
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

// ─── VALIDACIÓN DE POLÍTICA DE CONTRASEÑA ────────────────────────────────────
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

// ─── MI PERFIL — CARGA DE SELECTS EPS (COMPLETA, INDEPENDIENTE) ──────────────
// Cada selector (Régimen, Tipo EPS, EPS) se carga con el 100% de los registros
// de su tabla correspondiente. El Régimen ya NO depende de la EPS seleccionada;
// se muestra el catálogo completo para que el paciente elija libremente.
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

        // ── 1. Poblar select de RÉGIMEN EPS — catálogo completo ───────────────
        const selRegimen = document.getElementById('edit-regimen-eps');
        if (selRegimen) {
            selRegimen.innerHTML = '<option value="">Seleccione Régimen...</option>';
            selRegimen.disabled  = false;
            _listaRegimenGlobal.forEach(r => {
                const id  = r.Regimen_ID || r.ID_Regimen_EPS || r.regimen_id;
                const nom = r.Descripcion || r.Nombre_Regimen || r.nombre_regimen || '';
                const opt = document.createElement('option');
                opt.value       = id;
                opt.textContent = nom;
                selRegimen.appendChild(opt);
            });
        }

        // ── 2. Poblar select de TIPO EPS — catálogo completo ─────────────────
        const selTipo = document.getElementById('edit-tipo-eps');
        if (selTipo) {
            selTipo.innerHTML = '<option value="">Seleccione Tipo EPS...</option>';
            _listaTipoEpsGlobal.forEach(t => {
                const id  = t.TipoEPS_ID || t.ID_Tipo_EPS || t.tipoeps_id;
                const nom = t.Nombre_Tipo || t.nombre_tipo || t.Nombre || '';
                const opt = document.createElement('option');
                opt.value       = id;
                opt.textContent = nom;
                selTipo.appendChild(opt);
            });
        }

        // ── 3. Poblar select de EPS — catálogo completo ───────────────────────
        const selEps = document.getElementById('edit-eps');
        if (selEps) {
            selEps.innerHTML = '<option value="">Seleccione EPS...</option>';
            _listaEpsGlobal.forEach(e => {
                const id  = e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS;
                const nom = e.Nombre_EPS || e.nombre_eps || e.Nombre || '';
                const opt = document.createElement('option');
                opt.value       = id;
                opt.textContent = nom;
                selEps.appendChild(opt);
            });
        }

    } catch (err) {
        console.warn('[perfil] Error cargando selects EPS:', err);
    }
}

// ─── MI PERFIL — PRECARGA DESDE BD ───────────────────────────────────────────
async function _precargarPerfil() {
    if (!_usuarioId) return;

    _resetearFlujoPassword();

    // ── 1. Obtener datos actualizados del usuario desde el backend ────────────
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

    // ── 2. Precargar campos de texto con datos de la sesión (ya frescos) ──────
    const u = _sesionPaciente;
    const nombreCompleto = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
    _setVal('edit-nombres',   nombreCompleto);
    _setVal('edit-correo',    u.Correo   || '');
    _setVal('edit-telefono',  u.Telefono || '');

    // ── 3. Cargar TODOS los selects con el catálogo completo de la BD ─────────
    await _cargarSelectsEps();

    // ── 4. Precargar valores actuales de afiliación del paciente ──────────────
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

                // Obtener el Regimen_ID a partir de la EPS actual del paciente
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

    // ── 5. Listener: al cambiar EPS, sugerir el Régimen correspondiente ───────
    // El selector de Régimen permanece editable con el catálogo completo;
    // solo se pre-selecciona el régimen asociado a la EPS elegida como ayuda visual.
    const selEps = document.getElementById('edit-eps');
    if (selEps) {
        const selEpsNuevo = selEps.cloneNode(true);
        selEps.parentNode.replaceChild(selEpsNuevo, selEps);
        selEpsNuevo.addEventListener('change', function () {
            _sugerirRegimenSegunEps(this.value);
        });
    }
}

/**
 * Pre-selecciona el Régimen asociado a la EPS elegida.
 * El select de Régimen permanece habilitado y con todas las opciones;
 * el paciente puede cambiarlo libremente si lo desea.
 */
function _sugerirRegimenSegunEps(epsId) {
    const selRegimen = document.getElementById('edit-regimen-eps');
    if (!selRegimen || !epsId) return;

    const epsObj = _listaEpsGlobal.find(e =>
        String(e.EPS_ID || e.Id_EPS || e.eps_id || e.ID_EPS) === String(epsId)
    );
    if (!epsObj) return;

    const regimenId = epsObj.Regimen_ID || epsObj.regimen_id || epsObj.ID_Regimen_EPS || null;
    if (regimenId) {
        selRegimen.value = String(regimenId);
    }
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
    .catch(() => {
        _mostrarNotificacion('Error de Conexión', 'No se pudo verificar la contraseña.', 'error');
    });
};

// ─── GUARDAR PERFIL — UPDATE REAL EN BD ──────────────────────────────────────
window.guardarPerfilPaciente = function () {
    const nombreCompleto = (document.getElementById('edit-nombres')?.value || '').trim();
    const partes         = nombreCompleto.split(/\s+/);
    const mitad          = Math.ceil(partes.length / 2);
    const nombres        = partes.slice(0, mitad).join(' ');
    const apellidos      = partes.slice(mitad).join(' ');

    const correo    = (document.getElementById('edit-correo')?.value   || '').trim();
    const telefono  = (document.getElementById('edit-telefono')?.value || '').trim();
    const passNueva = document.getElementById('conf-pass-nueva')?.value    || '';
    const passConf  = document.getElementById('conf-pass-confirmar')?.value || '';
    const errNueva  = document.getElementById('error-pass-nueva');
    const step2     = document.getElementById('pass-step2');

    // ── Leer valores de los selectores EPS (orden: Régimen, Tipo, EPS) ───────
    const selEps     = document.getElementById('edit-eps');
    const selTipoEps = document.getElementById('edit-tipo-eps');
    const regimenEl  = document.getElementById('edit-regimen-eps');

    const epsId     = selEps     ? (selEps.value     || null) : null;
    const tipoEpsId = selTipoEps ? (selTipoEps.value || null) : null;
    const regimenId = regimenEl  ? (regimenEl.value  || null) : null;

    // ── Validar contraseña si se mostró el paso 2 ────────────────────────────
    if (step2?.style.display !== 'none' && passNueva) {
        const todosOk = _marcarRequisitosIncumplidos();
        if (!todosOk) return;
        if (passNueva !== passConf) {
            if (errNueva) errNueva.style.display = 'block';
            return;
        }
    }
    if (errNueva) errNueva.style.display = 'none';

    const payload = {
        usuario_id:  _usuarioId,
        nombres:     nombres   || undefined,
        apellidos:   apellidos || undefined,
        correo:      correo    || undefined,
        telefono:    telefono  || undefined,
        nuevaPass:   (step2?.style.display !== 'none' && passNueva) ? passNueva : null,
        eps_id:      epsId     ? parseInt(epsId)     : null,
        tipo_eps_id: tipoEpsId ? parseInt(tipoEpsId) : null,
        regimen_id:  regimenId ? parseInt(regimenId) : null,
    };

    fetch('/api/actualizar-perfil-paciente', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
    })
    .then(r => r.json())
    .then(data => {
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

    _cargarSesion();
    cambiarVista('inicio');
});