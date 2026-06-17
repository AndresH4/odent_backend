/**
 * creacion.js — Stylo Dental
 *
 * Responsabilidades:
 *  1. Cargar catálogos (roles, EPS) desde el backend.
 *  2. Validar el formulario paso a paso.
 *  3. Enviar código de verificación y confirmarlo.
 *  4. Construir el payload COMPLETO (incluyendo EPS, tarjeta profesional,
 *     especialidad, tipo de afiliación, género, tipo de documento) y
 *     enviarlo al backend transaccional POST /api/usuarios.
 *  5. Notificar al usuario sobre éxito o cualquier fallo ocurrido.
 */
 
"use strict";
 
// ── ESTADO GLOBAL ──────────────────────────────────────────────────────────────
let correoVerificacion  = "";
let esMenor             = false;
const EPS_OTRO_VALUE    = '__OTRO__';
let todasLasEPS         = [];
 
const acudienteSection  = document.getElementById("acudienteSection");
 
// ── HELPERS DE ENTRADA ─────────────────────────────────────────────────────────
function soloLetras(input) {
    input.value = input.value.replace(/[^a-zA-ZÁÉÍÓÚáéíóúñÑ\s]/g, '');
}
function soloNumeros(input) {
    input.value = input.value.replace(/\D/g, '');
}
function validarEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
function validarPassword(pass) {
    return /^(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/.test(pass);
}
 
// ── NOTIFICACIÓN AL USUARIO ────────────────────────────────────────────────────
/**
 * Muestra un mensaje de error visible en la UI.
 * Usa un elemento con id="mensajeError" si existe; si no, hace alert().
 */
function mostrarError(mensaje) {
    const el = document.getElementById("mensajeError");
    if (el) {
        el.innerText = mensaje;
        el.style.display = "block";
        // Auto-ocultar tras 8 segundos
        setTimeout(() => { el.style.display = "none"; }, 8000);
    } else {
        alert("Error: " + mensaje);
    }
    console.error("[crearUsuario] Error:", mensaje);
}
 
function limpiarMensajeError() {
    const el = document.getElementById("mensajeError");
    if (el) { el.style.display = "none"; el.innerText = ""; }
}
 
// ── INICIALIZACIÓN ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
 
    document.querySelectorAll("#nombres,#apellidos,#nombresAcudiente,#apellidosAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloLetras(this); }));
 
    document.querySelectorAll("#telefono,#documento,#telefonoAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloNumeros(this); }));
 
    document.getElementById("tipoDocumento")
        .addEventListener("change", checkRequisitosAcudiente);
 
    cargarRolesEnFormulario();
    cargarEPSEnFormulario();
});
 
// ── CATÁLOGO: EPS ──────────────────────────────────────────────────────────────
async function cargarEPSEnFormulario() {
    const selectEps = document.getElementById("eps");
 
    const epsFallback = [
        { ID_EPS: 1, Nombre_EPS: 'Compensar' },
        { ID_EPS: 2, Nombre_EPS: 'Salud Total' },
        { ID_EPS: 3, Nombre_EPS: 'NuevaEPS' },
        { ID_EPS: 4, Nombre_EPS: 'Famisanar' },
        { ID_EPS: 5, Nombre_EPS: 'Sanitas' },
        { ID_EPS: 6, Nombre_EPS: 'CapitalSalud' },
        { ID_EPS: 7, Nombre_EPS: 'Sura' },
    ];
 
    const poblarEPS = (lista) => {
        todasLasEPS = lista;
        selectEps.innerHTML = '<option value="">Seleccione una EPS...</option>';
        lista.forEach(eps => {
            const opt = document.createElement('option');
            opt.value       = eps.ID_EPS;
            opt.textContent = eps.Nombre_EPS;
            selectEps.appendChild(opt);
        });
        const optOtro = document.createElement('option');
        optOtro.value       = EPS_OTRO_VALUE;
        optOtro.textContent = 'Otro';
        selectEps.appendChild(optOtro);
    };
 
    try {
        const res  = await fetch('/api/eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Error al cargar EPS');
        poblarEPS(data.data);
    } catch (err) {
        console.warn('Usando lista de EPS de respaldo:', err);
        poblarEPS(epsFallback);
    }
}
 
// Muestra/oculta los campos de EPS personalizada
function manejarSeleccionEPSCreacion() {
    const epsSelect     = document.getElementById('eps');
    const otroContainer = document.getElementById('eps-otro-container-creacion');
    if (epsSelect.value === EPS_OTRO_VALUE) {
        otroContainer.style.display = 'block';
    } else {
        otroContainer.style.display = 'none';
        document.getElementById('eps-otro-nombre-creacion').value   = '';
        document.getElementById('eps-otro-telefono-creacion').value = '';
    }
}
 
// Crea la EPS en el backend y devuelve el ID asignado (o null si falla)
async function crearNuevaEPS(nombre, telefono, tipoEpsId = 1) {
    try {
        const res = await fetch('/api/eps', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Nombre_EPS: nombre, ID_Tipo_EPS: tipoEpsId, Telefono: telefono })
        });
        const data = await res.json();
        if (!data.ok) {
            console.error('Error al crear EPS:', data.error);
            return null;
        }
        return data.data.ID_EPS;
    } catch (err) {
        console.error('[crearNuevaEPS]', err);
        return null;
    }
}
 
