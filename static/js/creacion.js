"use strict";

// ── ESTADO GLOBAL ──────────────────────────────────────────────────────────────
let correoVerificacion = "";
let esMenor           = false;
const EPS_OTRO_VALUE  = '__OTRO__';

let todasLasEPS    = [];
let epsFiltradas   = [];
let todosTiposEps  = [];

const acudienteSection = document.getElementById("acudienteSection");

// ── HELPERS ────────────────────────────────────────────────────────────────────
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

// ── NOTIFICACIONES ─────────────────────────────────────────────────────────────
function mostrarError(mensaje) {
    const el = document.getElementById("mensajeError");
    if (el) {
        el.innerText = mensaje;
        el.style.display = "block";
        setTimeout(() => { el.style.display = "none"; }, 8000);
    } else {
        alert("Error: " + mensaje);
    }
}
function limpiarMensajeError() {
    const el = document.getElementById("mensajeError");
    if (el) { el.style.display = "none"; el.innerText = ""; }
}

// ── CAMPO FECHA: LÓGICA DE PLACEHOLDER + FORMATO MANUAL ──────────────────────
function inicializarCampoFecha() {
    const inputTexto  = document.getElementById("fechaNacimiento");
    const inputNativo = document.getElementById("fechaNacimientoNative");
    const btnCalendario = document.getElementById("datePickerBtn");

    if (!inputTexto || !inputNativo || !btnCalendario) return;

    // Al ganar foco: cambiar placeholder a formato
    inputTexto.addEventListener("focus", () => {
        inputTexto.placeholder = "DD/MM/AAAA";
        inputTexto.classList.add("typing-mode");
    });

    // Al perder foco: restaurar placeholder descriptivo si vacío
    inputTexto.addEventListener("blur", () => {
        if (!inputTexto.value) {
            inputTexto.placeholder = "Ingrese su fecha de nacimiento";
            inputTexto.classList.remove("typing-mode");
        }
    });

    // Formateo automático con separadores mientras escribe
    inputTexto.addEventListener("input", (e) => {
        let raw = inputTexto.value.replace(/\D/g, '').slice(0, 8);
        let formatted = '';

        if (raw.length > 0) formatted += raw.slice(0, 2);
        if (raw.length > 2) formatted += '/' + raw.slice(2, 4);
        if (raw.length > 4) formatted += '/' + raw.slice(4, 8);

        inputTexto.value = formatted;

        // Sincronizar con input nativo cuando la fecha está completa (DD/MM/AAAA)
        if (raw.length === 8) {
            const dd   = raw.slice(0, 2);
            const mm   = raw.slice(2, 4);
            const yyyy = raw.slice(4, 8);
            const isoDate = `${yyyy}-${mm}-${dd}`;
            inputNativo.value = isoDate;
            verificarEdad();
        } else {
            inputNativo.value = '';
        }
    });

    // Botón de calendario: abrir el date picker nativo
    btnCalendario.addEventListener("click", () => {
        // Mostrar el input nativo brevemente para disparar el picker
        inputNativo.style.position   = 'absolute';
        inputNativo.style.opacity    = '0';
        inputNativo.style.width      = '1px';
        inputNativo.style.height     = '1px';
        inputNativo.style.pointerEvents = 'auto';
        inputNativo.showPicker ? inputNativo.showPicker() : inputNativo.click();
    });

    // Cuando el usuario elige una fecha del picker nativo, reflejarla en el campo texto
    inputNativo.addEventListener("change", () => {
        const val = inputNativo.value; // formato YYYY-MM-DD
        if (!val) return;
        const [yyyy, mm, dd] = val.split('-');
        inputTexto.value = `${dd}/${mm}/${yyyy}`;
        verificarEdad();
    });
}

