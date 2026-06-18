/**
 * administrador.js — Stylo Dental
 * Lee la sesión guardada por login.js, muestra el saludo y carga datos reales
 * desde la API Flask en lugar de localStorage.
 */

'use strict';

// ─── Variables de módulo ─────────────────────────────────────────────────────
let adminData = {};

// ─── Utilidades ──────────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function mostrarToast(msg) {
    // Reutiliza un toast si existe en el HTML, si no usa alert
    const t = document.getElementById('toast');
    if (t) { t.textContent = msg; t.classList.add('visible'); setTimeout(() => t.classList.remove('visible'), 3000); }
    else alert(msg);
}

// ─── Sesión ──────────────────────────────────────────────────────────────────
function cargarSesion() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) { window.location.replace('/login'); return; }

    const u = JSON.parse(raw);
    if (u.Rol_ID !== 1) { window.location.replace('/login'); return; }

    const nombre = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
    adminData = { nombre, email: u.Correo, tel: u.Telefono, id: u.Usuario_ID };

    // Saludo visible en el header
    setText('header-name', nombre);
    setText('drop-name',   nombre);
    setText('drop-email',  u.Correo);
    setText('drop-tel',    u.Telefono || '—');

    const pic = document.getElementById('header-pic');
    if (pic) pic.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nombre)}&background=0284c7&color=fff&size=128`;

    actualizarStats();
}

function cerrarSesion() {
    sessionStorage.removeItem('odent_usuario');
    window.location.replace('/login');
}

// ─── Reloj ───────────────────────────────────────────────────────────────────
function actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();    // 0 = domingo … 6 = sábado
    const horas = ahora.getHours();

    const elReloj = document.getElementById('reloj');
    if (elReloj) elReloj.innerText = ahora.toLocaleTimeString('es-CO');

// ─── Módulo EPS: Reporte de afiliados por EPS ────────────────────────────────
/**
 * Consume GET /api/reporte/afiliados-por-eps del modulo_eps.
 * Calcula el total de afiliados y lo muestra en stat-total.
 */
async function cargarReporteAfiliados() {
    try {
        const res  = await fetch('/api/reporte/afiliados-por-eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        const totalAfiliados = data.data.reduce(
            (acc, eps) => acc + (eps.Total_Afiliados || 0), 0
        );
        setText('stat-total', totalAfiliados);
    } catch (e) {
        console.error('[admin/modulo_eps] Error cargando reporte afiliados:', e);
    }
}

// ─── Módulo EPS: Lista enriquecida de pacientes con EPS ──────────────────────
/**
 * Consume GET /api/paciente del modulo_eps.
 * Retorna el array con datos clínicos, EPS y estado de afiliación de cada paciente.
 */
async function cargarPacientesEPS() {
    try {
        const res  = await fetch('/api/paciente');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        return data.data;
    } catch (e) {
        console.error('[admin/modulo_eps] Error cargando pacientes EPS:', e);
        return [];
    }
}

// ─── Estadísticas (desde API) ────────────────────────────────────────────────
async function actualizarStats() {
    try {
        const res  = await fetch('/api/usuarios');
        const data = await res.json();

        const especialistas = data.filter(u => u.Rol_ID === 2);
        const pacientes     = data.filter(u => u.Rol_ID === 3);

        setText('stat-esp', especialistas.length);
        setText('stat-pac', pacientes.length);
    } catch (e) {
        console.error('[admin] Error cargando stats:', e);
    }

    // Módulo EPS: poblar stat-total con el total real de afiliados
    await cargarReporteAfiliados();
}

// ─── Lista dinámica de usuarios ──────────────────────────────────────────────
async function renderUsuarios(rolNombre) {
    const rolMap = { 'Especialista': 2, 'Paciente': 3 };
    const rolId  = rolMap[rolNombre];

    try {
        const res  = await fetch('/api/usuarios');
        const data = await res.json();
        const filtrados = data.filter(u => u.Rol_ID === rolId);

        // Módulo EPS: enriquecer pacientes con su EPS y estado de afiliación
        let pacientesEPS = [];
        if (rolNombre === 'Paciente') {
            pacientesEPS = await cargarPacientesEPS();
        }

        const body = document.getElementById('body-lista-dinamica');
        const cont = document.getElementById('container-lista-rapida');
        const tit  = document.getElementById('titulo-lista-dinamica');

        if (!body || !cont || !tit) return;
        cont.classList.remove('hidden');
        tit.textContent = `GESTIÓN: ${rolNombre.toUpperCase()}S`;

        body.innerHTML = filtrados.map(u => {
            // Buscar el registro de paciente EPS que corresponde a este usuario
            const datosEPS   = pacientesEPS.find(
                p => String(p.ID_Usuario) === String(u.ID_Usuario || u.Usuario_ID)
            );
            const epsNombre  = datosEPS ? (datosEPS.Nombre_EPS        || '—') : '—';
            const estadoAfil = datosEPS ? (datosEPS.Estado_Afiliacion || '—') : '—';

            return `
            <tr class="p-4 flex justify-between items-center px-8 hover:bg-sky-50/50 transition-all">
                <td>
                    <p class="font-black text-slate-800 text-[11px] uppercase">${u.Nombres} ${u.Apellidos}</p>
                    <p class="text-[9px] text-slate-400 font-bold">${u.Correo}</p>
                    ${rolNombre === 'Paciente'
                        ? `<p class="text-[9px] text-sky-500 font-bold mt-1">
                               <i class="fas fa-shield-alt mr-1"></i>${epsNombre}
                           </p>`
                        : ''}
                </td>
                <td>
                    <span class="text-[9px] font-bold uppercase px-2 py-1 rounded-full ${u.Estado_ID === 1 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                        ${u.Estado_ID === 1 ? 'Activo' : 'Inactivo'}
                    </span>
                    ${rolNombre === 'Paciente' && estadoAfil !== '—'
                        ? `<br><span class="text-[8px] font-bold uppercase px-2 py-1 rounded-full bg-sky-100 text-sky-700 mt-1 inline-block">${estadoAfil}</span>`
                        : ''}
                </td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('[admin] Error cargando usuarios:', e);
    }
}

