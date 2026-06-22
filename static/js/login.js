/**
 * login.js — Stylo Dental
 * Autentica contra /api/auth/login y redirige según Rol_ID.
 * Incluye flujo completo de recuperación de contraseña (modal 3 pasos).
 */

'use strict';

// ── Mostrar / ocultar contraseña ─────────────────────────────────────────────
function togglePassword(id) {
    const input = document.getElementById(id);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ── Validación básica del formulario de login ────────────────────────────────
function validarFormulario(correo, contrasena) {
    const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!correo || !contrasena) return 'Correo y contraseña son obligatorios.';
    if (!regexCorreo.test(correo))  return 'Ingresa un correo electrónico válido.';
    if (contrasena.length < 6)      return 'La contraseña debe tener al menos 6 caracteres.';
    return null;
}

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

function rutaPorRol(rolId) {
    const rutas = { 1: '/administrador.html', 2: '/especialista.html', 3: '/paciente.html' };
    return rutas[rolId] || '/login';
}

// ── Login principal ───────────────────────────────────────────────────────────
async function iniciarSesion(e) {
    e.preventDefault();
    ocultarError();

    const correo     = (document.getElementById('correo')?.value     || '').trim().toLowerCase();
    const contrasena = (document.getElementById('contrasena')?.value || '').trim();

    const errorLocal = validarFormulario(correo, contrasena);
    if (errorLocal) { mostrarError(errorLocal); return; }

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

        sessionStorage.setItem('odent_usuario', JSON.stringify(data.usuario));
        window.location.href = rutaPorRol(data.usuario.Rol_ID);

    } catch (err) {
        mostrarError('No se pudo conectar con el servidor. Intenta de nuevo.');
        console.error('[login.js] Error de red:', err);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Entrar al Sistema'; }
    }
}

/* ════════════════════════════════════════════════════════════════════════
   RECUPERACIÓN DE CONTRASEÑA
   ════════════════════════════════════════════════════════════════════════ */

