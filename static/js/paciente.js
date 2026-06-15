/**
 * paciente.js — Stylo Dental
 * Lee la sesión de sessionStorage, muestra el saludo con el nombre real
 * y consume la API Flask para citas (sin localStorage).
 */

'use strict';

// ─── Estado de módulo ─────────────────────────────────────────────────────────
let sesionUsuario   = null;
let pacienteId      = null;
let accionPendiente = null;
let indexPendiente  = null;
let citasCache      = [];

// ─── Utilidades ──────────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function actualizarReloj() {
    const el = document.getElementById('reloj');
    if (el) el.textContent = new Date().toLocaleTimeString('es-CO');
}

// ─── Sesión ──────────────────────────────────────────────────────────────────
async function cargarSesion() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) { window.location.replace('/login'); return; }

    const u = JSON.parse(raw);
    if (u.Rol_ID !== 3) { window.location.replace('/login'); return; }

    sesionUsuario = u;

    // Saludo personalizado
    const primerNombre = (u.Nombres || 'Paciente').split(' ')[0];
    setText('nombre-usuario', primerNombre);

    // Avatar con iniciales
    const iniciales = `${(u.Nombres || '?')[0]}${(u.Apellidos || '?')[0]}`.toUpperCase();
    setText('avatar-letras', iniciales);

    // Obtener Paciente_ID a partir del Usuario_ID
    try {
        const res  = await fetch(`/api/usuarios/${u.Usuario_ID}`);
        const data = await res.json();
        // El endpoint devuelve al usuario; buscamos su Paciente_ID via la lista
        // Usar endpoint de paciente por usuario
        const resPac = await fetch(`/api/paciente/por-usuario/${u.Usuario_ID}`);
        if (resPac.ok) {
            const pac = await resPac.json();
            pacienteId = pac.Paciente_ID;
        }
    } catch (e) {
        console.error('[paciente] No se pudo obtener Paciente_ID:', e);
    }

    cargarCitas();
}

function cerrarSesion() {
    sessionStorage.removeItem('odent_usuario');
    window.location.replace('/login');
}

// ─── Navegación ───────────────────────────────────────────────────────────────
function cambiarVista(vista) {
    const inicio    = document.getElementById('vista-inicio');
    const historial = document.getElementById('vista-historial');
    const btnIn     = document.getElementById('btn-inicio');
    const btnHis    = document.getElementById('btn-historial');
    const titulo    = document.getElementById('titulo-principal');

    const esInicio = vista === 'inicio';
    inicio?.classList.toggle('hidden', !esInicio);
    historial?.classList.toggle('hidden', esInicio);
    btnIn?.classList.toggle('active', esInicio);
    btnHis?.classList.toggle('active', !esInicio);

    if (titulo) titulo.textContent = esInicio ? 'Panel de Control' : 'Historial Completo';

    if (esInicio) cargarCitas();
    else          renderHistorial();
}

// ─── Carga de citas desde API ────────────────────────────────────────────────
async function cargarCitas() {
    if (!pacienteId) return;

    try {
        const res  = await fetch(`/api/paciente/${pacienteId}/citas`);
        citasCache = await res.json();

        const tbody     = document.getElementById('tabla-citas-body');
        const countEl   = document.getElementById('count-citas');
        const noMsgEl   = document.getElementById('no-citas-msg');
        if (!tbody) return;

        tbody.innerHTML = '';

        // Solo mostramos las vigentes (no canceladas) en la vista principal
        const vigentes = citasCache.filter(c =>
            c.EstadoAgenda !== 'Cancelado'
        );

        if (countEl) countEl.textContent = vigentes.length;
        if (noMsgEl) noMsgEl.classList.toggle('hidden', vigentes.length > 0);

        vigentes.forEach((c, i) => {
            const badge = c.EstadoAgenda === 'Disponible' || c.EstadoAgenda === 'Ocupado'
                ? 'status-agendada'
                : 'status-cancelada';

            tbody.insertAdjacentHTML('afterbegin', `
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="p-5 font-black text-slate-800 uppercase text-xs">
                        ${sesionUsuario?.Nombres} ${sesionUsuario?.Apellidos}
                    </td>
                    <td class="p-5 text-[10px] font-bold uppercase">
                        ${sesionUsuario?.NumeroDocumento || '—'}
                    </td>
                    <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">
                        ${c.Nombre_Especialidad || '—'}
                    </td>
                    <td class="p-5 font-bold uppercase text-xs">
                        ${c.Fecha}<br>
                        <span class="text-slate-400 text-[10px]">${c.Hora_Inicio}</span>
                    </td>
                    <td class="p-5"><span class="${badge}">${c.EstadoAgenda}</span></td>
                    <td class="p-5 text-center">
                        ${c.EstadoAgenda === 'Ocupado'
                            ? `<button onclick="iniciarCancelacion(${c.Cita_ID})"
                                class="text-red-400 hover:text-red-600 p-2 transition-transform hover:scale-125">
                                <i class="fas fa-ban"></i></button>`
                            : '<span class="text-slate-300 text-xs">—</span>'
                        }
                    </td>
                </tr>`);
        });

    } catch (e) {
        console.error('[paciente] Error cargando citas:', e);
    }
}