// ─── Ocultar lista rápida (llamada desde el HTML) ─────────────────────────────
function ocultarListaRapida() {
    const cont = document.getElementById('container-lista-rapida');
    if (cont) cont.classList.add('hidden');
}

// ─── Filtrar tabla de citas (llamada desde el HTML) ───────────────────────────
function filtrarTablaCitas() {
    const filtro = (document.getElementById('busqueda-citas')?.value || '').toLowerCase();
    document.querySelectorAll('#tabla-body tr').forEach(fila => {
        fila.style.display = fila.textContent.toLowerCase().includes(filtro) ? '' : 'none';
    });
}

// ─── Historial de citas (desde API) ──────────────────────────────────────────
async function renderCitas() {
    setText('main-title', 'Historial General de Citas');
    try {
        const res  = await fetch('/api/citas');
        const data = await res.json();

        const head = document.getElementById('tabla-head');
        const body = document.getElementById('tabla-body');
        if (!head || !body) return;

        head.innerHTML = `
            <tr>
                <th class="p-6">Paciente</th>
                <th class="p-6">Especialista</th>
                <th class="p-6">Especialidad</th>
                <th class="p-6">Fecha / Hora</th>
                <th class="p-6">Estado</th>
            </tr>`;

        body.innerHTML = data.map(c => `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="p-6 font-bold text-slate-800 text-[11px] uppercase">${c.NombrePaciente}</td>
                <td class="p-6 text-[10px] font-black text-slate-600 uppercase">
                    <i class="fas fa-user-md mr-2 text-sky-500"></i>${c.NombreEspecialista}
                </td>
                <td class="p-6 text-sky-600 font-black text-[10px] uppercase">${c.Nombre_Especialidad || '—'}</td>
                <td class="p-6 text-[10px] font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio}</span></td>
                <td class="p-6">
                    <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full 
                        ${c.EstadoAgenda === 'Disponible' ? 'bg-green-100 text-green-700'
                        : c.EstadoAgenda === 'Ocupado'    ? 'bg-sky-100 text-sky-700'
                        : 'bg-red-100 text-red-700'}">
                        ${c.EstadoAgenda}
                    </span>
                </td>
            </tr>`).join('');
    } catch (e) {
        console.error('[admin] Error cargando citas:', e);
    }
}

