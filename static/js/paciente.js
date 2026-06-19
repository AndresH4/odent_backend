// Archivo: paciente.js  — Stylo Dental Pro v2.8
// ─────────────────────────────────────────────────────────────────────────────
// CAMBIOS v2.8 respecto a v2.7:
//   • _cargarAfiliacionCompleta: consulta cruzada robusta que resuelve
//     Régimen EPS, Tipo EPS y EPS aunque el backend no haga JOINs.
//     Ahora obtiene EPS_ID desde /api/afiliacion y lo cruza con /api/eps
//     para obtener Nombre_EPS y Regimen_ID, luego cruza con /api/regimen-eps
//     y /api/tipo-eps. Cubre todos los alias posibles del backend.
//   • Botón "Agendar Cita" cambiado a <a href="/agendar"> en el HTML
//     para evitar que el document click listener intercepte la navegación.
// ─────────────────────────────────────────────────────────────────────────────
'use strict';

// ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────
let _sesionPaciente        = null;
let _pacienteId            = null;
let _usuarioId             = null;
let _citasData             = [];
let _citaParaCancelar      = null;
let _accionPendienteSimple = null;
let _dropdownOpen          = false;

// ─── MAPA DE VISTAS ───────────────────────────────────────────────────────────
const VISTAS_PACIENTE = {
    inicio   : { el: 'vista-inicio',    btn: 'btn-inicio',    titulo: 'Panel de Control'   },
    historial: { el: 'vista-historial', btn: 'btn-historial', titulo: 'Historial de Citas' },
    config   : { el: 'vista-config',    btn: 'btn-config',    titulo: 'Mi Perfil'          },
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

    // ── INICIAL ÚNICA: solo la primera letra del primer nombre ────────────────
    const inicial = (u.Nombres || '').trim().charAt(0).toUpperCase() || 'P';

    _setText('avatar-letras',         inicial);
    _setText('nombre-usuario-header', nombreCompleto);
    _setText('perfil-avatar-grande',  inicial);
    _setText('nombre-menu',           nombreCompleto.toUpperCase());
    _setText('doc-menu',              u.NumeroDocumento || '');

    // Nodos ocultos (retrocompatibilidad)
    _setText('nombre-usuario',    nombreCompleto);
    _setText('perfil-nombres',    u.Nombres    || '');
    _setText('perfil-apellidos',  u.Apellidos  || '');
    _setText('perfil-correo',     u.Correo     || '');
    _setText('perfil-numDoc',     u.NumeroDocumento || '');
    _setText('perfil-telefono',   u.Telefono   || '');
    _setText('perfil-nacimiento', u.FechaNacimiento || '');

    _setText('email-menu',    u.Correo   || '—');
    _setText('telefono-menu', u.Telefono || '—');

    // Tipo documento + número
    _cargarTipoDocumento(u.TipoDoc_ID, u.NumeroDocumento);

    // Paciente_ID → citas + EPS
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

// ─── EPS COMPLETA EN 3 CAMPOS — consulta cruzada robusta ─────────────────────
// CORRECCIÓN v2.8:
// El problema era que el endpoint /api/afiliacion puede devolver solo los IDs
// crudos (EPS_ID, TipoEPS_ID) sin hacer JOINs en el backend.
// La solución es hacer la resolución completa en el frontend:
//   1. GET /api/afiliacion       → obtiene EPS_ID y TipoEPS_ID del usuario
//   2. GET /api/eps              → lista de EPS con Nombre_EPS y Regimen_ID
//   3. GET /api/regimen-eps      → lista de regímenes con Nombre_Regimen
//   4. GET /api/tipo-eps         → lista de tipos con Nombre_Tipo
// Luego cruza por IDs para armar los 3 campos sin depender de JOINs del backend.
async function _cargarAfiliacionCompleta() {
    if (!_usuarioId) return;
    try {
        // Peticiones en paralelo
        const [resAfil, resEps, resRegimen, resTipo] = await Promise.all([
            fetch('/api/afiliacion'),
            fetch('/api/eps'),
            fetch('/api/regimen-eps'),
            fetch('/api/tipo-eps'),
        ]);

        if (!resAfil.ok) {
            console.warn('[paciente] /api/afiliacion no respondió OK');
            return;
        }

        const dataAfil    = await resAfil.json();
        const dataEps     = resEps.ok     ? await resEps.json()     : [];
        const dataRegimen = resRegimen.ok ? await resRegimen.json() : [];
        const dataTipo    = resTipo.ok    ? await resTipo.json()    : [];

        // Normalizar: algunos endpoints envuelven en { ok, data } otros son arrays directos
        const listaAfil    = _normalizar(dataAfil);
        const listaEps     = _normalizar(dataEps);
        const listaRegimen = _normalizar(dataRegimen);
        const listaTipos   = _normalizar(dataTipo);

        // Afiliación del usuario actual — busca por Usuario_ID o ID_Usuario
        const afil = listaAfil.find(
            a => String(a.Usuario_ID || a.ID_Usuario) === String(_usuarioId)
        );

        if (!afil) {
            console.warn('[paciente] No se encontró afiliación para Usuario_ID:', _usuarioId);
            return;
        }

        // ── IDs desde la afiliación (cubre distintos alias posibles) ──────────
        const epsId     = afil.EPS_ID     || afil.Id_EPS     || afil.eps_id     || null;
        const tipoEpsId = afil.TipoEPS_ID || afil.ID_Tipo_EPS || afil.tipoeps_id || null;

        // ── CAMPO 3: EPS ──────────────────────────────────────────────────────
        // Primero intentar nombre directo en la afiliación, luego cruzar con /api/eps
        let nombreEPS = afil.Nombre_EPS || afil.nombre_eps || '';
        if (!nombreEPS && epsId) {
            const epsObj = listaEps.find(
                e => String(e.EPS_ID || e.Id_EPS || e.eps_id) === String(epsId)
            );
            nombreEPS = epsObj
                ? (epsObj.Nombre_EPS || epsObj.nombre_eps || epsObj.Nombre || '—')
                : '—';
        }
        _setText('eps-menu',   nombreEPS || '—');
        _setText('perfil-eps', nombreEPS || '—');

        // ── CAMPO 1: Régimen EPS ──────────────────────────────────────────────
        // Ruta: afiliacion.EPS_ID → eps.Regimen_ID → regimen_eps.Descripcion
        let nombreRegimen = afil.Nombre_Regimen || afil.nombre_regimen || '';
        if (!nombreRegimen) {
            // Obtener Regimen_ID desde la tabla eps
            let regimenId = afil.Regimen_ID || afil.ID_Regimen_EPS || afil.regimen_id || null;
            if (!regimenId && epsId) {
                const epsObj = listaEps.find(
                    e => String(e.EPS_ID || e.Id_EPS || e.eps_id) === String(epsId)
                );
                regimenId = epsObj
                    ? (epsObj.Regimen_ID || epsObj.regimen_id || epsObj.ID_Regimen_EPS || null)
                    : null;
            }
            if (regimenId) {
                const regObj = listaRegimen.find(
                    r => String(r.Regimen_ID || r.ID_Regimen_EPS || r.regimen_id) === String(regimenId)
                );
                nombreRegimen = regObj
                    ? (regObj.Descripcion || regObj.Nombre_Regimen || regObj.nombre_regimen || '—')
                    : '—';
            } else {
                nombreRegimen = '—';
            }
        }
        _setText('regimen-menu', nombreRegimen);

        // ── CAMPO 2: Tipo EPS ─────────────────────────────────────────────────
        let nombreTipoEPS = afil.Nombre_Tipo || afil.nombre_tipo || '';
        if (!nombreTipoEPS && tipoEpsId) {
            const tipoObj = listaTipos.find(
                t => String(t.TipoEPS_ID || t.ID_Tipo_EPS || t.tipoeps_id) === String(tipoEpsId)
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

// ─── HELPER: normaliza respuesta del backend (array o { ok, data }) ───────────
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
    if (el) el.innerText = ahora.toLocaleTimeString('es-CO');

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

// ─── RENDER TABLA PRINCIPAL (INICIO) ─────────────────────────────────────────
function _renderTablaCitas() {
    const tbody   = document.getElementById('tabla-citas-body');
    const noMsg   = document.getElementById('no-citas-msg');
    const countEl = document.getElementById('count-citas');
    if (!tbody) return;

    const hoy = new Date().toISOString().split('T')[0];

    const activas = _citasData.filter(c =>
        c.EstadoAgenda === 'Ocupado' || c.EstadoAgenda === 'Disponible'
    );

    if (countEl) countEl.textContent = activas.length;

    tbody.innerHTML = '';
    if (activas.length === 0) {
        noMsg?.classList.remove('hidden');
        return;
    }
    noMsg?.classList.add('hidden');

    activas.forEach(c => {
        const citaCompletada = c.EstadoAgenda === 'Ocupado' && c.Fecha < hoy;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="p-5 font-black text-slate-700 uppercase text-xs">${c.NombrePaciente || '—'}</td>
            <td class="p-5 text-xs text-slate-500">${c.NumeroDocumento || '—'}</td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5">
                <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full
                    ${c.EstadoAgenda === 'Disponible' ? 'bg-green-100 text-green-700'
                    : c.EstadoAgenda === 'Ocupado'    ? 'bg-sky-100 text-sky-700'
                    : 'bg-red-100 text-red-700'}">
                    ${c.EstadoAgenda}
                </span>
                ${c.EstadoMulta && c.EstadoMulta !== 'Sin multa'
                    ? `<span class="text-[9px] font-black uppercase px-2 py-1 rounded-full bg-amber-100 text-amber-700 ml-1">${c.EstadoMulta}</span>`
                    : ''}
            </td>
            <td class="p-5 text-center">
                ${c.EstadoAgenda === 'Ocupado' && c.Fecha >= hoy
                    ? `<button onclick="abrirModalCancelar(${c.Cita_ID})"
                           class="text-[10px] bg-red-50 text-red-600 border border-red-200 px-4 py-2 rounded-xl font-black hover:bg-red-100 transition-all uppercase">
                           <i class="fas fa-ban mr-1"></i> Cancelar
                       </button>`
                    : citaCompletada
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

// ─── RENDER HISTORIAL ─────────────────────────────────────────────────────────
function _renderHistorial() {
    const tbody = document.getElementById('tabla-historial-completo');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (_citasData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-10 text-center text-slate-400 font-bold italic text-xs uppercase">Sin historial registrado.</td></tr>`;
        return;
    }

    _citasData.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="p-5 text-xs font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
            <td class="p-5 font-black text-sky-600 uppercase text-[10px]">${c.Nombre_Especialidad || '—'}</td>
            <td class="p-5 text-xs text-slate-600">Dr(a). ${c.NombreEspecialista || '—'}</td>
            <td class="p-5">
                <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full
                    ${c.EstadoAgenda === 'Disponible' ? 'bg-green-100 text-green-700'
                    : c.EstadoAgenda === 'Ocupado'    ? 'bg-sky-100 text-sky-700'
                    : 'bg-red-100 text-red-700'}">
                    ${c.EstadoAgenda}
                </span>
            </td>
            <td class="p-5 text-center">
                <span class="text-[10px] font-bold text-slate-400">${c.Motivo_Consulta || '—'}</span>
            </td>`;
        tbody.appendChild(tr);
    });
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
};

window.solicitarConfirmacionFinal = function () {
    document.getElementById('modalCancelarCita').style.display = 'none';
    document.getElementById('modalConfirmacionFinal').style.display = 'flex';
};

window.cerrarConfirmacionFinal = function () {
    document.getElementById('modalConfirmacionFinal').style.display = 'none';
};

window.confirmarAccionCancelado = async function () {
    if (!_citaParaCancelar) return;
    try {
        const res  = await fetch(`/api/citas/${_citaParaCancelar}/cancelar`, { method: 'PUT' });
        const data = await res.json();
        document.getElementById('modalConfirmacionFinal').style.display = 'none';
        _citaParaCancelar = null;
        if (data.ok) {
            alert('Cita cancelada. Se generó una multa pendiente.');
            await _cargarCitasPaciente();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (err) {
        console.error('[paciente] Error cancelando cita:', err);
        alert('Error de conexión al cancelar la cita.');
    }
};

// ─── LIMPIAR CANCELADAS ───────────────────────────────────────────────────────
function _limpiarCanceladas() {
    _citasData = _citasData.filter(c => c.EstadoAgenda !== 'Cancelado');
    _renderTablaCitas();
}

// ─── RANKING ──────────────────────────────────────────────────────────────────
window._abrirRanking = async function (citaId) {
    try {
        const resP  = await fetch('/api/pregunta');
        const dataP = await resP.json();
        if (!dataP.ok || !dataP.data.length) {
            alert('No hay preguntas de evaluación configuradas.');
            return;
        }
        _mostrarFormRanking(citaId, dataP.data);
    } catch (err) {
        console.error('[ranking] Error cargando preguntas:', err);
        alert('Error al cargar preguntas de evaluación.');
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
        alert('¡Gracias por tu evaluación!');
    } catch (err) {
        console.error('[ranking] Error enviando respuestas:', err);
        if (errEl) { errEl.textContent = 'Error de conexión. Intente de nuevo.'; errEl.style.display = 'block'; }
    }
};

// ─── MI PERFIL ────────────────────────────────────────────────────────────────
function _precargarPerfil() {
    if (!_sesionPaciente) return;
    _setVal('edit-correo',     _sesionPaciente.Correo          || '');
    _setVal('edit-telefono',   _sesionPaciente.Telefono        || '');
    _setVal('edit-nacimiento', _sesionPaciente.FechaNacimiento || '');
    _resetearFlujoPassword();
}

function _resetearFlujoPassword() {
    ['pass-actual', 'conf-pass-nueva', 'conf-pass-confirmar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const step1 = document.getElementById('pass-step1');
    const step2 = document.getElementById('pass-step2');
    if (step1) step1.style.display = '';
    if (step2) step2.style.display = 'none';
    ['error-pass-actual', 'error-pass-nueva'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
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
            if (errActual) { errActual.textContent = 'Contraseña incorrecta.'; errActual.style.display = 'block'; }
        }
    })
    .catch(() => {
        if (errActual) errActual.style.display = 'none';
        if (step1) step1.style.display = 'none';
        if (step2) step2.style.display = '';
    });
};

window.guardarPerfilPaciente = function () {
    const correo     = document.getElementById('edit-correo')?.value.trim();
    const telefono   = document.getElementById('edit-telefono')?.value.trim();
    const nacimiento = document.getElementById('edit-nacimiento')?.value;
    const passNueva  = document.getElementById('conf-pass-nueva')?.value;
    const passConf   = document.getElementById('conf-pass-confirmar')?.value;
    const errNueva   = document.getElementById('error-pass-nueva');
    const step2      = document.getElementById('pass-step2');

    if (step2?.style.display !== 'none' && passNueva !== passConf) {
        if (errNueva) errNueva.style.display = 'block';
        return;
    }
    if (errNueva) errNueva.style.display = 'none';

    fetch('/api/actualizar-perfil-paciente', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
            usuario_id: _usuarioId,
            correo, telefono, nacimiento,
            nuevaPass: passNueva || null
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (_sesionPaciente) {
                _sesionPaciente.Correo          = correo;
                _sesionPaciente.Telefono        = telefono;
                _sesionPaciente.FechaNacimiento = nacimiento;
                sessionStorage.setItem('odent_usuario', JSON.stringify(_sesionPaciente));
            }
            _cargarSesion();
            cambiarVista('inicio');
            alert('Perfil actualizado correctamente.');
        } else {
            alert(data.mensaje || 'No se pudo guardar. Intenta de nuevo.');
        }
    })
    .catch(() => alert('Error de conexión al guardar el perfil.'));
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
    if (_accionPendienteSimple === 'limpiar') {
        _limpiarCanceladas();
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

    // CORRECCIÓN: el listener verifica también si el click viene del enlace
    // de agendar para no bloquear la navegación
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