/**
 * static/js/login.js
 * ===================
 * Maneja el envío del formulario de login y redirige al panel
 * correspondiente según el Rol_ID devuelto por el backend.
 *
 * Rol_ID → 1 = Administrador → administrador.html
 * Rol_ID → 2 = Especialista   → especialista.html
 * Rol_ID → 3 = Paciente       → paciente.html
 *
 * HTML ESPERADO en login.html:
 * ──────────────────────────────────────────────────────────────
 * <form id="loginForm">
 * <input type="email"    id="correo"     required>
 * <input type="password" id="contrasena" required>
 * <button type="submit">Iniciar sesión</button>
 * </form>
 * <p id="loginError" style="display:none; color:red;"></p>
 *
 * <script src="/static/js/login.js"></script>
 * ──────────────────────────────────────────────────────────────
 * Si tu login.html ya tiene otros IDs, solo ajusta los
 * document.getElementById(...) de abajo para que coincidan.
 */

document.addEventListener('DOMContentLoaded', () => {
  
  // --- INICIO DE CÓDIGO NUEVO: Verificar sesión activa ---
  const usuarioGuardado = sessionStorage.getItem('odent_usuario');
  if (usuarioGuardado) {
    const usuario = JSON.parse(usuarioGuardado);
    redirigirSegunRol(usuario.Rol_ID);
    return;
  }
  // --- FIN DE CÓDIGO NUEVO ---

  const form = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');

  if (!form) {
    console.error('No se encontró el formulario #loginForm en login.html');
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    ocultarError();

    const correo = document.getElementById('correo').value.trim();
    const contrasena = document.getElementById('contrasena').value;

    if (!correo || !contrasena) {
      mostrarError('Por favor completa correo y contraseña.');
      return;
    }

    try {
      const respuesta = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ correo, contrasena })
      });

      const datos = await respuesta.json();

      if (!respuesta.ok || !datos.ok) {
        mostrarError(datos.error || 'Correo o contraseña incorrectos.');
        return;
      }

      // Guardamos los datos del usuario logueado para usarlos en los
      // paneles siguientes (administrador.html, paciente.html, etc.)
      sessionStorage.setItem('odent_usuario', JSON.stringify(datos.usuario));

      redirigirSegunRol(datos.usuario.Rol_ID);

    } catch (error) {
      console.error('Error de conexión con el servidor:', error);
      mostrarError('No se pudo conectar con el servidor. Intenta de nuevo.');
    }
  });

  /**
   * Redirige a la vista correspondiente según el Rol_ID del usuario.
   * @param {number} rolId - 1=Administrador, 2=Especialista, 3=Paciente
   */
  function redirigirSegunRol(rolId) {
    switch (rolId) {
      case 1:
        window.location.href = '/administrador.html';
        break;
      case 2:
        window.location.href = '/especialista.html';
        break;
      case 3:
        window.location.href = '/paciente.html';
        break;
      default:
        mostrarError('Rol de usuario no reconocido.');
    }
  }

  function mostrarError(mensaje) {
    if (errorBox) {
      errorBox.textContent = mensaje;
      errorBox.style.display = 'block';
    } else {
      alert(mensaje);
    }
  }

  function ocultarError() {
    if (errorBox) {
      errorBox.style.display = 'none';
      errorBox.textContent = '';
    }
  }
});

// ── TOGGLE DE VISIBILIDAD DE CONTRASEÑA ──
// (Añadido para que coincida con el ícono de "ojo" del diseño de Creación)
function togglePassword(id) {
  const input = document.getElementById(id);
  input.type = input.type === "password" ? "text" : "password";
}