// ── LEER FECHA DEL CAMPO TEXTO (retorna YYYY-MM-DD para el backend) ───────────
function leerFechaISO() {
    const inputTexto  = document.getElementById("fechaNacimiento");
    const inputNativo = document.getElementById("fechaNacimientoNative");

    // Si el nativo tiene valor (sync via picker o escritura completa), usarlo
    if (inputNativo && inputNativo.value) return inputNativo.value;

    // Fallback: parsear campo texto manualmente
    if (inputTexto && inputTexto.value) {
        const parts = inputTexto.value.split('/');
        if (parts.length === 3 && parts[2].length === 4) {
            return `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
    }
    return '';
}

// ── INICIALIZACIÓN ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("#nombres,#apellidos,#nombresAcudiente,#apellidosAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloLetras(this); }));

    document.querySelectorAll("#telefono,#documento,#telefonoAcudiente")
        .forEach(el => el.addEventListener("input", function () { soloNumeros(this); }));

    document.getElementById("tipoDocumento")
        .addEventListener("change", checkRequisitosAcudiente);

    inicializarCampoFecha();
    cargarRolesEnFormulario();
    cargarRegimenesEnFormulario();
    cargarTiposEpsEnFormulario();
    cargarTodasLasEPS();
});

// ── CATÁLOGO: REGÍMENES ────────────────────────────────────────────────────────
async function cargarRegimenesEnFormulario() {
    const select   = document.getElementById("regimen");
    const fallback = [
        { Regimen_ID: 1, Descripcion: 'Contributivo' },
        { Regimen_ID: 2, Descripcion: 'Subsidiado' }
    ];

    const poblar = (lista) => {
        select.innerHTML = '<option value="">Seleccione el régimen...</option>';
        lista.forEach(r => {
            const opt = document.createElement('option');
            opt.value       = r.Regimen_ID || r.ID_Regimen_EPS;
            opt.textContent = r.Descripcion || r.Nombre_Regimen;
            select.appendChild(opt);
        });
    };

    try {
        const res  = await fetch('/api/regimen-eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        poblar(data.data);
    } catch (err) {
        console.warn('Regímenes fallback:', err);
        poblar(fallback);
    }
}

// ── CATÁLOGO: TIPOS DE EPS ─────────────────────────────────────────────────────
async function cargarTiposEpsEnFormulario() {
    const fallback = [
        { TipoEPS_ID: 1, Nombre_Tipo: 'Cotizante' },
        { TipoEPS_ID: 2, Nombre_Tipo: 'Beneficiario' }
    ];
    try {
        const res  = await fetch('/api/tipo-eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        todosTiposEps = data.data;
    } catch (err) {
        console.warn('Tipos EPS fallback:', err);
        todosTiposEps = fallback;
    }
}

// ── CATÁLOGO: TODAS LAS EPS ────────────────────────────────────────────────────
async function cargarTodasLasEPS() {
    const fallback = [
        { ID_EPS: 1, Nombre_EPS: 'Compensar',   Regimen_ID: 1 },
        { ID_EPS: 2, Nombre_EPS: 'Salud Total',  Regimen_ID: 1 },
        { ID_EPS: 3, Nombre_EPS: 'NuevaEPS',     Regimen_ID: 1 },
        { ID_EPS: 4, Nombre_EPS: 'Famisanar',    Regimen_ID: 1 },
        { ID_EPS: 5, Nombre_EPS: 'Sanitas',      Regimen_ID: 1 },
        { ID_EPS: 6, Nombre_EPS: 'CapitalSalud', Regimen_ID: 2 },
        { ID_EPS: 7, Nombre_EPS: 'Sura',         Regimen_ID: 1 },
    ];
    try {
        const res  = await fetch('/api/eps');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        todasLasEPS = data.data;
    } catch (err) {
        console.warn('EPS fallback:', err);
        todasLasEPS = fallback;
    }
}

// ── CASCADING: RÉGIMEN → TIPO EPS → EPS ───────────────────────────────────────
function onRegimenChange() {
    const regimenId  = document.getElementById('regimen').value;
    const selectTipo = document.getElementById('tipoEps');
    const selectEps  = document.getElementById('eps');

    document.getElementById('errorRegimen').innerText = '';
    document.getElementById('regimen').classList.remove('invalid');

    selectTipo.innerHTML = '<option value="">Seleccione el tipo de EPS...</option>';
    selectEps.innerHTML  = '<option value="">Seleccione primero el tipo de EPS</option>';
    selectTipo.disabled  = true;
    selectEps.disabled   = true;
    document.getElementById('eps-otro-container-creacion').style.display = 'none';

    if (!regimenId) return;

    todosTiposEps.forEach(t => {
        const opt = document.createElement('option');
        opt.value       = t.TipoEPS_ID || t.ID_Tipo_EPS;
        opt.textContent = t.Nombre_Tipo;
        selectTipo.appendChild(opt);
    });
    selectTipo.disabled = false;

    epsFiltradas = todasLasEPS.filter(e => String(e.Regimen_ID) === String(regimenId));
}

function onTipoEpsChange() {
    const selectEps  = document.getElementById('eps');
    const selectTipo = document.getElementById('tipoEps');

    document.getElementById('errorTipoEps').innerText = '';
    selectTipo.classList.remove('invalid');

    selectEps.innerHTML = '<option value="">Seleccione la EPS...</option>';
    selectEps.disabled  = true;
    document.getElementById('eps-otro-container-creacion').style.display = 'none';

    if (!selectTipo.value) return;

    const lista = epsFiltradas.length > 0 ? epsFiltradas : todasLasEPS;
    lista.forEach(eps => {
        const opt = document.createElement('option');
        opt.value       = eps.ID_EPS || eps.EPS_ID;
        opt.textContent = eps.Nombre_EPS;
        selectEps.appendChild(opt);
    });

    const optOtro = document.createElement('option');
    optOtro.value       = EPS_OTRO_VALUE;
    optOtro.textContent = 'Otro';
    selectEps.appendChild(optOtro);

    selectEps.disabled = false;
}

function manejarSeleccionEPSCreacion() {
    const epsSelect     = document.getElementById('eps');
    const otroContainer = document.getElementById('eps-otro-container-creacion');
    document.getElementById('errorEps').innerText = '';
    epsSelect.classList.remove('invalid');

    if (epsSelect.value === EPS_OTRO_VALUE) {
        otroContainer.style.display = 'block';
    } else {
        otroContainer.style.display = 'none';
        document.getElementById('eps-otro-nombre-creacion').value   = '';
        document.getElementById('eps-otro-telefono-creacion').value = '';
    }
}

// ── CATÁLOGO: ROLES ────────────────────────────────────────────────────────────
async function cargarRolesEnFormulario() {
    const selectRol     = document.getElementById("rolUsuario");
    const rolesFallback = [
        { Rol_ID: 1, Nombre_Rol: "Administrador" },
        { Rol_ID: 2, Nombre_Rol: "Especialista"  },
        { Rol_ID: 3, Nombre_Rol: "Paciente"      }
    ];

    const poblarRoles = (lista) => {
        selectRol.innerHTML = '<option value="">Seleccione un rol</option>';
        lista.forEach(rol => {
            const opt = document.createElement("option");
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
        console.warn("Roles fallback:", err);
        poblarRoles(rolesFallback);
    }
}

// ── LÓGICA DE FORMULARIO ───────────────────────────────────────────────────────
function verificarEdad() {
    const fechaISO = leerFechaISO();
    if (!fechaISO) return;

    const hoy    = new Date();
    const cumple = new Date(fechaISO);
    if (isNaN(cumple.getTime())) return;

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
    const rolVal         = document.getElementById("rolUsuario").value;
    const esEspecialista = (rolVal === "2" || rolVal === "Especialista");
    const esPaciente     = (rolVal === "3" || rolVal === "Paciente");

    document.getElementById("especialistaExtra").style.display        = esEspecialista ? "block" : "none";
    document.getElementById("contenedor_datos_medicos").style.display = esPaciente     ? "block" : "none";

    if (!esPaciente) {
        document.getElementById("regimen").value                               = "";
        document.getElementById("tipoEps").innerHTML                           = '<option value="">Seleccione primero el régimen</option>';
        document.getElementById("tipoEps").disabled                            = true;
        document.getElementById("eps").innerHTML                               = '<option value="">Seleccione primero el tipo de EPS</option>';
        document.getElementById("eps").disabled                                = true;
        document.getElementById("eps-otro-container-creacion").style.display  = 'none';
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

// ── PASO 1: VALIDACIÓN ─────────────────────────────────────────────────────────
function validarPaso1() {
    limpiarErrores();
    let valido = true;

    const nombres         = document.getElementById("nombres");
    const apellidos       = document.getElementById("apellidos");
    const fechaInput      = document.getElementById("fechaNacimiento");
    const rolUsuario      = document.getElementById("rolUsuario");
    const documento       = document.getElementById("documento");
    const telefono        = document.getElementById("telefono");
    const fechaISO        = leerFechaISO();

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
    if (!fechaISO) {
        fechaInput.classList.add("invalid");
        document.getElementById("errorFecha").innerText = "Ingrese su fecha de nacimiento.";
        valido = false;
    } else {
        const fechaObj = new Date(fechaISO);
        if (isNaN(fechaObj.getTime())) {
            fechaInput.classList.add("invalid");
            document.getElementById("errorFecha").innerText = "Fecha inválida. Use el formato DD/MM/AAAA.";
            valido = false;
        }
    }
    if (!rolUsuario.value) {
        rolUsuario.classList.add("invalid");
        document.getElementById("errorRol").innerText = "Seleccione un rol.";
        valido = false;
    }

    const rolVal     = rolUsuario.value;
    const esPaciente = (rolVal === "3" || rolVal === "Paciente");

    if (esPaciente) {
        const regimenEl = document.getElementById("regimen");
        if (!regimenEl.value) {
            regimenEl.classList.add("invalid");
            document.getElementById("errorRegimen").innerText = "Seleccione un régimen.";
            valido = false;
        }
        const tipoEpsEl = document.getElementById("tipoEps");
        if (!tipoEpsEl.value) {
            tipoEpsEl.classList.add("invalid");
            document.getElementById("errorTipoEps").innerText = "Seleccione el tipo de EPS.";
            valido = false;
        }
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
                document.getElementById('err-eps-otro-nombre-creacion').innerText = 'Ingrese el nombre de la nueva EPS.';
                valido = false;
            }
            if (!telefonoOtro.value.trim()) {
                telefonoOtro.classList.add('invalid');
                document.getElementById('err-eps-otro-telefono-creacion').innerText = 'Ingrese el teléfono de la nueva EPS.';
                valido = false;
            }
        }
    }

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

    correoVerificacion          = correoUsado.trim().toLowerCase();
    const nombreMostrar         = document.getElementById("nombres").value;
    const btnContinuar          = document.querySelector("#step1 button");
    btnContinuar.disabled       = true;
    btnContinuar.innerHTML      = "Enviando código...";

    fetch("/api/enviar-codigo", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ correo: correoVerificacion, nombre: nombreMostrar })
    })
    .then(r => r.json())
    .then(data => {
        btnContinuar.disabled  = false;
        btnContinuar.innerHTML = "Continuar &#8594;";
        if (data.ok) {
            document.getElementById("emailDestino").innerText       = correoVerificacion;
            document.getElementById("nombreDestinatario").innerText = nombreMostrar;
            document.getElementById("step1").classList.remove("active");
            document.getElementById("step2").classList.add("active");
            actualizarIndicador(2);
        } else {
            mostrarError("Error al enviar el código: " + (data.error || "Intenta de nuevo."));
        }
    })
    .catch(() => {
        btnContinuar.disabled  = false;
        btnContinuar.innerHTML = "Continuar &#8594;";
        mostrarError("No se pudo conectar con el servidor. Verifica tu conexión.");
    });
}

// ── PASO 2: VERIFICAR CÓDIGO ───────────────────────────────────────────────────
function verificarCodigo() {
    const ingresado   = document.getElementById("codigo").value.trim();
    const errorCodigo = document.getElementById("errorCodigo");

    if (!ingresado) {
        errorCodigo.innerText = "Ingresa el código.";
        return;
    }

    const btnVerificar     = document.querySelector("#step2 button");
    btnVerificar.disabled  = true;
    btnVerificar.innerHTML = "Verificando...";

    fetch("/api/verificar-codigo", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ correo: correoVerificacion, codigo: ingresado })
    })
    .then(r => r.json())
    .then(data => {
        btnVerificar.disabled  = false;
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
        btnVerificar.disabled  = false;
        btnVerificar.innerHTML = "Verificar código ✓";
        document.getElementById("errorCodigo").innerText = "Error de conexión. Intenta de nuevo.";
    });
}

// ── REGISTRO DE PACIENTE ───────────────────────────────────────────────────────
async function registrarPacienteEnBackend(usuarioId) {
    const payload = {
        ID_Usuario:       usuarioId,
        Fecha_Nacimiento: leerFechaISO() || null,
        Genero:           null,
        Grupo_Sanguineo:  document.getElementById("grupoSanguineo")?.value       || null,
        Alergias:         document.getElementById("alergias")?.value.trim()      || null,
        Antecedentes:     document.getElementById("antecedentes")?.value.trim()  || null,
        Observaciones:    document.getElementById("observaciones")?.value.trim() || null,
    };
    try {
        const res  = await fetch('/api/paciente', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.ok) return { ok: false, pacienteId: null, error: data.error };
        return { ok: true, pacienteId: data.data.ID_Paciente, error: null };
    } catch (err) {
        return { ok: false, pacienteId: null, error: err.message };
    }
}

// ── REGISTRO DE AFILIACIÓN ─────────────────────────────────────────────────────
async function registrarAfiliacionEnBackend(usuarioId, epsId, tipoEpsId) {
    const payload = {
        ID_Usuario:       usuarioId,
        ID_EPS:           epsId,
        ID_Tipo_EPS:      tipoEpsId,
        Fecha_Afiliacion: new Date().toISOString().split('T')[0],
    };
    try {
        const res  = await fetch('/api/afiliacion', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.ok) return { ok: false, afiliacionId: null, error: data.error };
        return { ok: true, afiliacionId: data.data.ID_Afiliacion, error: null };
    } catch (err) {
        return { ok: false, afiliacionId: null, error: err.message };
    }
}

// ── CREAR EPS NUEVA ────────────────────────────────────────────────────────────
async function crearNuevaEPS(nombre, telefono, tipoEpsId) {
    try {
        const res  = await fetch('/api/eps', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Nombre_EPS: nombre, ID_Tipo_EPS: tipoEpsId, Telefono: telefono })
        });
        const data = await res.json();
        if (!data.ok) { console.error('Error al crear EPS:', data.error); return null; }
        return data.data.ID_EPS;
    } catch (err) {
        console.error('[crearNuevaEPS]', err);
        return null;
    }
}

// ── PASO 3: CREAR USUARIO ──────────────────────────────────────────────────────
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

    const correoRegistro = (
        document.getElementById("correoUsuarioGroup").style.display === "none"
            ? document.getElementById("emailAcudiente").value
            : document.getElementById("email").value
    ).trim().toLowerCase();

    const rolSelect  = document.getElementById("rolUsuario");
    const rolValor   = rolSelect.value;
    const rolTexto   = rolSelect.options[rolSelect.selectedIndex]?.text || "";

    let rolIdNumerico = parseInt(rolValor, 10);
    if (isNaN(rolIdNumerico)) {
        if (rolTexto === "Paciente")          rolIdNumerico = 3;
        else if (rolTexto === "Especialista") rolIdNumerico = 2;
        else                                  rolIdNumerico = 1;
    }

    const generoSelect = document.getElementById("genero");
    const generoId     = generoSelect ? parseInt(generoSelect.value, 10) || 1 : 1;

    const tipoDocTexto = document.getElementById("tipoDocumento").value;
    const mapaTipoDoc  = {
        "Cedula de ciudadania": 1,
        "Tarjeta de identidad": 2,
        "Permiso por protección temporal": 3
    };
    const tipoDocId = mapaTipoDoc[tipoDocTexto] || 1;

    const epsSelect = document.getElementById("eps");
    const tipoEpsId = parseInt(document.getElementById("tipoEps").value, 10)  || null;
    const regimenId = parseInt(document.getElementById("regimen").value, 10)   || null;
    let   epsId     = epsSelect.value === EPS_OTRO_VALUE
        ? null
        : (parseInt(epsSelect.value, 10) || null);

    if (epsSelect.value === EPS_OTRO_VALUE) {
        const nombreOtro   = document.getElementById('eps-otro-nombre-creacion').value.trim();
        const telefonoOtro = document.getElementById('eps-otro-telefono-creacion').value.trim();
        mostrarProgreso("Registrando nueva EPS...");
        const nuevoEpsId = await crearNuevaEPS(nombreOtro, telefonoOtro, tipoEpsId);
        if (!nuevoEpsId) {
            mostrarError("No se pudo registrar la nueva EPS. Intenta de nuevo.");
            return;
        }
        epsId = nuevoEpsId;
        await cargarTodasLasEPS();
    }

    const especialidadEl     = document.getElementById("especialidadMedica");
    const especialidadId     = especialidadEl?.value ? parseInt(especialidadEl.value, 10) : null;
    const tarjetaEl          = document.getElementById("tarjetaProfesional");
    const tarjetaProfesional = tarjetaEl ? tarjetaEl.value.trim() : "";

    const datosUsuarioBackend = {
        nombres:             document.getElementById("nombres").value.trim(),
        apellidos:           document.getElementById("apellidos").value.trim(),
        documento:           document.getElementById("documento").value.trim(),
        telefono:            document.getElementById("telefono").value.trim(),
        correo:              correoRegistro,
        contrasena:          password.value,
        fecha_nacimiento:    leerFechaISO(),
        genero_id:           generoId,
        tipo_documento_id:   tipoDocId,
        estado_id:           1,
        rol_id:              rolIdNumerico,
        eps_id:              epsId,
        tipo_eps_id:         tipoEpsId,
        regimen_id:          regimenId,
        tarjeta_profesional: tarjetaProfesional || null,
        especialidad_id:     especialidadId
    };

    const btnFinalizar = document.getElementById("btnFinalizar");
    if (btnFinalizar) { btnFinalizar.disabled = true; btnFinalizar.innerHTML = "Creando usuario..."; }

    try {
        const respuesta = await fetch('/api/usuarios', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(datosUsuarioBackend)
        });
        const resultado = await respuesta.json();

        if (btnFinalizar) { btnFinalizar.disabled = false; btnFinalizar.innerHTML = "Finalizar"; }

        if (!resultado.ok) {
            mostrarError("No se pudo crear el usuario: " +
                (resultado.error || "Error desconocido. Revisa los datos e intenta de nuevo."));
            return;
        }

        const usuarioId  = resultado.usuario_id;
        const esPaciente = (rolIdNumerico === 3 || rolTexto === "Paciente");

        if (esPaciente && usuarioId) {
            mostrarProgreso("Registrando datos del paciente...");
            const resPaciente = await registrarPacienteEnBackend(usuarioId);
            if (!resPaciente.ok) {
                mostrarError("Usuario creado, pero no se pudieron guardar los datos clínicos: " + resPaciente.error);
            }
            if (epsId && tipoEpsId) {
                mostrarProgreso("Registrando afiliación a EPS...");
                const resAfiliacion = await registrarAfiliacionEnBackend(usuarioId, epsId, tipoEpsId);
                if (!resAfiliacion.ok) {
                    mostrarError("Usuario creado, pero no se pudo registrar la afiliación: " + resAfiliacion.error);
                }
            }
        }

        document.getElementById("groupPassword").style.display = "none";
        document.getElementById("groupConfirm").style.display  = "none";
        if (btnFinalizar) btnFinalizar.style.display            = "none";
        mensajeFinal.innerText = "¡Usuario registrado correctamente!";
        document.getElementById("btnIrAlLogin").style.display  = "flex";

    } catch (errorRed) {
        if (btnFinalizar) { btnFinalizar.disabled = false; btnFinalizar.innerHTML = "Finalizar"; }
        mostrarError("Error de conexión con el servidor. (" + errorRed.message + ")");
    }
}

// ── UTILIDADES ─────────────────────────────────────────────────────────────────
function mostrarProgreso(texto) {
    const el = document.getElementById("mensajeFinal");
    if (el) el.innerText = texto;
}
function abrirLogin() {
    window.location.href = "/login.html";
}
function togglePassword(id) {
    const input = document.getElementById(id);
    if (input) input.type = input.type === "password" ? "text" : "password";
}