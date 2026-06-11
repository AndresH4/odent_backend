const RUTAS = {
    especialista: "especialista.html",
    paciente: "paciente.html",
    administrador: "administrador.html",
    defecto: "sistema_dental.html"
};

function validarYEntrar() {
    // Reset de errores
    document.querySelectorAll('.error-text').forEach(el => el.style.display = 'none');
    document.querySelectorAll('input').forEach(el => el.classList.remove('input-error'));

    const correo = document.getElementById('emailLogin').value.toLowerCase().trim();
    const clave = document.getElementById('passLogin').value;

    const usuariosDB = JSON.parse(localStorage.getItem('usuarios_dental')) || {};

    if (!correo) {
        mostrarError('emailLogin', 'errorEmail', 'Por favor, ingrese su correo');
        return;
    }

    if (!usuariosDB[correo]) {
        mostrarError('emailLogin', 'errorEmail', 'Este correo no existe en nuestro sistema');
        return;
    }

    if (!clave) {
        mostrarError('passLogin', 'errorPass', 'Por favor, ingrese su contraseña');
        return;
    }

    if (usuariosDB[correo].pass !== clave) {
        mostrarError('passLogin', 'errorPass', 'La contraseña es incorrecta');
        return;
    }

    localStorage.setItem('usuario_logueado', correo);

    const rolUsuario = usuariosDB[correo].rol;

    if (rolUsuario === "Especialista") {
        window.location.href = RUTAS.especialista;
    } else if (rolUsuario === "Paciente") {
        window.location.href = RUTAS.paciente;
    } else if (rolUsuario === "Administrador") {
        window.location.href = RUTAS.administrador;
    } else {
        window.location.href = RUTAS.defecto;
    }
}

function mostrarError(inputId, errorId, mensaje) {
    const input = document.getElementById(inputId);
    const errorDiv = document.getElementById(errorId);

    input.classList.add('input-error');
    errorDiv.innerText = mensaje;
    errorDiv.style.display = 'block';
    input.focus();
}