// ─── Historial completo ───────────────────────────────────────────────────────
function renderHistorial() {
    const tbody = document.getElementById('tabla-historial-completo');
    if (!tbody) return;
    tbody.innerHTML = '';

    [...citasCache].reverse().forEach(c => {
        let badgeClass = 'status-agendada';
        if (c.EstadoAgenda === 'Cancelado') badgeClass = 'status-cancelada';

        tbody.insertAdjacentHTML('beforeend', `
            <tr class="hover:bg-slate-50">
                <td class="p-5 font-bold text-slate-700">
                    ${c.Fecha}<br>
                    <span class="text-[10px] text-slate-400 font-black">${c.Hora_Inicio}</span>
                </td>
                <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">
                    ${c.Nombre_Especialidad || '—'}
                </td>
                <td class="p-5 font-bold uppercase text-xs text-slate-500">
                    ${c.NombreEspecialista}
                </td>
                <td class="p-5"><span class="${badgeClass}">${c.EstadoAgenda}</span></td>
                <td class="p-5 text-center">
                    <span class="text-[9px] font-bold ${c.EstadoMulta === 'Pendiente' ? 'text-orange-600' : 'text-green-600'}">
                        ${c.EstadoMulta}
                    </span>
                </td>
            </tr>`);
    });
}

// ─── Cancelación de cita ──────────────────────────────────────────────────────
let citaACancelarId = null;

function iniciarCancelacion(citaId) {
    citaACancelarId = citaId;
    const cita = citasCache.find(c => c.Cita_ID === citaId);
    if (!cita) return;

    document.getElementById('detalles-completos').innerHTML = `
        <div><p class="data-label">Nombre</p>
             <p class="data-value uppercase">${sesionUsuario?.Nombres} ${sesionUsuario?.Apellidos}</p></div>
        <div><p class="data-label">Especialidad</p>
             <p class="data-value uppercase text-sky-700 font-black">${cita.Nombre_Especialidad || '—'}</p></div>
        <div><p class="data-label">Fecha</p><p class="data-value">${cita.Fecha}</p></div>
        <div><p class="data-label">Hora</p><p class="data-value">${cita.Hora_Inicio}</p></div>
    `;
    document.getElementById('modalCancelarCita').style.display = 'flex';
}

function solicitarConfirmacionFinal() {
    document.getElementById('modalCancelarCita').style.display   = 'none';
    document.getElementById('modalConfirmacionFinal').style.display = 'flex';
}

async function confirmarAccionCancelado() {
    cerrarConfirmacionFinal();
    if (!citaACancelarId) return;

    try {
        const res = await fetch(`/api/citas/${citaACancelarId}/cancelar`, { method: 'PUT' });
        const data = await res.json();
        if (data.ok) {
            alert('Cita cancelada. Se ha generado una multa.');
            cargarCitas();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (e) {
        alert('No se pudo cancelar la cita. Intente de nuevo.');
    }
}

function cerrarConfirmacionFinal() { document.getElementById('modalConfirmacionFinal').style.display = 'none'; }
function cerrarModalCancelar()     { document.getElementById('modalCancelarCita').style.display      = 'none'; }

// ─── Modal perfil ─────────────────────────────────────────────────────────────
function abrirModalPerfil() {
    const u = sesionUsuario;
    if (!u) return;
    const iniciales = `${(u.Nombres || '?')[0]}${(u.Apellidos || '?')[0]}`.toUpperCase();
    setText('perfil-avatar-grande', iniciales);
    setText('perfil-nombres',   u.Nombres  || '—');
    setText('perfil-apellidos', u.Apellidos || '—');
    setText('perfil-correo',    u.Correo    || '—');
    setText('perfil-numDoc',    u.NumeroDocumento || '—');
    document.getElementById('modalPerfil').style.display = 'flex';
}
function cerrarModalPerfil() { document.getElementById('modalPerfil').style.display = 'none'; }

// ─── Modal configuración ──────────────────────────────────────────────────────
function abrirConfiguracion() {
    const u = sesionUsuario;
    if (u) {
        const el = (id) => document.getElementById(id);
        if (el('edit-correo'))    el('edit-correo').value    = u.Correo    || '';
        if (el('edit-telefono'))  el('edit-telefono').value  = u.Telefono  || '';
    }
    cerrarModalPerfil();
    document.getElementById('modalConfig').style.display = 'flex';
}

function cerrarConfiguracion() { document.getElementById('modalConfig').style.display = 'none'; }

async function guardarConfiguracionGeneral() {
    const nuevoCorreo = document.getElementById('edit-correo')?.value.trim();
    const nuevaPass   = document.getElementById('nueva-pass')?.value;
    const confirmar   = document.getElementById('confirmar-pass')?.value;

    if (!nuevoCorreo) { alert('El correo es obligatorio.'); return; }
    if (nuevaPass && nuevaPass.length < 6) { alert('La contraseña debe tener mínimo 6 caracteres.'); return; }
    if (nuevaPass && nuevaPass !== confirmar) { alert('Las contraseñas no coinciden.'); return; }

    // Actualizar sesión local
    if (sesionUsuario) {
        sesionUsuario.Correo = nuevoCorreo;
        sessionStorage.setItem('odent_usuario', JSON.stringify(sesionUsuario));
    }

    alert('Perfil actualizado.');
    cerrarConfiguracion();
}

// ─── Modal confirmación simple ────────────────────────────────────────────────
function mostrarConfirmacionSimple(mensaje, tipo, index = null) {
    accionPendiente = tipo;
    indexPendiente  = index;
    setText('confirm-text-simple', mensaje);
    document.getElementById('modalConfirmarSimple').style.display = 'flex';
}

function cerrarModalSimple() { document.getElementById('modalConfirmarSimple').style.display = 'none'; }

function ejecutarAccionSimple() {
    cerrarModalSimple();
    if (accionPendiente === 'salir') cerrarSesion();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    cargarSesion();
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
});

window.onfocus = () => { if (pacienteId) cargarCitas(); };