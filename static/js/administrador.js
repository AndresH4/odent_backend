// Archivo: administrador.js
'use strict';

// ─── Variables de módulo ─────────────────────────────────────────────────────
let adminData              = {};
let _accionPendienteSimple = '';

// ─── Utilidades ──────────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function mostrarToast(msg) {
    const t = document.getElementById('toast');
    if (t) { t.textContent = msg; t.classList.add('visible'); setTimeout(() => t.classList.remove('visible'), 3000); }
    else alert(msg);
}

// ─── Sesión — sessionStorage.getItem('odent_usuario') ────────────────────────
function cargarSesion() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) { window.location.replace('/login'); return; }

    const u = JSON.parse(raw);
    if (u.Rol_ID !== 1) { window.location.replace('/login'); return; }

    const nombre = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
    adminData = { nombre, email: u.Correo, tel: u.Telefono, id: u.Usuario_ID };

    setText('header-name', nombre);
    setText('drop-name',   nombre);
    setText('drop-email',  u.Correo);
    setText('drop-tel',    u.Telefono || '—');

    actualizarStats();
}

// ─── Reloj ───────────────────────────────────────────────────────────────────
function actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();
    const horas = ahora.getHours();

    const elReloj = document.getElementById('reloj');
    if (elReloj) elReloj.innerText = ahora.toLocaleTimeString('es-CO');

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

// ─── GET /api/reporte/afiliados-por-eps (modulo_eps) ─────────────────────────
async function cargarReporteAfiliados() {
    try {
        const res  = await fetch('/api/reporte/afiliados-por-eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        const totalAfiliados = data.data.reduce((acc, eps) => acc + (eps.Total_Afiliados || 0), 0);
        setText('stat-total', totalAfiliados);
    } catch (e) {
        console.error('[admin/modulo_eps] Error cargando reporte afiliados:', e);
    }
}

// ─── GET /api/paciente (modulo_eps) ──────────────────────────────────────────
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

// ─── GET /api/usuarios + /api/citas — estadísticas dashboard ─────────────────
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

    // GET /api/citas — citas de hoy
    try {
        const res  = await fetch('/api/citas');
        const data = await res.json();
        const hoy  = new Date().toISOString().split('T')[0];
        const citasHoy = Array.isArray(data) ? data.filter(c => c.Fecha === hoy) : [];
        setText('stat-citas-hoy', citasHoy.length);
    } catch (e) {
        console.error('[admin] Error cargando citas hoy:', e);
    }

    await cargarReporteAfiliados();
}