// ── CATÁLOGO: ROLES ────────────────────────────────────────────────────────────
async function cargarRolesEnFormulario() {
    const selectRol = document.getElementById("rolUsuario");
    const rolesFallback = [
        { Rol_ID: 1, Nombre_Rol: "Administrador" },
        { Rol_ID: 2, Nombre_Rol: "Especialista" },
        { Rol_ID: 3, Nombre_Rol: "Paciente" }
    ];
 
    const poblarRoles = (lista) => {
        selectRol.innerHTML = '<option value="">Seleccione un rol</option>';
        lista.forEach(rol => {
            const opt = document.createElement("option");
            // Guardamos el ID numérico como value para enviarlo directo al backend
            opt.value       = rol.Rol_ID || rol.Nombre_Rol;
            opt.textContent = rol.Nombre_Rol || rol.Descripcion;
            selectRol.appendChild(opt);
        });
    };
 
    try {
        const res  = await fetch("/api/roles");
        if (!res.ok) throw new Error("Respuesta no OK");
        const lista = await res.json();
        if (!Array.isArray(lista) || lista.length === 0) throw new Error("Lista vacía");
        poblarRoles(lista);
    } catch (err) {
        console.warn("Backend no disponible, usando roles de respaldo:", err);
        poblarRoles(rolesFallback);
    }
}
 
// ── LÓGICA DE FORMULARIO ───────────────────────────────────────────────────────
function verificarEdad() {
    const fecha = document.getElementById("fechaNacimiento").value;
    if (!fecha) return;
    const hoy   = new Date();
    const cumple = new Date(fecha);
    let edad = hoy.getFullYear() - cumple.getFullYear();
    const m  = hoy.getMonth() - cumple.getMonth();
    if (m < 0 || (m === 0 && hoy.getDate() < cumple.getDate())) edad--;
    esMenor = (edad < 18);
    checkRequisitosAcudiente();
}
 
function checkRequisitosAcudiente() {
    const tipoDoc = document.getElementById("tipoDocumento").value;
    if (tipoDoc === "Tarjeta de identidad" || esMenor) {
        acudienteSection.style.display = "block";
        document.getElementById("correoUsuarioGroup").style.display = "none";
        if (esMenor) document.getElementById("tipoDocumento").value = "Tarjeta de identidad";
        replicarCorreoAcudiente();
    } else {
        acudienteSection.style.display = "none";
        document.getElementById("correoUsuarioGroup").style.display = "flex";
    }
}
 
