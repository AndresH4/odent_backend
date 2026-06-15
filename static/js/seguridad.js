/**
 * seguridad.js — Stylo Dental
 * ─────────────────────────────────────────────────────────────────────────────
 * Script mínimo de seguridad cargado por administrador.html y paciente.html.
 * Su única responsabilidad es proteger la vista si no hay sesión válida
 * y exponer cerrarSesion() globalmente.
 *
 * La lógica de cada panel vive en administrador.js / paciente.js.
 */

'use strict';

/**
 * Cierra la sesión del usuario y lo manda al login.
 * Se llama desde los botones de logout en el HTML.
 */
function cerrarSesion() {
    sessionStorage.removeItem('odent_usuario');
    window.location.replace('/login');
}

/**
 * Verifica que haya una sesión activa al cargar la página.
 * Si no hay sesión, redirige al login inmediatamente.
 */
(function verificarSesionActiva() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) {
        window.location.replace('/login');
    }
})();