// ─── Lista dinámica — GET /api/usuarios + GET /api/paciente ──────────────────
async function renderUsuarios(rolNombre) {
    const rolMap = { 'Especialista': 2, 'Paciente': 3 };
    const rolId  = rolMap[rolNombre];

    try {
        const res      = await fetch('/api/usuarios');
        const data     = await res.json();
        const filtrados = data.filter(u => u.Rol_ID === rolId);

        let pacientesEPS = [];
        if (rolNombre === 'Paciente') pacientesEPS = await cargarPacientesEPS();

        const body  = document.getElementById('body-lista-dinamica');
        const cont  = document.getElementById('container-lista-rapida');
        const tit   = document.getElementById('titulo-lista-dinamica');
        const head  = document.getElementById('head-lista-dinamica');

        if (!body || !cont || !tit) return;

        cont.classList.remove('seccion-oculta');
        cont.classList.add('seccion-visible');
        tit.textContent = `GESTIÓN: ${rolNombre.toUpperCase()}S`;

        if (head) {
            head.innerHTML = rolNombre === 'Paciente'
                ? '<th class="p-5">Paciente</th><th class="p-5">Estado</th><th class="p-5">EPS</th>'
                : '<th class="p-5">Especialista</th><th class="p-5">Estado</th>';
        }

        body.innerHTML = '';
        if (filtrados.length === 0) {
            document.getElementById('no-datos-lista')?.classList.remove('hidden');
            return;
        }
        document.getElementById('no-datos-lista')?.classList.add('hidden');

        filtrados.forEach(u => {
            const datosEPS   = pacientesEPS.find(p => String(p.ID_Usuario) === String(u.Usuario_ID));
            const epsNombre  = datosEPS ? (datosEPS.Nombre_EPS        || '—') : '—';
            const estadoAfil = datosEPS ? (datosEPS.Estado_Afiliacion || '—') : '—';
            const tr         = document.createElement('tr');
            tr.className     = 'hover:bg-sky-50/50 transition-all';
            tr.innerHTML = `
                <td class="p-5">
                    <p class="font-black text-slate-800 text-[11px] uppercase">${u.Nombres} ${u.Apellidos}</p>
                    <p class="text-[9px] text-slate-400 font-bold">${u.Correo}</p>
                    ${rolNombre === 'Paciente'
                        ? `<p class="text-[9px] text-sky-500 font-bold mt-1"><i class="fas fa-shield-alt mr-1"></i>${epsNombre}</p>`
                        : ''}
                </td>
                <td class="p-5">
                    <span class="text-[9px] font-bold uppercase px-2 py-1 rounded-full
                        ${u.Estado_ID === 1 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                        ${u.Estado_ID === 1 ? 'Activo' : 'Inactivo'}
                    </span>
                    ${rolNombre === 'Paciente' && estadoAfil !== '—'
                        ? `<br><span class="text-[8px] font-bold uppercase px-2 py-1 rounded-full bg-sky-100 text-sky-700 mt-1 inline-block">${estadoAfil}</span>`
                        : ''}
                </td>
                ${rolNombre === 'Paciente' ? `<td class="p-5 text-[10px] font-bold text-slate-500">${epsNombre}</td>` : ''}`;
            body.appendChild(tr);
        });
    } catch (e) {
        console.error('[admin] Error cargando usuarios:', e);
    }
}

function ocultarListaRapida() {
    const cont = document.getElementById('container-lista-rapida');
    if (cont) {
        cont.classList.remove('seccion-visible');
        cont.classList.add('seccion-oculta');
    }
}

// ─── Filtrar tabla de citas ───────────────────────────────────────────────────
function filtrarTablaCitas() {
    const filtro = (document.getElementById('busqueda-citas')?.value || '').toLowerCase();
    document.querySelectorAll('#tabla-body tr').forEach(fila => {
        fila.style.display = fila.textContent.toLowerCase().includes(filtro) ? '' : 'none';
    });
}

// ─── GET /api/citas ───────────────────────────────────────────────────────────
async function renderCitas() {
    try {
        const res  = await fetch('/api/citas');
        const data = await res.json();

        const head = document.getElementById('tabla-head');
        const body = document.getElementById('tabla-body');
        const noD  = document.getElementById('no-datos');
        if (!head || !body) return;

        head.innerHTML = `
            <tr>
                <th class="p-6">Paciente</th>
                <th class="p-6">Especialista</th>
                <th class="p-6">Especialidad</th>
                <th class="p-6">Fecha / Hora</th>
                <th class="p-6">Estado</th>
                <th class="p-6 text-center">Multa</th>
            </tr>`;

        const citas = Array.isArray(data) ? data : [];

        if (citas.length === 0) { noD?.classList.remove('hidden'); return; }
        noD?.classList.add('hidden');

        body.innerHTML = citas.map(c => `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="p-6 font-bold text-slate-800 text-[11px] uppercase">${c.NombrePaciente || '—'}</td>
                <td class="p-6 text-[10px] font-black text-slate-600 uppercase">
                    <i class="fas fa-user-md mr-2 text-sky-500"></i>${c.NombreEspecialista || '—'}
                </td>
                <td class="p-6 text-sky-600 font-black text-[10px] uppercase">${c.Nombre_Especialidad || '—'}</td>
                <td class="p-6 text-[10px] font-bold">${c.Fecha}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
                <td class="p-6">
                    <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full
                        ${c.EstadoAgenda === 'Disponible' ? 'bg-green-100 text-green-700'
                        : c.EstadoAgenda === 'Ocupado'    ? 'bg-sky-100 text-sky-700'
                        : 'bg-red-100 text-red-700'}">
                        ${c.EstadoAgenda || '—'}
                    </span>
                </td>
                <td class="p-6 text-center">—</td>
            </tr>`).join('');

    } catch (e) {
        console.error('[admin] Error cargando citas:', e);
    }
}

