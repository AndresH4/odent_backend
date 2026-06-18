/* paciente_ui.js — Stylo Dental Pro
   Gestiona: reloj, estado laboral, dropdown de perfil,
   navegación de vistas y formulario de Mi Perfil.
   Depende de: paciente.js (cargado antes en el HTML)
*/
'use strict';

// ─── Control de Modales y Cierre de Sesión ────────────────────────────────────
let accionPendienteSimple = null;

// ─── Mapa de vistas ───────────────────────────────────────────────────────────
const VISTAS_PACIENTE = {
    inicio   : { el: 'vista-inicio',   btn: 'btn-inicio',   titulo: 'Panel de Control'    },
    historial: { el: 'vista-historial', btn: 'btn-historial', titulo: 'Historial de Citas' },
    config   : { el: 'vista-config',   btn: 'btn-config',   titulo: 'Mi Perfil'           },
};

// ─── Reloj y estado laboral ───────────────────────────────────────────────────
function actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();    // 0 = domingo … 6 = sábado
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

// ─── Dropdown de perfil ───────────────────────────────────────────────────────
let _dropdownOpen = false;

window.toggleProfileDropdown = function () {
    _dropdownOpen ? closeProfileDropdown() : openProfileDropdown();
};

function openProfileDropdown() {
    document.getElementById('profile-dropdown')?.classList.add('show');
    _dropdownOpen = true;
}

window.closeProfileDropdown = function () {
    document.getElementById('profile-dropdown')?.classList.remove('show');
    _dropdownOpen = false;
};

// ─── Sincronizar avatar y datos del dropdown ──────────────────────────────────
function _sincronizarDropdown() {
    const nombres   = document.getElementById('perfil-nombres')?.textContent.trim()   || '';
    const apellidos = document.getElementById('perfil-apellidos')?.textContent.trim() || '';
    const correo    = document.getElementById('perfil-correo')?.textContent.trim()    || '';
    const numDoc    = document.getElementById('perfil-numDoc')?.textContent.trim()    || '';
    const eps       = document.getElementById('perfil-eps')?.textContent.trim()       || '';

    const fullName  = [nombres, apellidos].filter(v => v && v !== '---').join(' ');
    const iniciales = fullName
        .split(' ').filter(Boolean).slice(0, 2)
        .map(p => p[0]).join('').toUpperCase() || 'PA';

    const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };

    set('perfil-avatar-grande',  iniciales);
    set('avatar-letras',         iniciales);
    set('nombre-menu',           fullName ? fullName.toUpperCase() : '');
    if (numDoc && numDoc !== '---') set('doc-menu',   numDoc);
    if (correo && correo !== '---') set('email-menu', correo);
    if (eps    && eps    !== '---' && eps !== 'Cargando...') set('eps-menu', eps);
    if (fullName) set('nombre-usuario-header', fullName);
}

// ─── Activar vista ────────────────────────────────────────────────────────────
function _activarVistaPaciente(vista) {
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

    if (vista === 'config') _precargarPerfil();
}

// ─── Precargar formulario Mi Perfil ──────────────────────────────────────────
function _precargarPerfil() {
    const vals = {
        'edit-correo'    : document.getElementById('perfil-correo')?.textContent.trim()     || '',
        'edit-nacimiento': document.getElementById('perfil-nacimiento')?.textContent.trim() || '',
        'edit-telefono'  : document.getElementById('perfil-telefono')?.textContent.trim()   || '',
    };
    Object.entries(vals).forEach(([id, val]) => {
        const inp = document.getElementById(id);
        if (inp && !inp.value && val !== '---') inp.value = val;
    });
    _resetearFlujoPassword();
}

function _resetearFlujoPassword() {
    const ids = ['pass-step1', 'pass-step2', 'error-pass-actual', 'error-pass-nueva',
                 'pass-actual', 'conf-pass-nueva', 'conf-pass-confirmar'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (id === 'pass-step1')           el.style.display = '';
        else if (id === 'pass-step2')      el.style.display = 'none';
        else if (id.startsWith('error-'))  el.style.display = 'none';
        else                               el.value = '';
    });
}

