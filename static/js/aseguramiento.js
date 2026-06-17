// =============================================================================
// aseguramiento.js
// Lógica de validación + integración con el backend (módulo EPS / Flask)
// =============================================================================
 
// ---------------------------------------------------------------------------
// CONSTANTES DE API
// ---------------------------------------------------------------------------
const BASE_URL = '/api';
 
// ---------------------------------------------------------------------------
// HELPERS DE VALIDACIÓN
// ---------------------------------------------------------------------------
function mostrarError(el, p, msg) {
    el.classList.add('input-error');
    p.innerText = msg;
    p.style.display = 'block';
}
 
function ocultarError(el, p) {
    el.classList.remove('input-error');
    p.style.display = 'none';
}
 
// ---------------------------------------------------------------------------
// SESIÓN — lectura flexible del usuario logueado
// ---------------------------------------------------------------------------
function obtenerUsuarioIdDeSesion() {
    const sesion = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    return sesion.ID_Usuario || sesion.id_usuario || sesion.usuario_id || sesion.Usuario_ID || null;
}
 
// ---------------------------------------------------------------------------
// CARGA DINÁMICA DE SELECTORES AL INICIAR LA PÁGINA
// ---------------------------------------------------------------------------
let todasLasEPS = [];
const EPS_OTRO_VALUE = '__OTRO__';

