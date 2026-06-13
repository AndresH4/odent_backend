let codigoGenerado = "";
let esMenor = false;
const acudienteSection = document.getElementById("acudienteSection");
 
function soloLetras(input) {
    input.value = input.value.replace(/[^a-zA-ZÁÉÍÓÚáéíóúñÑ\s]/g, '');
}
 
function soloNumeros(input) {
    input.value = input.value.replace(/\D/g, '');
}
 
// ── INICIO ──
document.addEventListener("DOMContentLoaded", () => {
 
    document.querySelectorAll("#nombres,#apellidos,#nombresAcudiente,#apellidosAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloLetras(this); }));
 
    document.querySelectorAll("#telefono,#documento,#telefonoAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloNumeros(this); }));
 
    document.getElementById("tipoDocumento").addEventListener("change", checkRequisitosAcudiente);
 
    cargarRolesEnFormulario();
});
 
// ── ROLES DESDE BACKEND ──
async function cargarRolesEnFormulario() {
    const selectRol = document.getElementById("rolUsuario");
 
    const rolesFallback = [
        { Nombre_Rol: "Administrador" },
        { Nombre_Rol: "Especialista" },
        { Nombre_Rol: "Paciente" }
    ];
 
    const poblarSelect = (lista) => {
        selectRol.innerHTML = '<option value="">Seleccione un rol</option>';
        lista.forEach(rol => {
            const opcion = document.createElement("option");
            opcion.value = rol.Nombre_Rol;
            opcion.textContent = rol.Nombre_Rol;
            selectRol.appendChild(opcion);
        });
    };
 
    try {
        const respuesta = await fetch("/api/roles");
        if (!respuesta.ok) throw new Error("Respuesta no OK");
        const listaDeRoles = await respuesta.json();
        if (!Array.isArray(listaDeRoles) || listaDeRoles.length === 0) throw new Error("Lista vacía");
        poblarSelect(listaDeRoles);
    } catch (error) {
        console.warn("Backend no disponible, usando roles de respaldo:", error);
        poblarSelect(rolesFallback);
    }
}
 
 
// ── VERIFICAR EDAD ──
function verificarEdad() {
    const fecha = document.getElementById("fechaNacimiento").value;
    if (!fecha) return;
 
    const hoy = new Date();
    const cumple = new Date(fecha);
    let edad = hoy.getFullYear() - cumple.getFullYear();
    const m = hoy.getMonth() - cumple.getMonth();
 
    if (m < 0 || (m === 0 && hoy.getDate() < cumple.getDate())) {
        edad--;
    }
 
    esMenor = (edad < 18);
    checkRequisitosAcudiente();
}
 
function checkRequisitosAcudiente() {
    const tipoDoc = document.getElementById("tipoDocumento").value;
 
    if (tipoDoc === "Tarjeta de identidad" || esMenor) {
        acudienteSection.style.display = "block";
        document.getElementById("correoUsuarioGroup").style.display = "none";
 
        if (esMenor) {
            document.getElementById("tipoDocumento").value = "Tarjeta de identidad";
        }
        replicarCorreoAcudiente();
    } else {
        acudienteSection.style.display = "none";
        document.getElementById("correoUsuarioGroup").style.display = "flex";
    }
}
 
// ── ROL: ESPECIALISTA Y PACIENTE ──
function checkRolEspecialista() {
    const rol = document.getElementById("rolUsuario").value;
    const extra = document.getElementById("especialistaExtra");
    const medicos = document.getElementById("contenedor_datos_medicos");
 
    if (rol === "Especialista" || rol === "2") {
        extra.style.display = "block";
    } else {
        extra.style.display = "none";
    }
 
    if (rol === "Paciente" || rol === "3") {
        medicos.style.display = "block";
    } else {
        medicos.style.display = "none";
        document.getElementById("eps").value = "";
        document.getElementById("tipoAfiliacion").value = "";
    }
}
 
function replicarCorreoAcudiente() {
    if (acudienteSection.style.display === "block") {
        document.getElementById("emailAcudiente").value = document.getElementById("email").value;
    }
}
 
function validarEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
 
function limpiarErrores() {
    document.querySelectorAll(".error-msg").forEach(e => e.innerText = "");
    document.querySelectorAll("input, select").forEach(i => i.classList.remove("invalid"));
}
 
// ── INDICADOR DE PASOS ──
function actualizarIndicador(pasoActual) {
    const dots = document.querySelectorAll(".step-dot");
    const lines = document.querySelectorAll(".step-line");
 
    dots.forEach((dot, i) => {
        dot.classList.remove("active", "done");
        if (i + 1 < pasoActual) dot.classList.add("done");
        else if (i + 1 === pasoActual) dot.classList.add("active");
    });
 
    lines.forEach((line, i) => {
        line.classList.remove("done");
        if (i + 1 < pasoActual) line.classList.add("done");
    });
}
 
// ── VALIDAR PASO 1 ──
function validarPaso1() {
    limpiarErrores();
    let valido = true;
 
    if (nombres.value.length < 2) {
        nombres.classList.add("invalid");
        errorNombres.innerText = "Ingrese sus nombres.";
        valido = false;
    }
 
    if (apellidos.value.length < 2) {
        apellidos.classList.add("invalid");
        errorApellidos.innerText = "Ingrese sus apellidos.";
        valido = false;
    }
 
    if (!fechaNacimiento.value) {
        fechaNacimiento.classList.add("invalid");
        errorFecha.innerText = "Seleccione su fecha de nacimiento.";
        valido = false;
    }
 
    if (!rolUsuario.value) {
        rolUsuario.classList.add("invalid");
        errorRol.innerText = "Seleccione un rol.";
        valido = false;
    }
 
    // Validar Datos Médicos si es Paciente
    if (rolUsuario.value === "Paciente" || rolUsuario.value === "3") {
        if (!document.getElementById("eps").value) {
            document.getElementById("eps").classList.add("invalid");
            document.getElementById("errorEps").innerText = "Seleccione una EPS.";
            valido = false;
        }
        if (!document.getElementById("tipoAfiliacion").value) {
            document.getElementById("tipoAfiliacion").classList.add("invalid");
            document.getElementById("errorAfiliacion").innerText = "Seleccione un tipo de EPS.";
            valido = false;
        }
    }
 
    if (documento.value.length < 5) {
        documento.classList.add("invalid");
        errorDocumento.innerText = "Documento no válido.";
        valido = false;
    }
 
    if (telefono.value.length !== 10) {
        telefono.classList.add("invalid");
        errorTelefono.innerText = "El teléfono debe tener 10 dígitos.";
        valido = false;
    }
 
    const emailAValidar = (document.getElementById("correoUsuarioGroup").style.display === "none")
        ? emailAcudiente.value
        : email.value;
 
    if (!validarEmail(emailAValidar)) {
        if (document.getElementById("correoUsuarioGroup").style.display === "none") {
            emailAcudiente.classList.add("invalid");
            errorEmailAcudiente.innerText = "Ingrese un correo electrónico válido.";
        } else {
            email.classList.add("invalid");
            errorEmail.innerText = "Ingrese un correo electrónico válido.";
        }
        valido = false;
    }
 
    if (valido) {
        codigoGenerado = Math.floor(100000 + Math.random() * 900000);
 
        // Llenar la tarjeta de correo simulada
        const correoMostrar = (document.getElementById("correoUsuarioGroup").style.display === "none")
            ? document.getElementById("emailAcudiente").value
            : document.getElementById("email").value;
 
        const nombreMostrar = document.getElementById("nombres").value;
 
        document.getElementById("codigoVisible").innerText = codigoGenerado;
        document.getElementById("emailDestino").innerText = correoMostrar;
        document.getElementById("nombreDestinatario").innerText = nombreMostrar;
 
        step1.classList.remove("active");
        step2.classList.add("active");
        actualizarIndicador(2);
    }
}
 
// ── VERIFICAR CÓDIGO ──
function verificarCodigo() {
    if (codigo.value == codigoGenerado) {
        step2.classList.remove("active");
        step3.classList.add("active");
        actualizarIndicador(3);
    } else {
        errorCodigo.innerText = "Código incorrecto.";
    }
}
 
function validarPassword(pass) {
    return /^(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/.test(pass);
}
 
// ── CREAR USUARIO ──
function crearUsuario() {
    limpiarErrores();
 
    if (!validarPassword(password.value)) {
        password.classList.add("invalid");
        errorPassword.innerText = "La contraseña no cumple los requisitos.";
        return;
    }
 
    if (password.value !== confirmPassword.value) {
        confirmPassword.classList.add("invalid");
        errorConfirm.innerText = "Las contraseñas no coinciden.";
        return;
    }
 
    const correoRegistro = (document.getElementById("correoUsuarioGroup").style.display === "none"
        ? emailAcudiente.value
        : email.value).toLowerCase();
 
    const rolSeleccionado = document.getElementById("rolUsuario").value;
    const especialidadSeleccionada = document.getElementById("especialidadMedica").value;
    const epsSeleccionada = document.getElementById("eps").value;
    const afiliacionSeleccionada = document.getElementById("tipoAfiliacion").value;
 
    let tabsConfig = ["Inicio"];
    let btnConfig = "Ver perfil";
 
    if (rolSeleccionado === "Paciente") {
        tabsConfig = ["Panel de citas", "Historial Personal"];
        btnConfig = "Agendar cita";
    } else if (rolSeleccionado === "Especialista") {
        tabsConfig = ["Agenda", "Pacientes", "Ranking"];
        btnConfig = "Ver mi agenda";
    } else if (rolSeleccionado === "Administrador") {
        tabsConfig = ["Usuarios", "Citas", "Sistema"];
        btnConfig = "Gestionar Sistema";
    }
 
    const nuevoUsuario = {
        nombre: nombres.value + " " + apellidos.value,
        pass: password.value,
        rol: rolSeleccionado,
        especialidad: especialidadSeleccionada,
        email: correoRegistro,
        esMenor: esMenor,
        foto: "",
        data: [
            ["Documento", documento.value],
            ["Tipo", document.getElementById("tipoDocumento").value],
            ["Estado", "Activo"]
        ],
        btn: btnConfig,
        tabs: tabsConfig
    };
 
    let dbLocal = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    dbLocal[correoRegistro] = nuevoUsuario;
    localStorage.setItem('usuarios_dental', JSON.stringify(dbLocal));
 
    let idRolNumerico = parseInt(rolSeleccionado);
    if (isNaN(idRolNumerico)) {
        if (rolSeleccionado === "Paciente") idRolNumerico = 3;
        else if (rolSeleccionado === "Especialista") idRolNumerico = 2;
        else if (rolSeleccionado === "Administrador") idRolNumerico = 1;
        else idRolNumerico = 3;
    }
 
    const datosUsuarioBackend = {
        nombres: nombres.value,
        apellidos: apellidos.value,
        documento: documento.value,
        telefono: telefono.value,
        correo: correoRegistro,
        contrasena: password.value,
        rol_id: idRolNumerico,
        genero_id: 1,
        tipo_documento_id: 1,
        estado_id: 1,
        eps_id: epsSeleccionada || null,
        tipo_afiliacion_id: afiliacionSeleccionada || null,
        fecha_nacimiento: document.getElementById("fechaNacimiento").value
    };
 
    fetch('/api/usuarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datosUsuarioBackend)
    })
    .then(respuesta => {
        if (!respuesta.ok) {
            console.error('El servidor Flask respondió con un error, pero mantendremos la UI activa.');
        }
        return respuesta.json();
    })
    .then(resultado => {
        console.log('Respuesta del backend SQLite:', resultado);
    })
    .catch(error => {
        console.error('Error de red al conectar con Flask:', error);
    });
 
    document.getElementById("groupPassword").style.display = "none";
    document.getElementById("groupConfirm").style.display = "none";
    document.getElementById("btnFinalizar").style.display = "none";
 
    mensajeFinal.innerText = "¡Usuario " + rolSeleccionado + " creado correctamente!";
    document.getElementById("btnIrAlLogin").style.display = "flex";
}
 
function abrirLogin() {
    window.location.href = "login.html";
}
 
function togglePassword(id) {
    const input = document.getElementById(id);
    input.type = input.type === "password" ? "text" : "password";
}