function checkRolEspecialista() {
    const rolVal = document.getElementById("rolUsuario").value;
    // Normalizar: puede venir como "2" o "Especialista"
    const esEspecialista = (rolVal === "2" || rolVal === "Especialista");
    const esPaciente     = (rolVal === "3" || rolVal === "Paciente");
 
    document.getElementById("especialistaExtra").style.display  = esEspecialista ? "block" : "none";
    document.getElementById("contenedor_datos_medicos").style.display = esPaciente ? "block" : "none";
 
    if (!esPaciente) {
        document.getElementById("eps").value = "";
        document.getElementById("tipoAfiliacion").value = "";
        document.getElementById("eps-otro-container-creacion").style.display = "none";
    }
}
 
function replicarCorreoAcudiente() {
    if (acudienteSection.style.display === "block") {
        document.getElementById("emailAcudiente").value =
            document.getElementById("email").value;
    }
}
 
function limpiarErrores() {
    document.querySelectorAll(".error-msg").forEach(e => e.innerText = "");
    document.querySelectorAll("input, select").forEach(i => i.classList.remove("invalid"));
    limpiarMensajeError();
}
 
// ── INDICADOR DE PASOS ─────────────────────────────────────────────────────────
function actualizarIndicador(pasoActual) {
    document.querySelectorAll(".step-dot").forEach((dot, i) => {
        dot.classList.remove("active", "done");
        if (i + 1 < pasoActual) dot.classList.add("done");
        else if (i + 1 === pasoActual) dot.classList.add("active");
    });
    document.querySelectorAll(".step-line").forEach((line, i) => {
        line.classList.remove("done");
        if (i + 1 < pasoActual) line.classList.add("done");
    });
}
 