async function cargarTiposEPS() {
    try {
        const res  = await fetch(`${BASE_URL}/tipo-eps`);
        const data = await res.json();
 
        if (!data.ok) throw new Error(data.error || 'Error al cargar tipos de EPS');
 
        const select = document.getElementById('tipo-eps-select');
        select.innerHTML = '<option value="" disabled selected>Seleccione el tipo de EPS</option>';
 
        data.data.forEach(tipo => {
            const opt = document.createElement('option');
            opt.value       = tipo.ID_Tipo_EPS;
            opt.textContent = tipo.Nombre_Tipo;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('[cargarTiposEPS]', err);
        mostrarMensajeGlobal('error', '⚠️ No se pudieron cargar los tipos de EPS. Recargue la página.');
    }
}
 
async function cargarTodasLasEPS() {
    try {
        const res  = await fetch(`${BASE_URL}/eps`);
        const data = await res.json();
 
        if (!data.ok) throw new Error(data.error || 'Error al cargar EPS');
 
        todasLasEPS = data.data;
        poblarSelectEPS(todasLasEPS);
    } catch (err) {
        console.error('[cargarTodasLasEPS]', err);
        mostrarMensajeGlobal('error', '⚠️ No se pudieron cargar las EPS. Recargue la página.');
    }
}
 
async function cargarRegimenes() {
    try {
        const res  = await fetch(`${BASE_URL}/regimen-eps`);
        const data = await res.json();
 
        if (!data.ok) throw new Error(data.error || 'Error al cargar regímenes');
 
        const select = document.getElementById('regimen-select');
        select.innerHTML = '<option value="" disabled selected>Seleccione el régimen</option>';
 
        data.data.forEach(regimen => {
            const opt = document.createElement('option');
            opt.value       = regimen.ID_Regimen_EPS;
            opt.textContent = regimen.Nombre_Regimen;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('[cargarRegimenes]', err);
        mostrarMensajeGlobal('error', '⚠️ No se pudieron cargar los regímenes. Recargue la página.');
    }
}
 
function poblarSelectEPS(lista) {
    const select = document.getElementById('eps-select');
    select.innerHTML = '<option value="" disabled selected>Seleccione la EPS</option>';
    lista.forEach(eps => {
        const opt = document.createElement('option');
        opt.value       = eps.ID_EPS;
        opt.textContent = eps.Nombre_EPS;
        select.appendChild(opt);
    });
    // Agregar opción "Otro" al final
    const optOtro = document.createElement('option');
    optOtro.value       = EPS_OTRO_VALUE;
    optOtro.textContent = 'Otro';
    select.appendChild(optOtro);
}

// Muestra u oculta el bloque de EPS personalizada al seleccionar "Otro"
function manejarSeleccionEPS() {
    const epsSelect = document.getElementById('eps-select');
    const otroContainer = document.getElementById('eps-otro-container');
    const errEps = document.getElementById('err-eps');

    ocultarError(epsSelect, errEps);

    if (epsSelect.value === EPS_OTRO_VALUE) {
        otroContainer.style.display = 'block';
    } else {
        otroContainer.style.display = 'none';
        // Limpiar campos de EPS personalizada
        document.getElementById('eps-otro-nombre').value = '';
        document.getElementById('eps-otro-telefono').value = '';
        ocultarError(document.getElementById('eps-otro-nombre'), document.getElementById('err-eps-otro-nombre'));
        ocultarError(document.getElementById('eps-otro-telefono'), document.getElementById('err-eps-otro-telefono'));
    }
}
 
// Filtrado reactivo: cuando el usuario cambia el tipo, recarga el select de EPS
function filtrarEPSporTipo() {
    const tipoId = document.getElementById('tipo-eps-select').value;
 
    ocultarError(
        document.getElementById('tipo-eps-select'),
        document.getElementById('err-tipo-eps')
    );
 
    if (!tipoId) {
        poblarSelectEPS(todasLasEPS);
        return;
    }
 
    const filtradas = todasLasEPS.filter(
        eps => String(eps.ID_Tipo_EPS) === String(tipoId)
    );
    poblarSelectEPS(filtradas);
 
    document.getElementById('eps-select').value = '';
    document.getElementById('eps-otro-container').style.display = 'none';

}

// ---------------------------------------------------------------------------
// AUTORIZACIÓN DE TRATAMIENTO DE DATOS (Habeas Data)
// Como el administrador es el único que tiene acceso a esta pantalla, la
// autorización se confirma con el simple hecho de marcar la casilla estilo
// reCAPTCHA. toggleAutorizacion() se dispara al hacer clic en la caja y
// alterna el checkbox real (oculto) junto con el estilo visual del recuadro.
// actualizarEstadoAutorizacion() sincroniza el recuadro visual con el estado
// del checkbox y oculta cualquier mensaje de error pendiente al marcarlo.
// ---------------------------------------------------------------------------
function toggleAutorizacion() {
    const checkbox = document.getElementById('terminos');
    checkbox.checked = !checkbox.checked;
    actualizarEstadoAutorizacion();
}

function actualizarEstadoAutorizacion() {
    const checkbox = document.getElementById('terminos');
    const caja = document.getElementById('recaptcha-box');
    const check = document.getElementById('recaptcha-check');
    const errTerminos = document.getElementById('err-terminos');

    if (caja) {
        caja.classList.toggle('checked', checkbox.checked);
        if (checkbox.checked) {
            caja.style.background = '#0ea5e9';
            caja.style.borderColor = '#0ea5e9';
        } else {
            caja.style.background = '#ffffff';
            caja.style.borderColor = '#9ca3af';
        }
    }

    if (check) {
        check.style.opacity = checkbox.checked ? '1' : '0';
        check.style.transform = checkbox.checked ? 'scale(1)' : 'scale(0.4)';
    }

    if (checkbox.checked && errTerminos) {
        errTerminos.style.display = 'none';
    }
    
}
 
// ---------------------------------------------------------------------------
// VALIDACIÓN COMPLETA DEL FORMULARIO
// ---------------------------------------------------------------------------
function validarFormulario() {
    const inputs = {
        nombre:   [document.getElementById('nombre'),         document.getElementById('err-nombre')],
        doc:      [document.getElementById('num-doc'),        document.getElementById('err-documento')],
        tel:      [document.getElementById('telefono'),       document.getElementById('err-telefono')],
        email:    [document.getElementById('correo'),         document.getElementById('err-correo')],
        tipo:     [document.getElementById('tipo-doc'),       document.getElementById('err-tipo-doc')],
        tipoEPS:  [document.getElementById('tipo-eps-select'), document.getElementById('err-tipo-eps')],
        eps:      [document.getElementById('eps-select'),      document.getElementById('err-eps')],
        regimen:  [document.getElementById('regimen-select'),  document.getElementById('err-regimen')]
    };
 
    let todoValido = true;
    const regexSoloNumeros = /^[0-9]+$/;
    const regexEmail       = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;
 
    // ── Nombre ────────────────────────────────────────────────────────────────
    if (inputs.nombre[0].value.trim() === '') {
        mostrarError(inputs.nombre[0], inputs.nombre[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (/\d/.test(inputs.nombre[0].value)) {
        mostrarError(inputs.nombre[0], inputs.nombre[1], '❌ Información incorrecta: Sin números.');
        todoValido = false;
    } else {
        ocultarError(inputs.nombre[0], inputs.nombre[1]);
    }
 
    // ── Documento (MAX 10) ────────────────────────────────────────────────────
    if (inputs.doc[0].value.trim() === '') {
        mostrarError(inputs.doc[0], inputs.doc[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexSoloNumeros.test(inputs.doc[0].value) || inputs.doc[0].value.length > 10) {
        mostrarError(inputs.doc[0], inputs.doc[1], '❌ Información incorrecta: Solo números (Máximo 10).');
        todoValido = false;
    } else {
        ocultarError(inputs.doc[0], inputs.doc[1]);
    }
 
    // ── Teléfono (EXACTO 10) ──────────────────────────────────────────────────
    if (inputs.tel[0].value.trim() === '') {
        mostrarError(inputs.tel[0], inputs.tel[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexSoloNumeros.test(inputs.tel[0].value) || inputs.tel[0].value.length !== 10) {
        mostrarError(inputs.tel[0], inputs.tel[1], '❌ Información incorrecta: Debe tener exactamente 10 números.');
        todoValido = false;
    } else {
        ocultarError(inputs.tel[0], inputs.tel[1]);
    }
 
    // ── Correo ────────────────────────────────────────────────────────────────
    if (inputs.email[0].value.trim() === '') {
        mostrarError(inputs.email[0], inputs.email[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexEmail.test(inputs.email[0].value)) {
        mostrarError(inputs.email[0], inputs.email[1], '❌ Información incorrecta: Formato de correo inválido.');
        todoValido = false;
    } else {
        ocultarError(inputs.email[0], inputs.email[1]);
    }
 
    // ── Tipo Documento ────────────────────────────────────────────────────────
    if (inputs.tipo[0].value === '') {
        mostrarError(inputs.tipo[0], inputs.tipo[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else {
        ocultarError(inputs.tipo[0], inputs.tipo[1]);
    }
 
    // ── Tipo EPS ──────────────────────────────────────────────────────────────
    if (!inputs.tipoEPS[0].value) {
        mostrarError(inputs.tipoEPS[0], inputs.tipoEPS[1], '⚠️ Seleccione el tipo de EPS.');
        todoValido = false;
    } else {
        ocultarError(inputs.tipoEPS[0], inputs.tipoEPS[1]);
    }
 
    // ── EPS ───────────────────────────────────────────────────────────────────
    if (!inputs.eps[0].value) {
        mostrarError(inputs.eps[0], inputs.eps[1], '⚠️ Seleccione la EPS.');
        todoValido = false;
    } else {
        ocultarError(inputs.eps[0], inputs.eps[1]);

        // Validar campos adicionales si se eligió "Otro"
        if (inputs.eps[0].value === EPS_OTRO_VALUE) {
            const nombreOtro   = document.getElementById('eps-otro-nombre');
            const telefonoOtro = document.getElementById('eps-otro-telefono');
            const errNombre    = document.getElementById('err-eps-otro-nombre');
            const errTelefono  = document.getElementById('err-eps-otro-telefono');

            if (nombreOtro.value.trim() === '') {
                mostrarError(nombreOtro, errNombre, '⚠️ Ingrese el nombre de la nueva EPS.');
                todoValido = false;
            } else {
                ocultarError(nombreOtro, errNombre);
            }

            if (telefonoOtro.value.trim() === '') {
                mostrarError(telefonoOtro, errTelefono, '⚠️ Ingrese el teléfono de la nueva EPS.');
                todoValido = false;
            } else {
                ocultarError(telefonoOtro, errTelefono);
            }
        }
    }
 
    // ── Régimen ───────────────────────────────────────────────────────────────
    if (!inputs.regimen[0].value) {
        mostrarError(inputs.regimen[0], inputs.regimen[1], '⚠️ Seleccione el régimen.');
        todoValido = false;
    } else {
        ocultarError(inputs.regimen[0], inputs.regimen[1]);
    }
 
    // ── Términos y condiciones ────────────────────────────────────────────────
    if (!document.getElementById('terminos').checked) {
        mostrarMensajeGlobal('error', '⚠️ Debe aceptar el tratamiento de datos.');
        todoValido = false;

        const errTerminos = document.getElementById('err-terminos');
        if (errTerminos) {
            errTerminos.innerText = '⚠️ Debe marcar la casilla para autorizar el tratamiento de los datos.';
            errTerminos.style.display = 'block';
        }
    } else {
        const errTerminos = document.getElementById('err-terminos');
        if (errTerminos) errTerminos.style.display = 'none';
    }
 
    return todoValido;
}
 
// ---------------------------------------------------------------------------
// LEER VALORES DEL FORMULARIO
// ---------------------------------------------------------------------------
function leerFormulario() {
    const epsSelect = document.getElementById('eps-select');
    const esEpsOtro = epsSelect.value === EPS_OTRO_VALUE;

    return {
        nombre:         document.getElementById('nombre').value.trim(),
        tipoDoc:        document.getElementById('tipo-doc').value,
        numDoc:         document.getElementById('num-doc').value.trim(),
        telefono:       document.getElementById('telefono').value.trim(),
        correo:         document.getElementById('correo').value.trim(),
        epsId:          esEpsOtro ? null : Number(epsSelect.value),
        esEpsOtro:      esEpsOtro,
        epsOtroNombre:  esEpsOtro ? document.getElementById('eps-otro-nombre').value.trim() : null,
        epsOtroTelefono: esEpsOtro ? document.getElementById('eps-otro-telefono').value.trim() : null,
        tipoEpsId:      Number(document.getElementById('tipo-eps-select').value),
        regimenId:      Number(document.getElementById('regimen-select').value),
    };
}
 
// ---------------------------------------------------------------------------
// BLOQUEO / DESBLOQUEO DE BOTONES DURANTE LA PETICIÓN
// ---------------------------------------------------------------------------
function setBotonesEstado(cargando) {
    const btns = document.querySelectorAll('.btn-accion');
    btns.forEach(btn => {
        btn.disabled = cargando;
        btn.classList.toggle('opacity-60', cargando);
        btn.classList.toggle('cursor-not-allowed', cargando);
    });
}
 
// ---------------------------------------------------------------------------
// MENSAJE GLOBAL DE ÉXITO / ERROR
// ---------------------------------------------------------------------------
function mostrarMensajeGlobal(tipo, texto) {
    const el = document.getElementById('mensaje-global');
    if (!el) return;
 
    el.className = tipo === 'exito' ? 'exito' : 'error';
    el.textContent = texto;
    el.style.display = 'block';
 
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}

// ---------------------------------------------------------------------------
// CREAR NUEVA EPS EN LA BASE DE DATOS
// El backend (routes.py → nueva_eps) requiere: Nombre_EPS e ID_Tipo_EPS.
// Telefono y Direccion son opcionales en el routes.py.
// ID_Tipo_EPS se toma del selector de Tipo EPS que el administrador ya eligió.
// Retorna el ID de la EPS recién creada, o null si falla.
// ---------------------------------------------------------------------------
async function crearNuevaEPS(nombre, telefono, tipoEpsId) {
    try {
        const res = await fetch(`${BASE_URL}/eps`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                Nombre_EPS:  nombre,
                ID_Tipo_EPS: tipoEpsId,   // requerido por routes.py
                Telefono:    telefono      // opcional en routes.py
            })
        });
        const data = await res.json();

        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Error al crear la nueva EPS: ${data.error}`);
            return null;
        }
        return data.data.ID_EPS;
    } catch (err) {
        console.error('[crearNuevaEPS]', err);
        mostrarMensajeGlobal('error', '❌ No se pudo conectar con el servidor para crear la EPS.');
        return null;
    }
}
 
// ---------------------------------------------------------------------------
// ACCIÓN: ASEGURAR DATOS
// ---------------------------------------------------------------------------
async function asegurarDatos(form) {
    const usuarioId = obtenerUsuarioIdDeSesion();
 
    if (!usuarioId) {
        mostrarMensajeGlobal('error', '❌ No hay sesión activa. Por favor inicie sesión antes de asegurar datos.');
        return;
    }

    // Si se eligió "Otro", crear la nueva EPS primero
    let epsIdFinal = form.epsId;
    if (form.esEpsOtro) {
        // Pasamos tipoEpsId porque routes.py requiere ID_Tipo_EPS (no Regimen_ID)
        epsIdFinal = await crearNuevaEPS(form.epsOtroNombre, form.epsOtroTelefono, form.tipoEpsId);
        if (!epsIdFinal) return;
        await cargarTodasLasEPS();
    }
 
    // ── Paso 1: Crear paciente ────────────────────────────────────────────────
    const bodyPaciente = {
        ID_Usuario: usuarioId,
    };
 
    let pacienteId;
    try {
        const resPaciente = await fetch(`${BASE_URL}/paciente`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(bodyPaciente)
        });
        const dataPaciente = await resPaciente.json();
 
        if (!dataPaciente.ok) {
            mostrarMensajeGlobal('error', `❌ Error al registrar paciente: ${dataPaciente.error}`);
            return;
        }
        pacienteId = dataPaciente.data.ID_Paciente;
    } catch (err) {
        console.error('[asegurarDatos/paciente]', err);
        mostrarMensajeGlobal('error', '❌ No se pudo conectar con el servidor al registrar el paciente.');
        return;
    }
 
    // ── Paso 2: Crear afiliación ──────────────────────────────────────────────
    const bodyAfiliacion = {
        ID_Usuario:       usuarioId,
        ID_EPS:           epsIdFinal,
        ID_Regimen_EPS:   form.regimenId,
        Fecha_Afiliacion: new Date().toISOString().split('T')[0],
        Estado:           'Activo'
    };
 
    try {
        const resAfiliacion = await fetch(`${BASE_URL}/afiliacion`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(bodyAfiliacion)
        });
        const dataAfiliacion = await resAfiliacion.json();
 
        if (!dataAfiliacion.ok) {
            mostrarMensajeGlobal('error', `❌ Paciente registrado (ID: ${pacienteId}) pero hubo un error en la afiliación: ${dataAfiliacion.error}`);
            return;
        }
 
        const sesion = JSON.parse(sessionStorage.getItem('usuario') || '{}');
        sesion.id_paciente   = pacienteId;
        sesion.id_afiliacion = dataAfiliacion.data.ID_Afiliacion;
        sessionStorage.setItem('usuario', JSON.stringify(sesion));
 
        mostrarMensajeGlobal('exito', `✅ Datos asegurados correctamente. Paciente #${pacienteId} afiliado a la EPS seleccionada.`);
    } catch (err) {
        console.error('[asegurarDatos/afiliacion]', err);
        mostrarMensajeGlobal('error', `❌ Paciente registrado (ID: ${pacienteId}) pero no se pudo conectar al servidor para la afiliación.`);
    }
}
 
// ---------------------------------------------------------------------------
// ACCIÓN: ACTUALIZAR DATOS
// ---------------------------------------------------------------------------
async function actualizarDatos(form) {
    const sesion       = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    const pacienteId   = sesion.id_paciente   || null;
    const afiliacionId = sesion.id_afiliacion || null;
 
    if (!pacienteId) {
        mostrarMensajeGlobal('error', '❌ No se encontró el ID del paciente en la sesión. Use primero "Asegurar Datos".');
        return;
    }

    // Si se eligió "Otro", crear la nueva EPS primero
    let epsIdFinal = form.epsId;
    if (form.esEpsOtro) {
        epsIdFinal = await crearNuevaEPS(form.epsOtroNombre, form.epsOtroTelefono, form.tipoEpsId);
        if (!epsIdFinal) return;
        await cargarTodasLasEPS();
    }
 
    // ── Actualizar paciente ───────────────────────────────────────────────────
    const bodyPaciente = {};
 
    try {
        const res  = await fetch(`${BASE_URL}/paciente/${pacienteId}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(bodyPaciente)
        });
        const data = await res.json();
 
        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Error al actualizar paciente: ${data.error}`);
            return;
        }
    } catch (err) {
        console.error('[actualizarDatos/paciente]', err);
        mostrarMensajeGlobal('error', '❌ No se pudo conectar con el servidor al actualizar el paciente.');
        return;
    }
 
    // ── Actualizar afiliación si tenemos el ID ────────────────────────────────
    if (afiliacionId) {
        const bodyAfiliacion = {
            ID_EPS:           epsIdFinal,
            ID_Regimen_EPS:   form.regimenId,
            Fecha_Afiliacion: new Date().toISOString().split('T')[0],
            Estado:           'Activo'
        };
 
        try {
            const res  = await fetch(`${BASE_URL}/afiliacion/${afiliacionId}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(bodyAfiliacion)
            });
            const data = await res.json();
 
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Paciente actualizado pero hubo un error en la afiliación: ${data.error}`);
                return;
            }
        } catch (err) {
            console.error('[actualizarDatos/afiliacion]', err);
            mostrarMensajeGlobal('error', '❌ Paciente actualizado pero no se pudo conectar al servidor para la afiliación.');
            return;
        }
    }
 
    mostrarMensajeGlobal('exito', '🔄 Información actualizada correctamente.');
}
 
// ---------------------------------------------------------------------------
// PUNTO DE ENTRADA PRINCIPAL
// ---------------------------------------------------------------------------
async function validarYProcesar(accion) {
    // --- NUEVA VALIDACIÓN ESTRICTA HABEAS DATA ---
    const checkboxTerminos = document.getElementById('terminos');
    const mensajeGlobal = document.getElementById('mensaje-global');
    
    if (!checkboxTerminos.checked) {
        mensajeGlobal.className = 'error';
        mensajeGlobal.style.display = 'block';
        mensajeGlobal.textContent = `⚠️ Para ${accion} la información clínica, es estrictamente obligatorio aceptar los términos de Habeas Data y el tratamiento de datos.`;
        setTimeout(() => { mensajeGlobal.style.display = 'none'; }, 6000);
        return; // Bloquea la ejecución inmediatamente
    }
    // ---------------------------------------------


    const esValido = validarFormulario();
    if (!esValido) return;
 
    const form = leerFormulario();
 
    setBotonesEstado(true);
 
    try {
        if (accion === 'asegurar') {
            await asegurarDatos(form);
        } else {
            await actualizarDatos(form);
        }
    } finally {
        setBotonesEstado(false);
    }
}
 
// ---------------------------------------------------------------------------
// INICIALIZACIÓN AL CARGAR LA PÁGINA
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        cargarTiposEPS(),
        cargarTodasLasEPS(),
        cargarRegimenes()
    ]);
 
    document.getElementById('tipo-eps-select')
            .addEventListener('change', filtrarEPSporTipo);

    document.getElementById('eps-select')
            .addEventListener('change', manejarSeleccionEPS);
});