const Recuperar = {
    correo: null,
    cooldownInterval: null,
    redirectInterval: null,
    COOLDOWN_SEGUNDOS: 30,

    // Prefijos de estado para las reglas
    PREFIX: { neutral: '- ', valid: '✓ ', error: '✗ ' },

    els: {},

    init() {
        this.els = {
            overlay:        document.getElementById('overlayRecuperar'),
            btnAbrir:       document.getElementById('btnAbrirRecuperar'),
            btnCerrar:      document.getElementById('btnCerrarModal'),

            panel1: document.getElementById('panel1'),
            panel2: document.getElementById('panel2'),
            panel3: document.getElementById('panel3'),
            panel4: document.getElementById('panel4'),

            recCorreo:         document.getElementById('recCorreo'),
            recError1:         document.getElementById('recError1'),
            btnEnviarCodigo:   document.getElementById('btnEnviarCodigo'),

            recCorreoMostrado: document.getElementById('recCorreoMostrado'),
            recCodigo:         document.getElementById('recCodigo'),
            recError2:         document.getElementById('recError2'),
            btnVerificarCodigo: document.getElementById('btnVerificarCodigo'),
            btnReenviar:       document.getElementById('btnReenviar'),
            resendTimer:       document.getElementById('resendTimer'),

            recNuevaPass:      document.getElementById('recNuevaPass'),
            recConfirmarPass:  document.getElementById('recConfirmarPass'),
            rulesList:         document.getElementById('rulesList'),
            recError3:         document.getElementById('recError3'),
            btnGuardarPass:    document.getElementById('btnGuardarPass'),

            redirectTimer:     document.getElementById('redirectTimer'),

            steps: document.querySelectorAll('.step')
        };

        if (!this.els.overlay) return;

        this.els.btnAbrir?.addEventListener('click', () => this.abrir());
        this.els.btnCerrar?.addEventListener('click', () => this.cerrar());
        this.els.overlay.addEventListener('click', (e) => {
            if (e.target === this.els.overlay) this.cerrar();
        });

        this.els.btnEnviarCodigo?.addEventListener('click', () => this.solicitarCodigo());
        this.els.btnVerificarCodigo?.addEventListener('click', () => this.verificarCodigo());
        this.els.btnReenviar?.addEventListener('click', () => this.solicitarCodigo(true));

        this.els.recCodigo?.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
        });

        this.els.recNuevaPass?.addEventListener('input', () => this.evaluarReglasNeutral());
        this.els.recConfirmarPass?.addEventListener('input', () => this.evaluarReglasNeutral());
        this.els.btnGuardarPass?.addEventListener('click', () => this.cambiarPassword());
    },

    // ── Abrir / cerrar modal ──
    abrir() {
        this.resetEstado();
        this.els.overlay.classList.add('show');
        this.irAPanel(1);
        setTimeout(() => this.els.recCorreo?.focus(), 150);
    },

    cerrar() {
        this.els.overlay.classList.remove('show');
        clearInterval(this.cooldownInterval);
        clearInterval(this.redirectInterval);
    },

    resetEstado() {
        this.correo = null;
        if (this.els.recCorreo)      this.els.recCorreo.value = '';
        if (this.els.recCodigo)      this.els.recCodigo.value = '';
        if (this.els.recNuevaPass)   this.els.recNuevaPass.value = '';
        if (this.els.recConfirmarPass) this.els.recConfirmarPass.value = '';
        this.ocultarErrores();
        if (this.els.btnGuardarPass) this.els.btnGuardarPass.disabled = true;
        this._resetearReglas();
    },

    _resetearReglas() {
        if (!this.els.rulesList) return;
        this.els.rulesList.querySelectorAll('li').forEach(li => {
            li.classList.remove('valid', 'invalid');
            const textEl = li.querySelector('.rule-text');
            if (textEl) {
                textEl.textContent = this.PREFIX.neutral + textEl.textContent.replace(/^[✓✗\-]\s/, '');
            }
        });
    },

    ocultarErrores() {
        [this.els.recError1, this.els.recError2, this.els.recError3].forEach(el => {
            if (el) { el.style.display = 'none'; el.textContent = ''; }
        });
    },

    mostrarErrorPanel(el, mensaje) {
        if (!el) return;
        el.textContent = mensaje;
        el.style.display = 'block';
    },

    // ── Navegación entre paneles ──
    irAPanel(numero) {
        [this.els.panel1, this.els.panel2, this.els.panel3, this.els.panel4].forEach((p, idx) => {
            if (p) p.hidden = (idx + 1) !== numero;
        });

        this.els.steps.forEach(step => {
            const stepNum = parseInt(step.dataset.step, 10);
            step.classList.remove('active', 'done');
            if (stepNum < numero && numero <= 3) step.classList.add('done');
            else if (stepNum === numero) step.classList.add('active');
            else if (numero === 4) step.classList.add('done');
        });
    },

    // ── Paso 1: Solicitar código ──
    async solicitarCodigo(esReenvio = false) {
        this.ocultarErrores();

        const correo = esReenvio
            ? this.correo
            : (this.els.recCorreo.value || '').trim().toLowerCase();

        const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!correo || !regexCorreo.test(correo)) {
            this.mostrarErrorPanel(this.els.recError1, 'Ingresa un correo electrónico válido.');
            return;
        }

        const btn = esReenvio ? this.els.btnReenviar : this.els.btnEnviarCodigo;
        const textoOriginal = btn.innerHTML;
        btn.disabled = true;
        if (!esReenvio) btn.textContent = 'Enviando...';

        try {
            const res = await fetch('/api/auth/solicitar-codigo', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ correo })
            });
            const data = await res.json();

            if (!data.ok) {
                this.mostrarErrorPanel(
                    esReenvio ? this.els.recError2 : this.els.recError1,
                    data.error || 'No se pudo enviar el código.'
                );
                if (esReenvio) btn.disabled = false;
                return;
            }

            this.correo = correo;

            if (!esReenvio) {
                this.els.recCorreoMostrado.textContent = correo;
                this.irAPanel(2);
                setTimeout(() => this.els.recCodigo?.focus(), 150);
            }

            this.iniciarCooldownReenvio();

        } catch (err) {
            this.mostrarErrorPanel(
                esReenvio ? this.els.recError2 : this.els.recError1,
                'No se pudo conectar con el servidor.'
            );
            if (esReenvio) btn.disabled = false;
            console.error('[Recuperar] Error solicitar-codigo:', err);
        } finally {
            if (!esReenvio) { btn.disabled = false; btn.innerHTML = textoOriginal; }
        }
    },

    iniciarCooldownReenvio() {
        clearInterval(this.cooldownInterval);
        let segundos = this.COOLDOWN_SEGUNDOS;
        this.els.btnReenviar.disabled = true;
        this.els.resendTimer.textContent = segundos;

        this.cooldownInterval = setInterval(() => {
            segundos--;
            if (segundos <= 0) {
                clearInterval(this.cooldownInterval);
                this.els.btnReenviar.disabled = false;
                this.els.btnReenviar.innerHTML = 'Reenviar código';
            } else {
                this.els.btnReenviar.innerHTML = `Reenviar (<span id="resendTimer">${segundos}</span>s)`;
            }
        }, 1000);
    },

    // ── Paso 2: Verificar código ──
    async verificarCodigo() {
        this.ocultarErrores();
        const codigo = (this.els.recCodigo.value || '').trim();

        if (codigo.length !== 6) {
            this.mostrarErrorPanel(this.els.recError2, 'Ingresa el código de 6 dígitos.');
            return;
        }

        const btn = this.els.btnVerificarCodigo;
        const textoOriginal = btn.innerHTML;
        btn.disabled = true;
        btn.textContent = 'Verificando...';

        try {
            const res = await fetch('/api/auth/verificar-codigo', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ correo: this.correo, codigo })
            });
            const data = await res.json();

            if (!data.ok) {
                this.mostrarErrorPanel(this.els.recError2, data.error || 'Código incorrecto.');
                return;
            }

            clearInterval(this.cooldownInterval);
            this.irAPanel(3);
            setTimeout(() => this.els.recNuevaPass?.focus(), 150);

        } catch (err) {
            this.mostrarErrorPanel(this.els.recError2, 'No se pudo conectar con el servidor.');
            console.error('[Recuperar] Error verificar-codigo:', err);
        } finally {
            btn.disabled = false;
            btn.innerHTML = textoOriginal;
        }
    },

    // ── Paso 3: Evaluación en tiempo real (neutral/verde) ──
    _calcularReglas(pass, confirm) {
        return {
            len:     pass.length >= 8,
            upper:   /[A-Z]/.test(pass),
            lower:   /[a-z]/.test(pass),
            num:     /\d/.test(pass),
            special: /[^A-Za-z0-9]/.test(pass),
            match:   pass.length > 0 && pass === confirm
        };
    },

    _aplicarEstadoReglas(reglas, marcarErrores = false) {
        if (!this.els.rulesList) return;

        Object.entries(reglas).forEach(([clave, valido]) => {
            const li = this.els.rulesList.querySelector(`[data-rule="${clave}"]`);
            if (!li) return;
            const textEl = li.querySelector('.rule-text');
            if (!textEl) return;

            // Texto base sin prefijo
            const textoBase = textEl.textContent.replace(/^[✓✗\-]\s/, '');

            if (valido) {
                li.classList.add('valid');
                li.classList.remove('invalid');
                textEl.textContent = this.PREFIX.valid + textoBase;
            } else if (marcarErrores) {
                li.classList.add('invalid');
                li.classList.remove('valid');
                textEl.textContent = this.PREFIX.error + textoBase;
            } else {
                li.classList.remove('valid', 'invalid');
                textEl.textContent = this.PREFIX.neutral + textoBase;
            }
        });
    },

    evaluarReglasNeutral() {
        const pass    = this.els.recNuevaPass?.value   || '';
        const confirm = this.els.recConfirmarPass?.value || '';
        const reglas  = this._calcularReglas(pass, confirm);
        this._aplicarEstadoReglas(reglas, false);
        const todasValidas = Object.values(reglas).every(Boolean);
        this.els.btnGuardarPass.disabled = !todasValidas;
        return { reglas, todasValidas };
    },

    evaluarReglasConErrores() {
        const pass    = this.els.recNuevaPass?.value   || '';
        const confirm = this.els.recConfirmarPass?.value || '';
        const reglas  = this._calcularReglas(pass, confirm);
        this._aplicarEstadoReglas(reglas, true);
        const todasValidas = Object.values(reglas).every(Boolean);
        this.els.btnGuardarPass.disabled = !todasValidas;
        return { reglas, todasValidas };
    },

    async cambiarPassword() {
        this.ocultarErrores();
        const { todasValidas } = this.evaluarReglasConErrores();

        if (!todasValidas) {
            this.mostrarErrorPanel(this.els.recError3, 'La contraseña no cumple todos los requisitos.');
            return;
        }

        const btn = this.els.btnGuardarPass;
        const textoOriginal = btn.innerHTML;
        btn.disabled = true;
        btn.textContent = 'Actualizando...';

        try {
            const res = await fetch('/api/auth/cambiar-password', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    correo: this.correo,
                    nueva_contrasena: this.els.recNuevaPass.value
                })
            });
            const data = await res.json();

            if (!data.ok) {
                this.mostrarErrorPanel(this.els.recError3, data.error || 'No se pudo actualizar la contraseña.');
                btn.disabled = false;
                btn.innerHTML = textoOriginal;
                return;
            }

            this.irAPanel(4);
            this.iniciarRedireccion();

        } catch (err) {
            this.mostrarErrorPanel(this.els.recError3, 'No se pudo conectar con el servidor.');
            console.error('[Recuperar] Error cambiar-password:', err);
            btn.disabled = false;
            btn.innerHTML = textoOriginal;
        }
    },

    // ── Paso 4: Éxito + redirección automática ──
    iniciarRedireccion() {
        let segundos = 3;
        this.els.redirectTimer.textContent = segundos;
        this.redirectInterval = setInterval(() => {
            segundos--;
            this.els.redirectTimer.textContent = segundos;
            if (segundos <= 0) {
                clearInterval(this.redirectInterval);
                this.cerrar();
                window.location.href = '/login.html';
            }
        }, 1000);
    }
};

// ── Inicialización ────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
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

    Recuperar.init();
});