// ── PASO 1: VALIDACIÓN Y ENVÍO DE CÓDIGO ──────────────────────────────────────
function validarPaso1() {
    limpiarErrores();
    let valido = true;
 
    const nombres        = document.getElementById("nombres");
    const apellidos      = document.getElementById("apellidos");
    const fechaNacimiento = document.getElementById("fechaNacimiento");
    const rolUsuario     = document.getElementById("rolUsuario");
    const documento      = document.getElementById("documento");
    const telefono       = document.getElementById("telefono");
 
    if (nombres.value.trim().length < 2) {
        nombres.classList.add("invalid");
        document.getElementById("errorNombres").innerText = "Ingrese sus nombres.";
        valido = false;
    }
    if (apellidos.value.trim().length < 2) {
        apellidos.classList.add("invalid");
        document.getElementById("errorApellidos").innerText = "Ingrese sus apellidos.";
        valido = false;
    }
    if (!fechaNacimiento.value) {
        fechaNacimiento.classList.add("invalid");
        document.getElementById("errorFecha").innerText = "Seleccione su fecha de nacimiento.";
        valido = false;
    }
    if (!rolUsuario.value) {
        rolUsuario.classList.add("invalid");
        document.getElementById("errorRol").innerText = "Seleccione un rol.";
        valido = false;
    }
 
    // Validar campos específicos de Paciente
    const rolVal     = rolUsuario.value;
    const esPaciente = (rolVal === "3" || rolVal === "Paciente");
    if (esPaciente) {
        const epsVal = document.getElementById("eps").value;
        if (!epsVal) {
            document.getElementById("eps").classList.add("invalid");
            document.getElementById("errorEps").innerText = "Seleccione una EPS.";
            valido = false;
        } else if (epsVal === EPS_OTRO_VALUE) {
            const nombreOtro   = document.getElementById('eps-otro-nombre-creacion');
            const telefonoOtro = document.getElementById('eps-otro-telefono-creacion');
            if (!nombreOtro.value.trim()) {
                nombreOtro.classList.add('invalid');
                document.getElementById('err-eps-otro-nombre-creacion').innerText =
                    'Ingrese el nombre de la nueva EPS.';
                valido = false;
            }
            if (!telefonoOtro.value.trim()) {
                telefonoOtro.classList.add('invalid');
                document.getElementById('err-eps-otro-telefono-creacion').innerText =
                    'Ingrese el teléfono de la nueva EPS.';
                valido = false;
            }
        }
        if (!document.getElementById("tipoAfiliacion").value) {
            document.getElementById("tipoAfiliacion").classList.add("invalid");
            document.getElementById("errorAfiliacion").innerText = "Seleccione un tipo de afiliación.";
            valido = false;
        }
    }
 
    // Validar tarjeta profesional si es Especialista
    const esEspecialista = (rolVal === "2" || rolVal === "Especialista");
    if (esEspecialista) {
        const tarjeta = document.getElementById("tarjetaProfesional");
        if (tarjeta && tarjeta.value.trim().length < 5) {
            tarjeta.classList.add("invalid");
            const errTarjeta = document.getElementById("errorTarjeta");
            if (errTarjeta) errTarjeta.innerText = "Ingrese la tarjeta profesional.";
            valido = false;
        }
    }
 
    if (documento.value.trim().length < 5) {
        documento.classList.add("invalid");
        document.getElementById("errorDocumento").innerText = "Documento no válido.";
        valido = false;
    }
    if (telefono.value.trim().length !== 10) {
        telefono.classList.add("invalid");
        document.getElementById("errorTelefono").innerText = "El teléfono debe tener 10 dígitos.";
        valido = false;
    }
 
    const correoUsado = (document.getElementById("correoUsuarioGroup").style.display === "none")
        ? document.getElementById("emailAcudiente").value
        : document.getElementById("email").value;
 
    if (!validarEmail(correoUsado)) {
        if (document.getElementById("correoUsuarioGroup").style.display === "none") {
            document.getElementById("emailAcudiente").classList.add("invalid");
            document.getElementById("errorEmailAcudiente").innerText = "Correo electrónico inválido.";
        } else {
            document.getElementById("email").classList.add("invalid");
            document.getElementById("errorEmail").innerText = "Correo electrónico inválido.";
        }
        valido = false;
    }
 
    if (!valido) return;
 
    // Enviar código de verificación
    correoVerificacion = correoUsado.trim().toLowerCase();
    const nombreMostrar = document.getElementById("nombres").value;
    const btnContinuar  = document.querySelector("#step1 button");
 
    btnContinuar.disabled = true;
    btnContinuar.innerHTML = "Enviando código...";
 
    fetch("/api/enviar-codigo", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ correo: correoVerificacion, nombre: nombreMostrar })
    })
    .then(r => r.json())
    .then(data => {
        btnContinuar.disabled = false;
        btnContinuar.innerHTML = "Continuar &#8594;";
        if (data.ok) {
            document.getElementById("emailDestino").innerText      = correoVerificacion;
            document.getElementById("nombreDestinatario").innerText = nombreMostrar;
            document.getElementById("step1").classList.remove("active");
            document.getElementById("step2").classList.add("active");
            actualizarIndicador(2);
        } else {
            mostrarError("Error al enviar el código: " + (data.error || "Intenta de nuevo."));
        }
    })
    .catch(() => {
        btnContinuar.disabled = false;
        btnContinuar.innerHTML = "Continuar &#8594;";
        mostrarError("No se pudo conectar con el servidor. Verifica tu conexión.");
    });
}
 
