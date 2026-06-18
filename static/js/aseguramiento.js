"use strict";

// =============================================================================
// CONSTANTES
// =============================================================================
const BASE_URL       = '/api';
const EPS_OTRO_VALUE = '__OTRO__';

let todasLasEPS    = [];
let todosTiposEps  = [];
let epsFiltradas   = [];

// =============================================================================
// HELPERS DE VALIDACIÓN
// =============================================================================
function mostrarErrorCampo(el, p, msg) {
    el.classList.add('input-error');
    p.innerText = msg;
    p.style.display = 'block';
}

function ocultarErrorCampo(el, p) {
    el.classList.remove('input-error');
    p.innerText = '';
    p.style.display = 'none';
}

// =============================================================================
// SESIÓN
// =============================================================================
function obtenerUsuarioIdDeSesion() {
    const sesion = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    return sesion.ID_Usuario || sesion.id_usuario || sesion.usuario_id || sesion.Usuario_ID || null;
}

// =============================================================================
// CARGA DE CATÁLOGOS
// =============================================================================
async function cargarRegimenes() {
    const select   = document.getElementById('regimen-select');
    const fallback = [
        { Regimen_ID: 1, Descripcion: 'Contributivo' },
        { Regimen_ID: 2, Descripcion: 'Subsidiado' }
    ];

    const poblar = (lista) => {
        select.innerHTML = '<option value="" disabled selected>Seleccione el régimen...</option>';
        lista.forEach(r => {
            const opt = document.createElement('option');
            opt.value       = r.Regimen_ID || r.ID_Regimen_EPS;
            opt.textContent = r.Descripcion || r.Nombre_Regimen;
            select.appendChild(opt);
        });
    };

    try {
        const res  = await fetch(`${BASE_URL}/regimen-eps`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        poblar(data.data);
    } catch (err) {
        console.warn('[cargarRegimenes] fallback:', err);
        poblar(fallback);
    }
}

async function cargarTiposEPS() {
    const fallback = [
        { TipoEPS_ID: 1, Nombre_Tipo: 'Cotizante' },
        { TipoEPS_ID: 2, Nombre_Tipo: 'Beneficiario' }
    ];
    try {
        const res  = await fetch(`${BASE_URL}/tipo-eps`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        todosTiposEps = data.data;
    } catch (err) {
        console.warn('[cargarTiposEPS] fallback:', err);
        todosTiposEps = fallback;
    }
}

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
        const res  = await fetch(`${BASE_URL}/eps`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        todasLasEPS = data.data;
    } catch (err) {
        console.warn('[cargarTodasLasEPS] fallback:', err);
        todasLasEPS = fallback;
    }
}

// =============================================================================
// CASCADING DROPDOWNS: RÉGIMEN → TIPO EPS → EPS
// =============================================================================
function onRegimenChangeAseg() {
    const regimenId  = document.getElementById('regimen-select').value;
    const selectTipo = document.getElementById('tipo-eps-select');
    const selectEps  = document.getElementById('eps-select');
    const errReg     = document.getElementById('err-regimen');

    ocultarErrorCampo(document.getElementById('regimen-select'), errReg);

    // Reset dependientes
    selectTipo.innerHTML = '<option value="" disabled selected>Seleccione el tipo de EPS...</option>';
    selectEps.innerHTML  = '<option value="" disabled selected>Seleccione primero el tipo de EPS</option>';
    selectTipo.disabled  = true;
    selectEps.disabled   = true;
    document.getElementById('eps-otro-container').style.display = 'none';

    if (!regimenId) return;

    // Poblar Tipo de EPS
    todosTiposEps.forEach(t => {
        const opt = document.createElement('option');
        opt.value       = t.TipoEPS_ID || t.ID_Tipo_EPS;
        opt.textContent = t.Nombre_Tipo;
        selectTipo.appendChild(opt);
    });
    selectTipo.disabled = false;

    // Pre-filtrar EPS por régimen
    epsFiltradas = todasLasEPS.filter(e => String(e.Regimen_ID) === String(regimenId));
}

function onTipoEpsChangeAseg() {
    const selectEps  = document.getElementById('eps-select');
    const selectTipo = document.getElementById('tipo-eps-select');
    const errTipo    = document.getElementById('err-tipo-eps');

    ocultarErrorCampo(selectTipo, errTipo);

    selectEps.innerHTML = '<option value="" disabled selected>Seleccione la EPS...</option>';
    selectEps.disabled  = true;
    document.getElementById('eps-otro-container').style.display = 'none';

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

function manejarSeleccionEPS() {
    const epsSelect     = document.getElementById('eps-select');
    const otroContainer = document.getElementById('eps-otro-container');
    const errEps        = document.getElementById('err-eps');

    ocultarErrorCampo(epsSelect, errEps);

    if (epsSelect.value === EPS_OTRO_VALUE) {
        otroContainer.style.display = 'block';
    } else {
        otroContainer.style.display = 'none';
        document.getElementById('eps-otro-nombre').value   = '';
        document.getElementById('eps-otro-telefono').value = '';
        ocultarErrorCampo(document.getElementById('eps-otro-nombre'),   document.getElementById('err-eps-otro-nombre'));
        ocultarErrorCampo(document.getElementById('eps-otro-telefono'), document.getElementById('err-eps-otro-telefono'));
    }
}

// =============================================================================
// AUTORIZACIÓN HABEAS DATA
// =============================================================================
function toggleAutorizacion() {
    const checkbox = document.getElementById('terminos');
    checkbox.checked = !checkbox.checked;
    actualizarEstadoAutorizacion();
}

function actualizarEstadoAutorizacion() {
    const checkbox    = document.getElementById('terminos');
    const caja        = document.getElementById('recaptcha-box');
    const check       = document.getElementById('recaptcha-check');
    const errTerminos = document.getElementById('err-terminos');

    if (caja) {
        caja.classList.toggle('checked', checkbox.checked);
        caja.style.background   = checkbox.checked ? '#0ea5e9' : '#ffffff';
        caja.style.borderColor  = checkbox.checked ? '#0ea5e9' : '#9ca3af';
    }
    if (check) {
        check.style.opacity   = checkbox.checked ? '1' : '0';
        check.style.transform = checkbox.checked ? 'scale(1)' : 'scale(0.4)';
    }
    if (checkbox.checked && errTerminos) errTerminos.style.display = 'none';
}

// =============================================================================
// VALIDACIÓN DEL FORMULARIO
// =============================================================================
function validarFormulario() {
    const nombre    = document.getElementById('nombre');
    const numDoc    = document.getElementById('num-doc');
    const telefono  = document.getElementById('telefono');
    const correo    = document.getElementById('correo');
    const tipoDoc   = document.getElementById('tipo-doc');
    const regimen   = document.getElementById('regimen-select');
    const tipoEps   = document.getElementById('tipo-eps-select');
    const epsSelect = document.getElementById('eps-select');

    const errNombre   = document.getElementById('err-nombre');
    const errDoc      = document.getElementById('err-documento');
    const errTel      = document.getElementById('err-telefono');
    const errCorreo   = document.getElementById('err-correo');
    const errTipoDoc  = document.getElementById('err-tipo-doc');
    const errRegimen  = document.getElementById('err-regimen');
    const errTipoEps  = document.getElementById('err-tipo-eps');
    const errEps      = document.getElementById('err-eps');

    let todoValido = true;
    const regexNumeros = /^[0-9]+$/;
    const regexEmail   = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

    // Nombre
    if (!nombre.value.trim()) {
        mostrarErrorCampo(nombre, errNombre, '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (/\d/.test(nombre.value)) {
        mostrarErrorCampo(nombre, errNombre, '❌ Sin números en el nombre.');
        todoValido = false;
    } else {
        ocultarErrorCampo(nombre, errNombre);
    }

    // Documento
    if (!numDoc.value.trim()) {
        mostrarErrorCampo(numDoc, errDoc, '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexNumeros.test(numDoc.value) || numDoc.value.length > 10) {
        mostrarErrorCampo(numDoc, errDoc, '❌ Solo números (máximo 10).');
        todoValido = false;
    } else {
        ocultarErrorCampo(numDoc, errDoc);
    }

    // Teléfono
    if (!telefono.value.trim()) {
        mostrarErrorCampo(telefono, errTel, '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexNumeros.test(telefono.value) || telefono.value.length !== 10) {
        mostrarErrorCampo(telefono, errTel, '❌ Debe tener exactamente 10 dígitos.');
        todoValido = false;
    } else {
        ocultarErrorCampo(telefono, errTel);
    }

    // Correo
    if (!correo.value.trim()) {
        mostrarErrorCampo(correo, errCorreo, '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else if (!regexEmail.test(correo.value)) {
        mostrarErrorCampo(correo, errCorreo, '❌ Formato de correo inválido.');
        todoValido = false;
    } else {
        ocultarErrorCampo(correo, errCorreo);
    }

    // Tipo de documento
    if (!tipoDoc.value) {
        mostrarErrorCampo(tipoDoc, errTipoDoc, '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else {
        ocultarErrorCampo(tipoDoc, errTipoDoc);
    }

    // Régimen
    if (!regimen.value) {
        mostrarErrorCampo(regimen, errRegimen, '⚠️ Seleccione el régimen.');
        todoValido = false;
    } else {
        ocultarErrorCampo(regimen, errRegimen);
    }

    // Tipo EPS
    if (!tipoEps.value) {
        mostrarErrorCampo(tipoEps, errTipoEps, '⚠️ Seleccione el tipo de EPS.');
        todoValido = false;
    } else {
        ocultarErrorCampo(tipoEps, errTipoEps);
    }

    // EPS
    if (!epsSelect.value) {
        mostrarErrorCampo(epsSelect, errEps, '⚠️ Seleccione la EPS.');
        todoValido = false;
    } else {
        ocultarErrorCampo(epsSelect, errEps);

        if (epsSelect.value === EPS_OTRO_VALUE) {
            const nombreOtro   = document.getElementById('eps-otro-nombre');
            const telefonoOtro = document.getElementById('eps-otro-telefono');
            const errNombreO   = document.getElementById('err-eps-otro-nombre');
            const errTelO      = document.getElementById('err-eps-otro-telefono');

            if (!nombreOtro.value.trim()) {
                mostrarErrorCampo(nombreOtro, errNombreO, '⚠️ Ingrese el nombre de la nueva EPS.');
                todoValido = false;
            } else {
                ocultarErrorCampo(nombreOtro, errNombreO);
            }
            if (!telefonoOtro.value.trim()) {
                mostrarErrorCampo(telefonoOtro, errTelO, '⚠️ Ingrese el teléfono de la nueva EPS.');
                todoValido = false;
            } else {
                ocultarErrorCampo(telefonoOtro, errTelO);
            }
        }
    }

    // Términos
    if (!document.getElementById('terminos').checked) {
        const errTerminos = document.getElementById('err-terminos');
        if (errTerminos) {
            errTerminos.innerText      = '⚠️ Debe marcar la casilla para autorizar el tratamiento de los datos.';
            errTerminos.style.display  = 'block';
        }
        todoValido = false;
    }

    return todoValido;
}

// =============================================================================
// LEER FORMULARIO
// =============================================================================
function leerFormulario() {
    const epsSelect = document.getElementById('eps-select');
    const esEpsOtro = epsSelect.value === EPS_OTRO_VALUE;
    const tipoEpsEl = document.getElementById('tipo-eps-select');

    return {
        nombre:          document.getElementById('nombre').value.trim(),
        tipoDoc:         document.getElementById('tipo-doc').value,
        numDoc:          document.getElementById('num-doc').value.trim(),
        telefono:        document.getElementById('telefono').value.trim(),
        correo:          document.getElementById('correo').value.trim(),
        regimenId:       Number(document.getElementById('regimen-select').value),
        tipoEpsId:       Number(tipoEpsEl.value),
        epsId:           esEpsOtro ? null : Number(epsSelect.value),
        esEpsOtro,
        epsOtroNombre:   esEpsOtro ? document.getElementById('eps-otro-nombre').value.trim()   : null,
        epsOtroTelefono: esEpsOtro ? document.getElementById('eps-otro-telefono').value.trim() : null,
    };
}

// =============================================================================
// ESTADO DE BOTONES
// =============================================================================
function setBotonesEstado(cargando) {
    document.querySelectorAll('.btn-accion').forEach(btn => {
        btn.disabled = cargando;
    });
}

// =============================================================================
// MENSAJES GLOBALES
// =============================================================================
function mostrarMensajeGlobal(tipo, texto) {
    const el = document.getElementById('mensaje-global');
    if (!el) return;
    el.className        = tipo === 'exito' ? 'exito' : 'error';
    el.textContent      = texto;
    el.style.display    = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}

// =============================================================================
// CREAR EPS NUEVA
// =============================================================================
async function crearNuevaEPS(nombre, telefono, tipoEpsId) {
    try {
        const res  = await fetch(`${BASE_URL}/eps`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Nombre_EPS: nombre, ID_Tipo_EPS: tipoEpsId, Telefono: telefono })
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

// =============================================================================
// ACCIÓN: ASEGURAR DATOS
// =============================================================================
async function asegurarDatos(form) {
    const usuarioId = obtenerUsuarioIdDeSesion();
    if (!usuarioId) {
        mostrarMensajeGlobal('error', '❌ No hay sesión activa. Por favor inicie sesión.');
        return;
    }

    let epsIdFinal = form.epsId;
    if (form.esEpsOtro) {
        epsIdFinal = await crearNuevaEPS(form.epsOtroNombre, form.epsOtroTelefono, form.tipoEpsId);
        if (!epsIdFinal) return;
        await cargarTodasLasEPS();
    }

    // Registrar paciente
    let pacienteId;
    try {
        const res  = await fetch(`${BASE_URL}/paciente`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ ID_Usuario: usuarioId })
        });
        const data = await res.json();
        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Error al registrar paciente: ${data.error}`);
            return;
        }
        pacienteId = data.data.ID_Paciente;
    } catch (err) {
        mostrarMensajeGlobal('error', '❌ No se pudo conectar al registrar el paciente.');
        return;
    }

    // Registrar afiliación — usa TipoEPS_ID (Cotizante/Beneficiario)
    try {
        const res  = await fetch(`${BASE_URL}/afiliacion`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                ID_Usuario:       usuarioId,
                ID_EPS:           epsIdFinal,
                ID_Tipo_EPS:      form.tipoEpsId,
                Fecha_Afiliacion: new Date().toISOString().split('T')[0],
            })
        });
        const data = await res.json();
        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Paciente registrado (ID: ${pacienteId}) pero error en afiliación: ${data.error}`);
            return;
        }

        const sesion = JSON.parse(sessionStorage.getItem('usuario') || '{}');
        sesion.id_paciente   = pacienteId;
        sesion.id_afiliacion = data.data.ID_Afiliacion;
        sessionStorage.setItem('usuario', JSON.stringify(sesion));

        mostrarMensajeGlobal('exito', `✅ Datos asegurados correctamente. Paciente #${pacienteId} afiliado.`);
    } catch (err) {
        mostrarMensajeGlobal('error', `❌ Paciente registrado (ID: ${pacienteId}) pero no se pudo registrar la afiliación.`);
    }
}

// =============================================================================
// ACCIÓN: ACTUALIZAR DATOS
// =============================================================================
async function actualizarDatos(form) {
    const sesion       = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    const pacienteId   = sesion.id_paciente   || null;
    const afiliacionId = sesion.id_afiliacion || null;

    if (!pacienteId) {
        mostrarMensajeGlobal('error', '❌ No se encontró el ID del paciente. Use primero "Asegurar Datos".');
        return;
    }

    let epsIdFinal = form.epsId;
    if (form.esEpsOtro) {
        epsIdFinal = await crearNuevaEPS(form.epsOtroNombre, form.epsOtroTelefono, form.tipoEpsId);
        if (!epsIdFinal) return;
        await cargarTodasLasEPS();
    }

    // Actualizar paciente
    try {
        const res  = await fetch(`${BASE_URL}/paciente/${pacienteId}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({})
        });
        const data = await res.json();
        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Error al actualizar paciente: ${data.error}`);
            return;
        }
    } catch (err) {
        mostrarMensajeGlobal('error', '❌ No se pudo conectar al actualizar el paciente.');
        return;
    }

    // Actualizar afiliación
    if (afiliacionId) {
        try {
            const res  = await fetch(`${BASE_URL}/afiliacion/${afiliacionId}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    ID_EPS:           epsIdFinal,
                    ID_Tipo_EPS:      form.tipoEpsId,
                    Fecha_Afiliacion: new Date().toISOString().split('T')[0],
                })
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Paciente actualizado pero error en afiliación: ${data.error}`);
                return;
            }
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ Paciente actualizado pero no se pudo actualizar la afiliación.');
            return;
        }
    }

    mostrarMensajeGlobal('exito', '🔄 Información actualizada correctamente.');
}

// =============================================================================
// PUNTO DE ENTRADA PRINCIPAL
// =============================================================================
async function validarYProcesar(accion) {
    const checkbox      = document.getElementById('terminos');
    const mensajeGlobal = document.getElementById('mensaje-global');

    if (!checkbox.checked) {
        mensajeGlobal.className    = 'error';
        mensajeGlobal.style.display = 'block';
        mensajeGlobal.textContent  =
            `⚠️ Para ${accion} la información clínica, es obligatorio aceptar los términos de Habeas Data.`;
        setTimeout(() => { mensajeGlobal.style.display = 'none'; }, 6000);
        return;
    }

    if (!validarFormulario()) return;

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

// =============================================================================
// INICIALIZACIÓN
// =============================================================================
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        cargarRegimenes(),
        cargarTiposEPS(),
        cargarTodasLasEPS(),
    ]);
});