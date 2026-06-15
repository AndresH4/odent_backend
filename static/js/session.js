/**
 * session.js — Stylo Dental
 * ───────────────────────────────────────────────────────────────────────────
 * Utilidad compartida por administrador.js, paciente.js y especialista.js.
 *
 * Exporta:
 *   obtenerSesion()        → objeto usuario o null
 *   exigirSesion(rolId?)   → redirige a /login si no hay sesión (o rol incorrecto)
 *   cerrarSesion()         → limpia sessionStorage y va a /login
 *   saludar(elementoId)    → escribe "¡Hola, {Nombres}!" en el elemento dado
 *   nombreCompleto(u)      → "Nombres Apellidos"
 */

'use strict';

/**
 * Lee el usuario guardado por login.js en sessionStorage.
 * @returns {Object|null}
 */
function obtenerSesion() {
    try {
        const raw = sessionStorage.getItem('odent_usuario');
        return raw ? JSON.parse(raw) : null;
    } catch (_) {
        return null;
    }
}

/**
 * Verifica que exista sesión (y opcionalmente que el rol coincida).
 * Si no, redirige a /login.
 * @param {number|null} rolEsperado  — 1=Admin, 2=Especialista, 3=Paciente
 */
function exigirSesion(rolEsperado = null) {
    const u = obtenerSesion();
    if (!u) {
        window.location.replace('/login');
        return null;
    }
    if (rolEsperado !== null && u.Rol_ID !== rolEsperado) {
        // El usuario tiene otro rol: mandarlo a su panel correcto
        const rutas = { 1: '/administrador.html', 2: '/especialista.html', 3: '/paciente.html' };
        window.location.replace(rutas[u.Rol_ID] || '/login');
        return null;
    }
    return u;
}

/**
 * Cierra sesión y redirige al login.
 */
function cerrarSesion() {
    sessionStorage.removeItem('odent_usuario');
    window.location.replace('/login');
}

/**
 * Devuelve el nombre completo del usuario.
 * @param {Object} u  — objeto usuario de la sesión
 * @returns {string}
 */
function nombreCompleto(u) {
    if (!u) return 'Usuario';
    return `${u.Nombres || ''} ${u.Apellidos || ''}`.trim() || 'Usuario';
}

/**
 * Inserta un saludo en el elemento con el id indicado.
 * Ejemplo:  saludar('nombre-usuario')  →  "¡Hola, María!"
 * @param {string} elementoId
 * @param {Object|null} usuario  — si null, usa obtenerSesion()
 */
function saludar(elementoId, usuario = null) {
    const u  = usuario || obtenerSesion();
    const el = document.getElementById(elementoId);
    if (!el || !u) return;
    const primerNombre = (u.Nombres || 'Usuario').split(' ')[0];
    el.textContent = primerNombre;
}