// ── PASO 2: VERIFICAR CÓDIGO ───────────────────────────────────────────────────
function verificarCodigo() {
    const ingresado  = document.getElementById("codigo").value.trim();
    const errorCodigo = document.getElementById("errorCodigo");
 
    if (!ingresado) {
        errorCodigo.innerText = "Ingresa el código.";
        return;
    }
 
    const btnVerificar = document.querySelector("#step2 button");
    btnVerificar.disabled = true;
    btnVerificar.innerHTML = "Verificando...";
 
    fetch("/api/verificar-codigo", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ correo: correoVerificacion, codigo: ingresado })
    })
    .then(r => r.json())
    .then(data => {
        btnVerificar.disabled = false;
        btnVerificar.innerHTML = "Verificar código ✓";
        if (data.ok) {
            document.getElementById("step2").classList.remove("active");
            document.getElementById("step3").classList.add("active");
            actualizarIndicador(3);
        } else {
            errorCodigo.innerText = "Código incorrecto. Inténtalo de nuevo.";
            document.getElementById("codigo").classList.add("invalid");
        }
    })
    .catch(() => {
        btnVerificar.disabled = false;
        btnVerificar.innerHTML = "Verificar código ✓";
        document.getElementById("errorCodigo").innerText = "Error de conexión. Intenta de nuevo.";
    });
}
 