// ─── GET /api/multas ──────────────────────────────────────────────────────────
async function renderMultas() {
    try {
        const res  = await fetch('/api/multas');
        const data = await res.json();
        const multas = Array.isArray(data) ? data : [];

        const head = document.getElementById('tabla-head');
        const body = document.getElementById('tabla-body');
        const noD  = document.getElementById('no-datos');
        if (!head || !body) return;

        head.innerHTML = `
            <tr>
                <th class="p-6">ID Multa</th>
                <th class="p-6">Paciente</th>
                <th class="p-6">Fecha Cita</th>
                <th class="p-6">Estado Multa</th>
                <th class="p-6 text-center">Acción</th>
            </tr>`;

        if (multas.length === 0) { noD?.classList.remove('hidden'); return; }
        noD?.classList.add('hidden');

        body.innerHTML = multas.map(m => `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="p-6 font-black text-slate-700 text-[11px]">#${m.Multa_ID}</td>
                <td class="p-6 font-bold text-slate-800 text-[11px] uppercase">${m.NombrePaciente || '—'}</td>
                <td class="p-6 text-[10px] font-bold">${m.Fecha || '—'}<br><span class="text-slate-400">${m.Hora_Inicio || ''}</span></td>
                <td class="p-6">
                    <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full
                        ${m.EstadoMulta === 'Pendiente' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}">
                        ${m.EstadoMulta || '—'}
                    </span>
                </td>
                <td class="p-6 text-center">
                    ${m.EstadoMulta === 'Pendiente'
                        ? `<button onclick="pagarMulta(${m.Multa_ID})"
                               class="text-[10px] bg-emerald-50 text-emerald-600 border border-emerald-200 px-4 py-2 rounded-xl font-black hover:bg-emerald-100 transition-all uppercase">
                               <i class="fas fa-check mr-1"></i> Marcar Pagada
                           </button>`
                        : '<span class="text-slate-300 text-[10px] font-bold">Pagada</span>'}
                </td>
            </tr>`).join('');

    } catch (e) {
        console.error('[admin] Error cargando multas:', e);
    }
}

// ─── PUT /api/multas/<id>/pagar ───────────────────────────────────────────────
async function pagarMulta(multaId) {
    if (!confirm(`¿Marcar la multa #${multaId} como pagada?`)) return;
    try {
        const res  = await fetch(`/api/multas/${multaId}/pagar`, { method: 'PUT' });
        const data = await res.json();
        if (data.ok) {
            mostrarToast('Multa marcada como Pagada.');
            renderMultas();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (e) {
        console.error('[admin] Error pagando multa:', e);
        alert('Error de conexión.');
    }
}

// ─── Navegación de secciones ─────────────────────────────────────────────────
function cambiarSeccion(sec) {
    ['sec-dashboard', 'sec-citas', 'sec-config'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('seccion-visible');
            el.classList.add('seccion-oculta');
        }
    });

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const secEl  = document.getElementById(`sec-${sec}`);
    const btnEl  = document.getElementById(`btn-${sec}`);
    if (secEl) { secEl.classList.remove('seccion-oculta'); secEl.classList.add('seccion-visible'); }
    if (btnEl) btnEl.classList.add('active');

    const titles = {
        dashboard: 'Administración',
        citas:     'Historial de Citas',
        multas:    'Gestión de Multas',
        config:    'Mi Perfil'
    };
    const mainTitle = document.getElementById('main-title');
    if (mainTitle) mainTitle.textContent = titles[sec] || 'Administración';

    if (sec === 'citas')   renderCitas();
    if (sec === 'multas')  renderMultas();
    if (sec === 'config')  _precargarPerfilAdmin();
}

// ─── Dropdown de perfil ───────────────────────────────────────────────────────
function toggleProfileDropdown() {
    const dp = document.getElementById('profile-dropdown');
    if (!dp) return;
    const vis = dp.style.display === 'block';
    dp.style.display = vis ? 'none' : 'block';
}