// ─── Validar contraseña actual (paso 1) ──────────────────────────────────────
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
        method : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body   : JSON.stringify({ password: inputActual.value }),
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

// ─── Guardar perfil del paciente ──────────────────────────────────────────────
window.guardarPerfilPaciente = function () {
    const correo        = document.getElementById('edit-correo')?.value.trim();
    const telefono      = document.getElementById('edit-telefono')?.value.trim();
    const nacimiento    = document.getElementById('edit-nacimiento')?.value;
    const passNueva     = document.getElementById('conf-pass-nueva')?.value;
    const passConfirmar = document.getElementById('conf-pass-confirmar')?.value;
    const errNueva      = document.getElementById('error-pass-nueva');
    const step2         = document.getElementById('pass-step2');

    if (step2?.style.display !== 'none' && passNueva !== passConfirmar) {
        if (errNueva) errNueva.style.display = 'block';
        return;
    }
    if (errNueva) errNueva.style.display = 'none';

    if (typeof guardarConfiguracionGeneral === 'function') {
        const map = {
            'edit-correo': correo, 'edit-nacimiento': nacimiento,
            'edit-telefono': telefono, 'nueva-pass': passNueva, 'confirmar-pass': passConfirmar
        };
        Object.entries(map).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el && val) el.value = val;
        });
        guardarConfiguracionGeneral();
        return;
    }

    fetch('/api/actualizar-perfil-paciente', {
        method : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body   : JSON.stringify({ correo, telefono, nacimiento, nuevaPass: passNueva || null }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (correo)     { const el = document.getElementById('perfil-correo');     if (el) el.textContent = correo; }
            if (nacimiento) { const el = document.getElementById('perfil-nacimiento'); if (el) el.textContent = nacimiento; }
            _sincronizarDropdown();
            cambiarVista('inicio');
        } else {
            alert(data.mensaje || 'No se pudo guardar. Intenta de nuevo.');
        }
    })
    .catch(() => alert('Error de conexión al guardar el perfil.'));
};

// ─── Funciones Dinámicas del Modal de Confirmación ───────────────────────────
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
// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    // Reloj: arrancar y repetir cada segundo
    actualizarReloj();
    setInterval(actualizarReloj, 1000);

    // Fecha en cabecera
    const fechaEl = document.getElementById('fecha-actual-paciente');
    if (fechaEl) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }).toUpperCase();
    }

    // Dropdown: estado inicial oculto
    closeProfileDropdown();

    // Cerrar dropdown al hacer clic fuera
    document.addEventListener('click', function (e) {
        const trigger  = document.getElementById('profile-trigger');
        const dropdown = document.getElementById('profile-dropdown');
        if (!trigger || !dropdown) return;
        if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
            closeProfileDropdown();
        }
    });

    // Sincronización inicial del dropdown con datos de paciente.js
    _sincronizarDropdown();

    // Observar mutaciones en los nodos de datos que escribe paciente.js
    const observer = new MutationObserver(_sincronizarDropdown);
    ['perfil-nombres', 'perfil-apellidos', 'perfil-correo', 'perfil-numDoc', 'perfil-eps'].forEach(id => {
        const el = document.getElementById(id);
        if (el) observer.observe(el, { childList: true, subtree: true, characterData: true });
    });

    // Sincronizar nombre del header con el nodo oculto que escribe paciente.js
    const fuente  = document.getElementById('nombre-usuario');
    const destino = document.getElementById('nombre-usuario-header');
    if (fuente && destino) {
        const copiar = () => { const v = fuente.innerText.trim(); if (v) { destino.innerText = v; _sincronizarDropdown(); } };
        copy();
        new MutationObserver(copiar).observe(fuente, { childList: true, subtree: true, characterData: true });
    }

    // Capturar cambiarVista de paciente.js y extender con soporte para 'config'
    const _originalCambiarVista = window.cambiarVista;
    window.cambiarVista = function (vista) {
        closeProfileDropdown();
        if (VISTAS_PACIENTE[vista]) {
            _activarVistaPaciente(vista);
        } else if (typeof _originalCambiarVista === 'function') {
            _originalCambiarVista(vista);
        }
    };
});