/**
 * login.js — Stylo Dental
 * Autentica contra /api/auth/login y redirige según Rol_ID:
 *   1 → administrador.html
 *   2 → especialista.html
 *   3 → paciente.html
 */

'use strict';

// ── Mostrar / ocultar contraseña ─────────────────────────────────────────────
function togglePassword(id) {
    const input = document.getElementById(id);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ── Validación básica del formulario ─────────────────────────────────────────
function validarFormulario(correo, contrasena) {
    const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!correo || !contrasena) return 'Correo y contraseña son obligatorios.';
    if (!regexCorreo.test(correo))  return 'Ingresa un correo electrónico válido.';
    if (contrasena.length < 6)      return 'La contraseña debe tener al menos 6 caracteres.';
    return null;
}

// ── Mostrar error en el formulario ───────────────────────────────────────────
function mostrarError(mensaje) {
    const el = document.getElementById('loginError');
    if (!el) return;
    el.textContent = mensaje;
    el.style.display = 'block';
}

function ocultarError() {
    const el = document.getElementById('loginError');
    if (el) el.style.display = 'none';
}

// ── Ruta por rol ─────────────────────────────────────────────────────────────
function rutaPorRol(rolId) {
    const rutas = { 1: '/administrador.html', 2: '/especialista.html', 3: '/paciente.html' };
    return rutas[rolId] || '/login';
}

// ── Login principal ───────────────────────────────────────────────────────────
async function iniciarSesion(e) {
    e.preventDefault();
    ocultarError();

    const correo    = (document.getElementById('correo')?.value    || '').trim().toLowerCase();
    const contrasena = (document.getElementById('contrasena')?.value || '').trim();

    // Validación en cliente
    const errorLocal = validarFormulario(correo, contrasena);
    if (errorLocal) { mostrarError(errorLocal); return; }

    // Bloquear botón mientras espera
    const btn = document.querySelector('#loginForm button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Verificando...'; }

    try {
        const res  = await fetch('/api/auth/login', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ correo, contrasena })
        });
        const data = await res.json();

        if (!data.ok) {
            mostrarError(data.error || 'Credenciales incorrectas.');
            return;
        }

        // Guardar sesión en sessionStorage (se borra al cerrar pestaña)
        sessionStorage.setItem('odent_usuario', JSON.stringify(data.usuario));

        // Redirigir según rol
        window.location.href = rutaPorRol(data.usuario.Rol_ID);

    } catch (err) {
        mostrarError('No se pudo conectar con el servidor. Intenta de nuevo.');
        console.error('[login.js] Error de red:', err);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Entrar al Sistema'; }
    }
}

// ── Inicialización ────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    // Si ya hay sesión activa, redirigir directo
    const sesionActiva = sessionStorage.getItem('odent_usuario');
    if (sesionActiva) {
        try {
            const u = JSON.parse(sesionActiva);
            window.location.href = rutaPorRol(u.Rol_ID);
            return;
        } catch (_) { sessionStorage.clear(); }
    }

    const form = document.getElementById('loginForm');
    if (form) form.addEventListener('submit', iniciarSesion);
});