// ── PASO 3: CREAR USUARIO (payload completo + manejo de errores) ───────────────
async function crearUsuario() {
    limpiarErrores();
 
    const password        = document.getElementById("password");
    const confirmPassword = document.getElementById("confirmPassword");
    const mensajeFinal    = document.getElementById("mensajeFinal");
 
    if (!validarPassword(password.value)) {
        password.classList.add("invalid");
        document.getElementById("errorPassword").innerText =
            "Mínimo 8 caracteres, una mayúscula, un número y un símbolo.";
        return;
    }
    if (password.value !== confirmPassword.value) {
        confirmPassword.classList.add("invalid");
        document.getElementById("errorConfirm").innerText = "Las contraseñas no coinciden.";
        return;
    }
 
    // ── Leer todos los campos del formulario ──────────────────────────────────
    const correoRegistro = (
        document.getElementById("correoUsuarioGroup").style.display === "none"
            ? document.getElementById("emailAcudiente").value
            : document.getElementById("email").value
    ).trim().toLowerCase();
 
    const rolSelect      = document.getElementById("rolUsuario");
    const rolValor       = rolSelect.value;                      // "1", "2", "3" o texto
    const rolTexto       = rolSelect.options[rolSelect.selectedIndex]?.text || "";
 
    // Normalizar rol_id a entero
    let rolIdNumerico = parseInt(rolValor, 10);
    if (isNaN(rolIdNumerico)) {
        if (rolTexto === "Paciente")      rolIdNumerico = 3;
        else if (rolTexto === "Especialista") rolIdNumerico = 2;
        else if (rolTexto === "Administrador") rolIdNumerico = 1;
        else rolIdNumerico = 3;
    }
 
    // Género: leer del select si existe, default 1
    const generoSelect  = document.getElementById("genero");
    const generoId      = generoSelect ? parseInt(generoSelect.value, 10) || 1 : 1;
 
    // Tipo de documento: mapear texto a ID
    const tipoDocTexto  = document.getElementById("tipoDocumento").value;
    const mapaTipoDoc   = {
        "Cedula de ciudadania": 1,
        "Tarjeta de identidad": 2,
        "Permiso por protección temporal": 3
    };
    const tipoDocId = mapaTipoDoc[tipoDocTexto] || 1;
 
    // EPS: puede requerir crear una nueva antes del registro de usuario
    const epsSelect = document.getElementById("eps");
    let epsId       = epsSelect.value === EPS_OTRO_VALUE ? null : (parseInt(epsSelect.value, 10) || null);
 
    if (epsSelect.value === EPS_OTRO_VALUE) {
        const nombreOtro   = document.getElementById('eps-otro-nombre-creacion').value.trim();
        const telefonoOtro = document.getElementById('eps-otro-telefono-creacion').value.trim();
 
        mostrarProgreso("Registrando nueva EPS...");
        const nuevoEpsId = await crearNuevaEPS(nombreOtro, telefonoOtro, 1);
 
        if (!nuevoEpsId) {
            mostrarError("No se pudo registrar la nueva EPS. Intenta de nuevo.");
            return;
        }
        epsId = nuevoEpsId;
        await cargarEPSEnFormulario();   // refrescar select
    }
 
    const tipoAfiliacionId = parseInt(document.getElementById("tipoAfiliacion").value, 10) || null;
 
    // Especialista: tarjeta y especialidad
    const tarjetaEl         = document.getElementById("tarjetaProfesional");
    const tarjetaProfesional = tarjetaEl ? tarjetaEl.value.trim() : "";
 
    const especialidadEl  = document.getElementById("especialidadMedica");
    const especialidadId  = especialidadEl && especialidadEl.value
        ? parseInt(especialidadEl.value, 10)
        : null;
 
    // ── Construir payload que refleja exactamente lo que espera el backend ────
    /** @type {Object} */
    const datosUsuarioBackend = {
        nombres:            document.getElementById("nombres").value.trim(),
        apellidos:          document.getElementById("apellidos").value.trim(),
        documento:          document.getElementById("documento").value.trim(),
        telefono:           document.getElementById("telefono").value.trim(),
        correo:             correoRegistro,
        contrasena:         password.value,
        fecha_nacimiento:   document.getElementById("fechaNacimiento").value,
        genero_id:          generoId,
        tipo_documento_id:  tipoDocId,
        estado_id:          1,               // Activo por defecto
        rol_id:             rolIdNumerico,
 
        // Paciente
        eps_id:             epsId,
        tipo_afiliacion_id: tipoAfiliacionId,
 
        // Especialista
        tarjeta_profesional: tarjetaProfesional || null,
        especialidad_id:     especialidadId
    };
 
    // ── Enviar al backend transaccional ────────────────────────────────────────
    const btnFinalizar = document.getElementById("btnFinalizar");
    if (btnFinalizar) {
        btnFinalizar.disabled = true;
        btnFinalizar.innerHTML = "Creando usuario...";
    }
 
    try {
        const respuesta = await fetch('/api/usuarios', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(datosUsuarioBackend)
        });
 
        const resultado = await respuesta.json();
 
        if (btnFinalizar) {
            btnFinalizar.disabled = false;
            btnFinalizar.innerHTML = "Finalizar";
        }
 
        if (!resultado.ok) {
            // El backend hizo ROLLBACK: mostrar el mensaje exacto
            mostrarError(
                "No se pudo crear el usuario: " +
                (resultado.error || "Error desconocido. Revisa los datos e intenta de nuevo.")
            );
            return;    // Detenemos aquí; el formulario sigue visible para corregir
        }
 
        // ── Éxito: mostrar confirmación y botón de login ───────────────────
        console.log("Usuario creado con ID:", resultado.usuario_id);
 
        document.getElementById("groupPassword").style.display  = "none";
        document.getElementById("groupConfirm").style.display   = "none";
        if (btnFinalizar) btnFinalizar.style.display            = "none";
 
        mensajeFinal.innerText = "¡Usuario registrado correctamente!";
        document.getElementById("btnIrAlLogin").style.display = "flex";
 
    } catch (errorRed) {
        if (btnFinalizar) {
            btnFinalizar.disabled = false;
            btnFinalizar.innerHTML = "Finalizar";
        }
        mostrarError(
            "Error de conexión con el servidor. Verifica tu red e intenta de nuevo. " +
            "(" + errorRed.message + ")"
        );
    }
}
 
// ── UTILIDAD: indicador de progreso en mensajeFinal ───────────────────────────
function mostrarProgreso(texto) {
    const el = document.getElementById("mensajeFinal");
    if (el) el.innerText = texto;
}
 
// ── NAVEGACIÓN ─────────────────────────────────────────────────────────────────
function abrirLogin() {
    window.location.href = "/login.html";
}
 
function togglePassword(id) {
    const input = document.getElementById(id);
    if (input) input.type = input.type === "password" ? "text" : "password";
}