// ─── Navegación de secciones ─────────────────────────────────────────────────
function cambiarSeccion(sec) {
    const dash   = document.getElementById('sec-dashboard');
    const tablas = document.getElementById('sec-tablas');

    if (dash)   dash.classList.toggle('hidden',   sec !== 'dashboard');
    if (tablas) tablas.classList.toggle('hidden',  sec === 'dashboard');

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btnActivo = document.getElementById(`btn-${sec}`);
    if (btnActivo) btnActivo.classList.add('active');

    if (sec === 'citas') renderCitas();
}

// ─── Perfil (modal de configuración) ─────────────────────────────────────────
function toggleProfileDropdown() {
    document.getElementById('profileDropdown')?.classList.toggle('active');
}

window.addEventListener('click', (e) => {
    if (!e.target.closest('#profileDropdown') && !e.target.closest('header .cursor-pointer')) {
        document.getElementById('profileDropdown')?.classList.remove('active');
    }
});

function abrirConfiguracion() {
    document.getElementById('edit-nombre').value = adminData.nombre || '';
    document.getElementById('edit-email').value  = adminData.email  || '';
    document.getElementById('edit-tel').value    = adminData.tel    || '';
    document.getElementById('modalConfig').style.display = 'flex';
}

function cerrarConfiguracion() {
    document.getElementById('modalConfig').style.display = 'none';
    const s1 = document.getElementById('step-1');
    const s2 = document.getElementById('step-2');
    if (s1) s1.classList.remove('hidden');
    if (s2) s2.classList.add('hidden');
}

async function guardarPerfil() {
    adminData.nombre = document.getElementById('edit-nombre').value.trim();
    adminData.email  = document.getElementById('edit-email').value.trim();
    adminData.tel    = document.getElementById('edit-tel').value.trim();

    // Actualizar sesión local
    const raw = sessionStorage.getItem('odent_usuario');
    if (raw) {
        const u = JSON.parse(raw);
        u.Nombres  = adminData.nombre.split(' ')[0] || u.Nombres;
        u.Apellidos = adminData.nombre.split(' ').slice(1).join(' ') || u.Apellidos;
        u.Correo   = adminData.email;
        u.Telefono = adminData.tel;
        sessionStorage.setItem('odent_usuario', JSON.stringify(u));
    }

    mostrarToast('PERFIL ACTUALIZADO');
    cerrarConfiguracion();
    cargarSesion();
}

function verificarOldPass() {
    // Verificación local simple (en producción esto iría al backend)
    const ingresada = document.getElementById('old-pass').value;
    if (ingresada && ingresada.length >= 6) {
        document.getElementById('step-1').classList.add('hidden');
        document.getElementById('step-2').classList.remove('hidden');
    } else {
        alert('Contraseña inválida o muy corta.');
    }
}

function togglePass(id) {
    const el = document.getElementById(id);
    if (el) el.type = el.type === 'password' ? 'text' : 'password';
}

// ─── Modal confirmación simple ────────────────────────────────────────────────
window.mostrarConfirmacionSimple = function (mensaje, accion) {
    accionPendienteSimple = accion;
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');
    if (texto) texto.textContent = mensaje;
    if (modal) modal.style.display = 'flex';
};

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

const cerrarSesion = () => mostrarConfirmacionSimple('¿Quiere salir de la sesión?', 'salir');
// ─── Init ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    cargarSesion();
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
});