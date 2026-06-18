/**
 * administrador.js — Stylo Dental
 * Lee la sesión guardada por login.js, muestra el saludo y carga datos reales
 * desde la API Flask en lugar de localStorage.
 */

'use strict';

// ─── Variables de módulo ─────────────────────────────────────────────────────
let adminData = {};
let accionPendienteSimple = '';

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

// ─── Sesión ──────────────────────────────────────────────────────────────────
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

    const pic = document.getElementById('header-pic');
    if (pic) pic.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(nombre)}&background=0284c7&color=fff&size=128`;

    actualizarStats();
}

window.cerrarSesion = function () {
    mostrarConfirmacionSimple('¿Quiere salir de la sesión?', 'salir');
};

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

// ─── Módulo EPS: Reporte de afiliados por EPS ────────────────────────────────
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

    await cargarReporteAfiliados();
}

// ─── Lista dinámica de usuarios ──────────────────────────────────────────────
window.renderUsuarios = async function (rolNombre) {
    const rolMap = { 'Especialista': 2, 'Paciente': 3 };
    const rolId  = rolMap[rolNombre];

    try {
        const res  = await fetch('/api/usuarios');
        const data = await res.json();
        const filtrados = data.filter(u => u.Rol_ID === rolId);

        let pacientesEPS = [];
        if (rolNombre === 'Paciente') {
            pacientesEPS = await cargarPacientesEPS();
        }

        const body = document.getElementById('body-lista-dinamica');
        const cont = document.getElementById('container-lista-rapida');
        const tit  = document.getElementById('titulo-lista-dinamica');

        if (!body || !cont || !tit) return;
        cont.classList.remove('hidden', 'seccion-oculta');
        cont.classList.add('seccion-visible');
        tit.textContent = `GESTIÓN: ${rolNombre.toUpperCase()}S`;

        body.innerHTML = filtrados.map(u => {
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
};

window.ocultarListaRapida = function () {
    const cont = document.getElementById('container-lista-rapida');
    if (cont) {
        cont.classList.remove('seccion-visible');
        cont.classList.add('seccion-oculta');
    }
};

// ─── Filtrar tabla de citas ───────────────────────────────────────────────────
window.filtrarTablaCitas = function () {
    const filtro = (document.getElementById('busqueda-citas')?.value || '').toLowerCase();
    document.querySelectorAll('#tabla-body tr').forEach(fila => {
        fila.style.display = fila.textContent.toLowerCase().includes(filtro) ? '' : 'none';
    });
};

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
const SECCIONES_ADMIN = {
    dashboard : { sec: 'sec-dashboard', btn: 'btn-dashboard', titulo: 'Administración'       },
    citas     : { sec: 'sec-citas',     btn: 'btn-citas',     titulo: 'Historial Citas'      },
    config    : { sec: 'sec-config',    btn: 'btn-config',    titulo: 'Mi Perfil'            },
};

window.cambiarSeccion = function (seccion) {
    const cfg = SECCIONES_ADMIN[seccion];
    if (!cfg) return;

    // Ocultar todas las secciones
    Object.values(SECCIONES_ADMIN).forEach(({ sec }) => {
        const el = document.getElementById(sec);
        if (el) {
            el.classList.remove('seccion-visible');
            el.classList.add('seccion-oculta');
        }
    });

    // Desactivar todos los botones del sidebar
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    // Mostrar la sección activa
    const secEl = document.getElementById(cfg.sec);
    if (secEl) {
        secEl.classList.remove('seccion-oculta');
        secEl.classList.add('seccion-visible');
    }

    // Activar el botón correspondiente
    const btnEl = document.getElementById(cfg.btn);
    if (btnEl) btnEl.classList.add('active');

    // Actualizar título del header
    const titleEl = document.getElementById('main-title');
    if (titleEl) titleEl.textContent = cfg.titulo;

    // Acciones específicas por sección
    if (seccion === 'citas')  renderCitas();
    if (seccion === 'config') _cargarDatosPerfil();
};

// ─── Dropdown de perfil ───────────────────────────────────────────────────────
window.toggleProfileDropdown = function () {
    const dropdown = document.getElementById('profile-dropdown');
    if (!dropdown) return;
    const isVisible = dropdown.style.display === 'block';
    dropdown.style.display = isVisible ? 'none' : 'block';
};

window.addEventListener('click', (e) => {
    if (!e.target.closest('#profile-dropdown') && !e.target.closest('#profile-trigger')) {
        const dropdown = document.getElementById('profile-dropdown');
        if (dropdown) dropdown.style.display = 'none';
    }
});

// ─── Perfil: carga de datos en el formulario ─────────────────────────────────
function _cargarDatosPerfil() {
    const nombre = document.getElementById('drop-name')?.textContent.trim()  || '';
    const email  = document.getElementById('drop-email')?.textContent.trim() || '';
    const tel    = document.getElementById('drop-tel')?.textContent.trim()   || '';

    const inputNombre = document.getElementById('edit-nombre');
    const inputEmail  = document.getElementById('edit-email');
    const inputTel    = document.getElementById('edit-tel');

    if (inputNombre) inputNombre.value = nombre !== 'Admin Root' ? nombre : (adminData.nombre || '');
    if (inputEmail)  inputEmail.value  = email  || adminData.email  || '';
    if (inputTel)    inputTel.value    = tel    || adminData.tel    || '';

    // Reiniciar flujo de contraseña
    const step1      = document.getElementById('pass-step1');
    const step2      = document.getElementById('pass-step2');
    const errActual  = document.getElementById('error-pass-actual');
    const errNueva   = document.getElementById('error-pass-nueva');
    const passActual = document.getElementById('pass-actual');
    const passNueva  = document.getElementById('conf-pass-nueva');
    const passConf   = document.getElementById('conf-pass-confirmar');

    if (step1)      step1.style.display      = '';
    if (step2)      step2.style.display      = 'none';
    if (errActual)  errActual.style.display  = 'none';
    if (errNueva)   errNueva.style.display   = 'none';
    if (passActual) passActual.value = '';
    if (passNueva)  passNueva.value  = '';
    if (passConf)   passConf.value   = '';
}

// ─── Validación de contraseña paso 1 → paso 2 ───────────────────────────────
window.validarPasswordActual = function () {
    const inputActual = document.getElementById('pass-actual');
    const errActual   = document.getElementById('error-pass-actual');
    const step1       = document.getElementById('pass-step1');
    const step2       = document.getElementById('pass-step2');

    if (!inputActual || !inputActual.value.trim()) {
        if (errActual) {
            errActual.textContent   = 'Ingresa tu contraseña actual.';
            errActual.style.display = 'block';
        }
        return;
    }

    fetch('/api/verificar-password', {
        method  : 'POST',
        headers : { 'Content-Type': 'application/json' },
        body    : JSON.stringify({ password: inputActual.value }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (errActual) errActual.style.display = 'none';
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = '';
        } else {
            if (errActual) {
                errActual.textContent   = 'Contraseña incorrecta.';
                errActual.style.display = 'block';
            }
        }
    })
    .catch(() => {
        // Fallback sin backend: avanzar al paso 2 directamente
        if (errActual) errActual.style.display = 'none';
        if (step1) step1.style.display = 'none';
        if (step2) step2.style.display = '';
    });
};

// ─── Guardar perfil completo ─────────────────────────────────────────────────
window.guardarPerfilCompleto = function () {
    const nombre        = document.getElementById('edit-nombre')?.value.trim();
    const email         = document.getElementById('edit-email')?.value.trim();
    const tel           = document.getElementById('edit-tel')?.value.trim();
    const passNueva     = document.getElementById('conf-pass-nueva')?.value;
    const passConfirmar = document.getElementById('conf-pass-confirmar')?.value;
    const errNueva      = document.getElementById('error-pass-nueva');
    const step2         = document.getElementById('pass-step2');

    // Validar coincidencia de contraseñas si el paso 2 está visible
    if (step2 && step2.style.display !== 'none') {
        if (passNueva !== passConfirmar) {
            if (errNueva) errNueva.style.display = 'block';
            return;
        }
        if (errNueva) errNueva.style.display = 'none';
    }

    // Actualizar sesión local
    adminData.nombre = nombre || adminData.nombre;
    adminData.email  = email  || adminData.email;
    adminData.tel    = tel    || adminData.tel;

    const raw = sessionStorage.getItem('odent_usuario');
    if (raw) {
        const u = JSON.parse(raw);
        if (nombre) {
            u.Nombres   = nombre.split(' ')[0]          || u.Nombres;
            u.Apellidos = nombre.split(' ').slice(1).join(' ') || u.Apellidos;
        }
        if (email) u.Correo   = email;
        if (tel)   u.Telefono = tel;
        sessionStorage.setItem('odent_usuario', JSON.stringify(u));
    }

    fetch('/api/actualizar-perfil-admin', {
        method  : 'POST',
        headers : { 'Content-Type': 'application/json' },
        body    : JSON.stringify({
            nombre,
            email,
            telefono  : tel,
            nuevaPass : passNueva || null,
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            // Reflejar cambios en el header y dropdown
            if (nombre) {
                setText('drop-name',   nombre);
                setText('header-name', nombre);
            }
            if (email) setText('drop-email', email);
            if (tel)   setText('drop-tel',   tel);

            mostrarToast('PERFIL ACTUALIZADO');
            cambiarSeccion('dashboard');
        } else {
            alert(data.mensaje || 'No se pudo guardar. Intenta de nuevo.');
        }
    })
    .catch(() => {
        // Fallback sin backend: actualizar UI localmente
        if (nombre) { setText('drop-name', nombre); setText('header-name', nombre); }
        if (email)  setText('drop-email', email);
        if (tel)    setText('drop-tel',   tel);

        mostrarToast('PERFIL ACTUALIZADO');
        cambiarSeccion('dashboard');
    });
};

// ─── Funciones de perfil heredadas (compatibilidad) ──────────────────────────
window.abrirConfiguracion = function () {
    cambiarSeccion('config');
};

window.cerrarConfiguracion = function () {
    cambiarSeccion('dashboard');
};

window.guardarPerfil = function () {
    guardarPerfilCompleto();
};

window.verificarOldPass = function () {
    validarPasswordActual();
};

window.togglePass = function (id) {
    const el = document.getElementById(id);
    if (el) el.type = el.type === 'password' ? 'text' : 'password';
};

// ─── Modal confirmación simple ────────────────────────────────────────────────
window.mostrarConfirmacionSimple = function (mensaje, accion) {
    accionPendienteSimple = accion;
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');
    if (texto) texto.textContent = mensaje;
    if (modal) modal.style.display = 'flex';
};

window.cerrarModalSimple = function () {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
    accionPendienteSimple = '';
};

window.ejecutarAccionSimple = function () {
    if (accionPendienteSimple === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
    cerrarModalSimple();
};

// ─── Init ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    cargarSesion();
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
});