window.addEventListener('click', (e) => {
    const trig = document.getElementById('profile-trigger');
    const drop = document.getElementById('profile-dropdown');
    if (trig && drop && !trig.contains(e.target) && !drop.contains(e.target)) {
        drop.style.display = 'none';
    }
});

// ─── Perfil administrador ─────────────────────────────────────────────────────
function _precargarPerfilAdmin() {
    const el = (id) => document.getElementById(id);
    if (el('edit-nombre')) el('edit-nombre').value = adminData.nombre || '';
    if (el('edit-email'))  el('edit-email').value  = adminData.email  || '';
    if (el('edit-tel'))    el('edit-tel').value    = adminData.tel    || '';
    _resetearPasswordAdmin();
}

function _resetearPasswordAdmin() {
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

// POST /usuarios/verificar-password
window.validarPasswordActual = function () {
    const inputActual = document.getElementById('pass-actual');
    const errActual   = document.getElementById('error-pass-actual');
    const step1       = document.getElementById('pass-step1');
    const step2       = document.getElementById('pass-step2');

    if (!inputActual?.value.trim()) {
        if (errActual) { errActual.textContent = 'Ingresa tu contraseña actual.'; errActual.style.display = 'block'; }
        return;
    }

    fetch('/usuarios/verificar-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ usuario_id: adminData.id, contrasena_actual: inputActual.value }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (errActual) errActual.style.display = 'none';
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = 'grid';
        } else {
            if (errActual) { errActual.textContent = 'Contraseña incorrecta.'; errActual.style.display = 'block'; }
        }
    })
    .catch(() => {
        if (errActual) errActual.style.display = 'none';
        if (step1) step1.style.display = 'none';
        if (step2) step2.style.display = 'grid';
    });
};

// POST /usuarios/cambiar-password
window.guardarPerfilCompleto = async function () {
    const nombre     = document.getElementById('edit-nombre')?.value.trim();
    const email      = document.getElementById('edit-email')?.value.trim();
    const tel        = document.getElementById('edit-tel')?.value.trim();
    const passNueva  = document.getElementById('conf-pass-nueva')?.value;
    const passConf   = document.getElementById('conf-pass-confirmar')?.value;
    const errNueva   = document.getElementById('error-pass-nueva');
    const step2      = document.getElementById('pass-step2');

    if (step2?.style.display === 'grid' && passNueva) {
        if (passNueva !== passConf) {
            if (errNueva) errNueva.style.display = 'block';
            return;
        }
        if (errNueva) errNueva.style.display = 'none';

        try {
            const res = await fetch('/usuarios/cambiar-password', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    usuario_id:           adminData.id,
                    contrasena_actual:    document.getElementById('pass-actual').value,
                    contrasena_nueva:     passNueva,
                    contrasena_confirmar: passConf
                })
            });
            const data = await res.json();
            if (!data.ok) {
                if (errNueva) { errNueva.textContent = data.error || 'No se pudo actualizar la contraseña.'; errNueva.style.display = 'block'; }
                return;
            }
        } catch (err) {
            if (errNueva) { errNueva.textContent = 'Error de conexión.'; errNueva.style.display = 'block'; }
            return;
        }
    }

    const raw = sessionStorage.getItem('odent_usuario');
    if (raw) {
        const u = JSON.parse(raw);
        const partes    = (nombre || '').split(' ');
        u.Nombres       = partes[0] || u.Nombres;
        u.Apellidos     = partes.slice(1).join(' ') || u.Apellidos;
        u.Correo        = email;
        u.Telefono      = tel;
        sessionStorage.setItem('odent_usuario', JSON.stringify(u));
    }

    adminData = { ...adminData, nombre, email, tel };
    mostrarToast('Perfil actualizado correctamente.');
    cargarSesion();
    cambiarSeccion('dashboard');
};

// ─── Modal confirmación simple ────────────────────────────────────────────────
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

const cerrarSesion = () => window.mostrarConfirmacionSimple('¿Quiere salir de la sesión?', 'salir');

// ─── Init ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    cargarSesion();
    setInterval(actualizarReloj, 1000);
    actualizarReloj();

    const fechaEl = document.getElementById('fecha-actual');
    if (fechaEl) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }).toUpperCase();
    }

    cambiarSeccion('dashboard');
});