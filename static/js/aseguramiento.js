"use strict";

// =============================================================================
// CONSTANTES
// =============================================================================
const BASE_URL       = '/api';
const EPS_OTRO_VALUE = '__OTRO__';

// =============================================================================
// ESTADO LOCAL
// =============================================================================
let todasLasEPS   = [];
let todosTiposEps = [];
let epsFiltradas  = [];

let _usuarioId      = null;   // ID del usuario encontrado en búsqueda
let _pacienteId     = null;
let _especialistaId = null;
let _afiliacionId   = null;
let _rolActual      = null;   // 'Paciente' | 'Especialista' | 'Administrador'

// =============================================================================
// HELPERS DE VALIDACIÓN DE CAMPO
// =============================================================================
function mostrarErrorCampo(el, p, msg) {
    if (!el || !p) return;
    el.classList.add('input-error');
    p.innerText      = msg;
    p.style.display  = 'block';
}
function ocultarErrorCampo(el, p) {
    if (!el || !p) return;
    el.classList.remove('input-error');
    p.innerText      = '';
    p.style.display  = 'none';
}

// =============================================================================
// CARGA DE CATÁLOGOS
// =============================================================================
async function cargarRegimenes() {
    const select   = document.getElementById('regimen-select');
    // Fallback: mapeo con la clave que devuelve la API (Regimen_ID / Descripcion)
    const fallback = [
        { Regimen_ID: 1, Descripcion: 'Contributivo' },
        { Regimen_ID: 2, Descripcion: 'Subsidiado'   },
    ];
    const poblar = (lista) => {
        select.innerHTML = '<option value="" disabled selected>Seleccione el régimen…</option>';
        lista.forEach(r => {
            const opt       = document.createElement('option');
            // La API de /regimen-eps devuelve { ID_Regimen_EPS, Nombre_Regimen }
            // FIX: aceptar ambas formas de clave para ser resiliente
            opt.value       = r.Regimen_ID ?? r.ID_Regimen_EPS;
            opt.textContent = r.Descripcion ?? r.Nombre_Regimen;
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
        { TipoEPS_ID: 1, Nombre_Tipo: 'Cotizante'    },
        { TipoEPS_ID: 2, Nombre_Tipo: 'Beneficiario' },
    ];
    try {
        // FIX: la ruta correcta es /api/tipo-eps (definida en app.py)
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
        // La API devuelve EPS_ID (no ID_EPS); normalizamos aquí para
        // que el resto del código use siempre "ID_EPS"
        todasLasEPS = data.data.map(e => ({
            ...e,
            ID_EPS: e.EPS_ID ?? e.ID_EPS,
        }));
    } catch (err) {
        console.warn('[cargarTodasLasEPS] fallback:', err);
        todasLasEPS = fallback;
    }
}

async function cargarEspecialidades() {
    const select   = document.getElementById('especialidad-select');
    const fallback = [
        { Especialidad_ID: 1, Nombre_Especialidad: 'Endodoncia'         },
        { Especialidad_ID: 2, Nombre_Especialidad: 'Odontopediatría'    },
        { Especialidad_ID: 3, Nombre_Especialidad: 'Odontología General' },
        { Especialidad_ID: 4, Nombre_Especialidad: 'Cirugía Oral'       },
        { Especialidad_ID: 5, Nombre_Especialidad: 'Ortodoncia'         },
        { Especialidad_ID: 6, Nombre_Especialidad: 'Control brackets'   },
    ];
    const poblar = (lista) => {
        select.innerHTML = '<option value="" disabled selected>Seleccione especialidad…</option>';
        lista.forEach(e => {
            const opt       = document.createElement('option');
            opt.value       = e.Especialidad_ID;
            opt.textContent = e.Nombre_Especialidad;
            select.appendChild(opt);
        });
    };
    try {
        // FIX: la ruta es /api/especialidades (definida en app.py)
        const res  = await fetch(`${BASE_URL}/especialidades`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);
        poblar(data.data);
    } catch (err) {
        console.warn('[cargarEspecialidades] fallback:', err);
        poblar(fallback);
    }
}

// =============================================================================
// CONTROL DEL BUSCADOR
// =============================================================================
function onFiltroTipoChange() {
    const tipo    = document.getElementById('filtro-tipo').value;
    const grupo   = document.getElementById('filtro-input-group');
    const label   = document.getElementById('filtro-input-label');
    const input   = document.getElementById('filtro-valor');
    const errBusq = document.getElementById('err-busqueda');
    const icono   = document.getElementById('filtro-input-icon');

    input.value = '';
    ocultarErrorCampo(input, errBusq);

    if (tipo === 'id') {
        label.textContent   = 'ID de Usuario';
        input.placeholder   = 'Ej. 42';
        input.inputMode     = 'numeric';
        // Ícono: identificador numérico
        icono.innerHTML = `<rect x="3" y="4" width="18" height="16" rx="2"/>
                           <line x1="3" y1="9" x2="21" y2="9"/>
                           <line x1="8" y1="14" x2="16" y2="14"/>`;
    } else if (tipo === 'documento') {
        label.textContent   = 'Número de Documento';
        input.placeholder   = 'Ej. 1018234567';
        input.inputMode     = 'numeric';
        // Ícono: documento
        icono.innerHTML = `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                           <polyline points="14 2 14 8 20 8"/>
                           <line x1="16" y1="13" x2="8" y2="13"/>
                           <line x1="16" y1="17" x2="8" y2="17"/>`;
    }

    grupo.style.display = tipo ? 'flex' : 'none';
    // Ocultar formulario si el usuario cambia el tipo de búsqueda
    ocultarFormulario();
}

function ocultarFormulario() {
    document.getElementById('card-formulario').style.display = 'none';
    _usuarioId      = null;
    _pacienteId     = null;
    _especialistaId = null;
    _afiliacionId   = null;
    _rolActual      = null;
}

// =============================================================================
// BÚSQUEDA DE USUARIO — conecta con las rutas de app.py
// GET /api/usuario/<id>                → aseg_get_usuario_por_id
// GET /api/usuario/documento/<numero>  → aseg_get_usuario_por_documento
// =============================================================================
async function buscarUsuario() {
    const tipo    = document.getElementById('filtro-tipo').value;
    const valor   = document.getElementById('filtro-valor').value.trim();
    const input   = document.getElementById('filtro-valor');
    const errBusq = document.getElementById('err-busqueda');
    const btnBusc = document.getElementById('btn-buscar');
    const btnTexto = document.getElementById('btn-buscar-texto');

    ocultarErrorCampo(input, errBusq);

    if (!tipo) {
        mostrarErrorCampo(input, errBusq, '⚠️ Seleccione primero el tipo de búsqueda.');
        return;
    }
    if (!valor) {
        mostrarErrorCampo(input, errBusq, '⚠️ Ingrese un valor para buscar.');
        return;
    }
    // Validación básica: ambos campos deben ser numéricos
    if (!/^\d+$/.test(valor)) {
        mostrarErrorCampo(input, errBusq, '❌ Solo se permiten números.');
        return;
    }

    btnBusc.disabled   = true;
    btnTexto.textContent = 'Buscando…';

    try {
        // FIX: rutas correctas según app.py
        const url = tipo === 'id'
            ? `${BASE_URL}/usuario/${encodeURIComponent(valor)}`
            : `${BASE_URL}/usuario/documento/${encodeURIComponent(valor)}`;

        const res  = await fetch(url);
        const data = await res.json();

        if (!data.ok || !data.data) {
            mostrarErrorCampo(input, errBusq,
                res.status === 404
                    ? '❌ Usuario no encontrado.'
                    : `❌ Error del servidor: ${data.error || 'desconocido'}`
            );
            ocultarFormulario();
            return;
        }

        await poblarFormulario(data.data);
        const card = document.getElementById('card-formulario');
        card.style.display = 'block';
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        console.error('[buscarUsuario]', err);
        mostrarErrorCampo(input, errBusq, '❌ Error de conexión. Verifique el servidor.');
        ocultarFormulario();
    } finally {
        btnBusc.disabled     = false;
        btnTexto.textContent = 'Buscar';
    }
}

// =============================================================================
// POBLAR FORMULARIO CON DATOS DEL USUARIO
// Los campos retornados por la API: Usuario_ID, Nombres, Apellidos,
// TipoDoc_ID, NumeroDocumento, Correo, Telefono, Rol_ID
// =============================================================================
async function poblarFormulario(usuario) {
    // FIX: la API devuelve "Usuario_ID" (mayúscula) — aceptar ambas variantes
    _usuarioId = usuario.Usuario_ID ?? usuario.usuario_id;

    document.getElementById('nombres').value   = usuario.Nombres    || '';
    document.getElementById('apellidos').value = usuario.Apellidos  || '';
    document.getElementById('num-doc').value   = usuario.NumeroDocumento || '';
    document.getElementById('telefono').value  = usuario.Telefono   || '';
    document.getElementById('correo').value    = usuario.Correo     || '';

    // Tipo de documento
    const tipoDocSelect = document.getElementById('tipo-doc');
    if (usuario.TipoDoc_ID) {
        tipoDocSelect.value = String(usuario.TipoDoc_ID);
    }

    // Mapa Rol_ID → nombre
    const rolMap = { 1: 'Administrador', 2: 'Especialista', 3: 'Paciente' };
    _rolActual = rolMap[usuario.Rol_ID] || 'Paciente';
    document.getElementById('campo-rol-display').textContent = _rolActual;

    // Badge
    const iconMap = { Administrador: '🛡️', Especialista: '🦷', Paciente: '👤' };
    const badge   = document.getElementById('rol-badge');
    badge.className = `aseg-rol-badge rol-${_rolActual.toLowerCase()}`;
    document.getElementById('rol-icono').textContent = iconMap[_rolActual] || '👤';
    document.getElementById('rol-texto').textContent = _rolActual;

    // Ocultar secciones condicionales antes de mostrar la correcta
    document.getElementById('seccion-paciente').style.display     = 'none';
    document.getElementById('seccion-especialista').style.display = 'none';

    // Limpiar checkbox de términos al cargar un usuario nuevo
    const cb = document.getElementById('terminos');
    cb.checked = false;
    actualizarEstadoAutorizacion();

    if (_rolActual === 'Paciente') {
        document.getElementById('seccion-paciente').style.display = 'block';
        await cargarDatosPaciente(_usuarioId);
    } else if (_rolActual === 'Especialista') {
        document.getElementById('seccion-especialista').style.display = 'block';
        await cargarDatosEspecialista(_usuarioId);
    }
    // Administrador: solo datos básicos — no hay sección adicional
}

// =============================================================================
// CARGAR DATOS DE PACIENTE
// GET /api/paciente/por-usuario/<uid>   → { Paciente_ID }   (app.py)
// GET /api/afiliacion/por-usuario/<uid> → { ok, data: { Afiliacion_ID, EPS_ID,
//                                            TipoEPS_ID, Regimen_ID } }  (app.py)
// =============================================================================
async function cargarDatosPaciente(usuarioId) {
    // 1. Obtener Paciente_ID
    try {
        const res = await fetch(`${BASE_URL}/paciente/por-usuario/${usuarioId}`);
        if (res.ok) {
            const data = await res.json();
            // FIX: este endpoint devuelve { Paciente_ID } sin envoltura ok/data
            if (data.Paciente_ID) _pacienteId = data.Paciente_ID;
        }
    } catch (err) {
        console.warn('[cargarDatosPaciente] paciente:', err);
    }

    // 2. Obtener afiliación (con Regimen_ID por JOIN en la API)
    try {
        const res  = await fetch(`${BASE_URL}/afiliacion/por-usuario/${usuarioId}`);
        const data = await res.json();
        if (!data.ok || !data.data) return; // paciente sin afiliación registrada — OK

        const af     = data.data;
        _afiliacionId = af.Afiliacion_ID;

        // Poblar régimen
        const regimenSelect = document.getElementById('regimen-select');
        if (af.Regimen_ID) {
            regimenSelect.value = String(af.Regimen_ID);
            // Disparar cascada: régimen → tipos EPS
            onRegimenChangeAseg();

            // Poblar tipo EPS (después de que onRegimenChangeAseg cargó las opciones)
            if (af.TipoEPS_ID) {
                const tipoEpsSelect = document.getElementById('tipo-eps-select');
                tipoEpsSelect.value = String(af.TipoEPS_ID);
                // Disparar cascada: tipo EPS → lista de EPS
                onTipoEpsChangeAseg();

                // Poblar EPS
                if (af.EPS_ID) {
                    // Pequeño defer para que el DOM tenga las opciones cargadas
                    await new Promise(r => setTimeout(r, 0));
                    const epsSelect = document.getElementById('eps-select');
                    epsSelect.value = String(af.EPS_ID);
                }
            }
        }
    } catch (err) {
        console.warn('[cargarDatosPaciente] afiliación:', err);
    }
}

// =============================================================================
// CARGAR DATOS DE ESPECIALISTA
// GET /api/especialista/por-usuario/<uid> → { ok, data: { Especialista_ID,
//                                              Tarjeta_Profesional, Especialidad_ID }}
// =============================================================================
async function cargarDatosEspecialista(usuarioId) {
    try {
        const res  = await fetch(`${BASE_URL}/especialista/por-usuario/${usuarioId}`);
        const data = await res.json();
        if (!data.ok || !data.data) return;

        const esp       = data.data;
        _especialistaId = esp.Especialista_ID;

        document.getElementById('tarjeta-profesional').value = esp.Tarjeta_Profesional || '';

        if (esp.Especialidad_ID) {
            // Diferir por si el select aún no tiene las opciones cargadas
            await new Promise(r => setTimeout(r, 0));
            document.getElementById('especialidad-select').value = String(esp.Especialidad_ID);
        }
    } catch (err) {
        console.warn('[cargarDatosEspecialista]', err);
    }
}

// =============================================================================
// CASCADING DROPDOWNS: RÉGIMEN → TIPO EPS → EPS
// =============================================================================
function onRegimenChangeAseg() {
    const regimenId  = document.getElementById('regimen-select').value;
    const selectTipo = document.getElementById('tipo-eps-select');
    const selectEps  = document.getElementById('eps-select');

    ocultarErrorCampo(
        document.getElementById('regimen-select'),
        document.getElementById('err-regimen')
    );

    // Resetear los siguientes selectores
    selectTipo.innerHTML = '<option value="" disabled selected>Seleccione el tipo de afiliación…</option>';
    selectEps.innerHTML  = '<option value="" disabled selected>Seleccione primero el tipo</option>';
    selectTipo.disabled  = true;
    selectEps.disabled   = true;
    document.getElementById('eps-otro-container').style.display = 'none';

    if (!regimenId) return;

    // Poblar tipos EPS (no están filtrados por régimen — todos aplican)
    todosTiposEps.forEach(t => {
        const opt       = document.createElement('option');
        // FIX: aceptar ambas claves posibles de la API
        opt.value       = t.TipoEPS_ID ?? t.ID_Tipo_EPS;
        opt.textContent = t.Nombre_Tipo;
        selectTipo.appendChild(opt);
    });
    selectTipo.disabled = false;

    // Filtrar EPS por régimen para el siguiente nivel
    epsFiltradas = todasLasEPS.filter(e => String(e.Regimen_ID) === String(regimenId));
}

function onTipoEpsChangeAseg() {
    const selectEps  = document.getElementById('eps-select');
    const selectTipo = document.getElementById('tipo-eps-select');

    ocultarErrorCampo(selectTipo, document.getElementById('err-tipo-eps'));

    selectEps.innerHTML = '<option value="" disabled selected>Seleccione la EPS…</option>';
    selectEps.disabled  = true;
    document.getElementById('eps-otro-container').style.display = 'none';

    if (!selectTipo.value) return;

    // Usar EPS filtradas por régimen; si no hay filtro, mostrar todas
    const lista = epsFiltradas.length > 0 ? epsFiltradas : todasLasEPS;
    lista.forEach(eps => {
        const opt       = document.createElement('option');
        opt.value       = eps.ID_EPS;
        opt.textContent = eps.Nombre_EPS;
        selectEps.appendChild(opt);
    });

    // Opción para crear una EPS nueva
    const optOtro       = document.createElement('option');
    optOtro.value       = EPS_OTRO_VALUE;
    optOtro.textContent = '➕ Otra (registrar nueva EPS)';
    selectEps.appendChild(optOtro);

    selectEps.disabled = false;
}

function manejarSeleccionEPS() {
    const epsSelect = document.getElementById('eps-select');
    ocultarErrorCampo(epsSelect, document.getElementById('err-eps'));

    if (epsSelect.value === EPS_OTRO_VALUE) {
        document.getElementById('eps-otro-container').style.display = 'block';
    } else {
        document.getElementById('eps-otro-container').style.display = 'none';
        document.getElementById('eps-otro-nombre').value   = '';
        document.getElementById('eps-otro-telefono').value = '';
        ocultarErrorCampo(
            document.getElementById('eps-otro-nombre'),
            document.getElementById('err-eps-otro-nombre')
        );
        ocultarErrorCampo(
            document.getElementById('eps-otro-telefono'),
            document.getElementById('err-eps-otro-telefono')
        );
    }
}

// =============================================================================
// HABEAS DATA
// =============================================================================
function toggleAutorizacion() {
    const cb     = document.getElementById('terminos');
    cb.checked   = !cb.checked;
    actualizarEstadoAutorizacion();
}

function actualizarEstadoAutorizacion() {
    const cb          = document.getElementById('terminos');
    const caja        = document.getElementById('recaptcha-box');
    const check       = document.getElementById('recaptcha-check');
    const errTerminos = document.getElementById('err-terminos');

    if (caja) {
        caja.classList.toggle('checked', cb.checked);
        caja.style.background  = cb.checked ? '#0ea5e9' : '#ffffff';
        caja.style.borderColor = cb.checked ? '#0ea5e9' : '#9ca3af';
    }
    if (check) {
        check.style.opacity   = cb.checked ? '1' : '0';
        check.style.transform = cb.checked ? 'scale(1)' : 'scale(0.4)';
    }
    if (cb.checked && errTerminos) errTerminos.style.display = 'none';
}

// =============================================================================
// VALIDACIÓN DEL FORMULARIO
// =============================================================================
function validarFormulario() {
    const nombres   = document.getElementById('nombres');
    const apellidos = document.getElementById('apellidos');
    const numDoc    = document.getElementById('num-doc');
    const telefono  = document.getElementById('telefono');
    const correo    = document.getElementById('correo');
    const tipoDoc   = document.getElementById('tipo-doc');
    const regexEmail = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;
    let ok = true;

    // Helper local: evalúa condición y muestra/oculta error
    const check = (el, errId, cond, msg) => {
        if (cond) { mostrarErrorCampo(el, document.getElementById(errId), msg); ok = false; }
        else        ocultarErrorCampo(el, document.getElementById(errId));
    };

    check(nombres,   'err-nombres',   !nombres.value.trim(),           '⚠️ Campo obligatorio.');
    check(nombres,   'err-nombres',   /\d/.test(nombres.value),        '❌ Sin números en el nombre.');
    check(apellidos, 'err-apellidos', !apellidos.value.trim(),         '⚠️ Campo obligatorio.');
    check(numDoc,    'err-num-doc',   !numDoc.value.trim(),            '⚠️ Campo obligatorio.');
    check(telefono,  'err-telefono',  !telefono.value.trim(),          '⚠️ Campo obligatorio.');
    check(correo,    'err-correo',    !correo.value.trim(),            '⚠️ Campo obligatorio.');
    check(correo,    'err-correo',    !regexEmail.test(correo.value),  '❌ Formato de correo inválido.');
    check(tipoDoc,   'err-tipo-doc',  !tipoDoc.value,                  '⚠️ Seleccione el tipo de documento.');

    if (_rolActual === 'Paciente') {
        const regimen   = document.getElementById('regimen-select');
        const tipoEps   = document.getElementById('tipo-eps-select');
        const epsSelect = document.getElementById('eps-select');

        check(regimen,   'err-regimen',  !regimen.value,   '⚠️ Seleccione el régimen.');
        check(tipoEps,   'err-tipo-eps', !tipoEps.value,   '⚠️ Seleccione el tipo de afiliación.');
        check(epsSelect, 'err-eps',      !epsSelect.value, '⚠️ Seleccione la EPS.');

        if (epsSelect.value === EPS_OTRO_VALUE) {
            const nOtro = document.getElementById('eps-otro-nombre');
            const tOtro = document.getElementById('eps-otro-telefono');
            check(nOtro, 'err-eps-otro-nombre',   !nOtro.value.trim(), '⚠️ Ingrese el nombre de la EPS.');
            check(tOtro, 'err-eps-otro-telefono', !tOtro.value.trim(), '⚠️ Ingrese el teléfono de la EPS.');
        }
    }

    if (_rolActual === 'Especialista') {
        const esp = document.getElementById('especialidad-select');
        const tp  = document.getElementById('tarjeta-profesional');
        check(esp, 'err-especialidad', !esp.value,        '⚠️ Seleccione la especialidad.');
        check(tp,  'err-tarjeta',      !tp.value.trim(),  '⚠️ Ingrese la tarjeta profesional.');
    }

    if (!document.getElementById('terminos').checked) {
        const et = document.getElementById('err-terminos');
        if (et) { et.innerText = '⚠️ Debe autorizar el tratamiento de los datos.'; et.style.display = 'block'; }
        ok = false;
    }

    return ok;
}

// =============================================================================
// LEER FORMULARIO
// =============================================================================
function leerFormulario() {
    const epsSelect = document.getElementById('eps-select');
    const esEpsOtro = _rolActual === 'Paciente' && epsSelect && epsSelect.value === EPS_OTRO_VALUE;

    return {
        nombres:            document.getElementById('nombres').value.trim(),
        apellidos:          document.getElementById('apellidos').value.trim(),
        tipoDocId:          Number(document.getElementById('tipo-doc').value) || null,
        numDoc:             document.getElementById('num-doc').value.trim(),
        telefono:           document.getElementById('telefono').value.trim(),
        correo:             document.getElementById('correo').value.trim(),
        regimenId:          _rolActual === 'Paciente'     ? Number(document.getElementById('regimen-select').value) : null,
        tipoEpsId:          _rolActual === 'Paciente'     ? Number(document.getElementById('tipo-eps-select').value) : null,
        epsId:              _rolActual === 'Paciente' && !esEpsOtro ? Number(epsSelect.value) : null,
        esEpsOtro,
        epsOtroNombre:      esEpsOtro ? document.getElementById('eps-otro-nombre').value.trim()   : null,
        epsOtroTelefono:    esEpsOtro ? document.getElementById('eps-otro-telefono').value.trim() : null,
        especialidadId:     _rolActual === 'Especialista' ? Number(document.getElementById('especialidad-select').value) : null,
        tarjetaProfesional: _rolActual === 'Especialista' ? document.getElementById('tarjeta-profesional').value.trim() : null,
    };
}

// =============================================================================
// ESTADO DE BOTONES
// =============================================================================
function setBotonesEstado(cargando) {
    document.querySelectorAll('.btn-accion').forEach(btn => { btn.disabled = cargando; });
}

// =============================================================================
// MENSAJE GLOBAL
// =============================================================================
function mostrarMensajeGlobal(tipo, texto) {
    const el = document.getElementById('mensaje-global');
    if (!el) return;
    el.className     = tipo === 'exito' ? 'exito' : 'error';
    el.textContent   = texto;
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setTimeout(() => { el.style.display = 'none'; }, 7000);
}

// =============================================================================
// CREAR EPS NUEVA
// POST /api/eps  → { ok, data: { ID_EPS } }
// =============================================================================
async function crearNuevaEPS(nombre, telefono, tipoEpsId) {
    try {
        const res  = await fetch(`${BASE_URL}/eps`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Nombre_EPS: nombre, ID_Tipo_EPS: tipoEpsId, Telefono: telefono }),
        });
        const data = await res.json();
        if (!data.ok) {
            mostrarMensajeGlobal('error', `❌ Error al crear la EPS: ${data.error}`);
            return null;
        }
        return data.data.ID_EPS;
    } catch (err) {
        mostrarMensajeGlobal('error', '❌ No se pudo crear la nueva EPS.');
        return null;
    }
}

// =============================================================================
// ACTUALIZAR DATOS BÁSICOS DEL USUARIO
// PUT /api/usuario/<id>  → { ok, mensaje }
// =============================================================================
async function actualizarDatosBasicos(form) {
    const res  = await fetch(`${BASE_URL}/usuario/${_usuarioId}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
            Nombres:         form.nombres,
            Apellidos:       form.apellidos,
            TipoDoc_ID:      form.tipoDocId,
            NumeroDocumento: form.numDoc,
            Telefono:        form.telefono,
            Correo:          form.correo,
        }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Error al actualizar datos básicos.');
    return data;
}

// =============================================================================
// FLUJO PRINCIPAL: ASEGURAR / ACTUALIZAR
// =============================================================================
async function asegurarDatos(form) {
    // 1. Actualizar datos básicos del usuario
    try {
        await actualizarDatosBasicos(form);
    } catch (err) {
        mostrarMensajeGlobal('error', `❌ ${err.message}`);
        return;
    }

    // 2. Persistir datos específicos por rol
    if (_rolActual === 'Paciente') {
        await asegurarDatosPaciente(form);
    } else if (_rolActual === 'Especialista') {
        await asegurarDatosEspecialista(form);
    } else {
        // Administrador: solo datos básicos
        mostrarMensajeGlobal('exito', '✅ Datos del administrador actualizados correctamente.');
        await registrarAuditoria(_usuarioId, _afiliacionId ? 2 : 1, 'Datos básicos actualizados desde módulo de aseguramiento');
    }
}

async function asegurarDatosPaciente(form) {
    // Si es EPS nueva, crearla primero
    let epsIdFinal = form.epsId;
    if (form.esEpsOtro) {
        epsIdFinal = await crearNuevaEPS(form.epsOtroNombre, form.epsOtroTelefono, form.tipoEpsId);
        if (!epsIdFinal) return;
        await cargarTodasLasEPS(); // refrescar catálogo local
    }

    // Crear registro de paciente si no existe
    if (!_pacienteId) {
        try {
            const res  = await fetch(`${BASE_URL}/paciente`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ ID_Usuario: _usuarioId }),
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Error al registrar paciente: ${data.error}`);
                return;
            }
            _pacienteId = data.data.ID_Paciente;
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ No se pudo registrar al paciente.');
            return;
        }
    }

    const bodyAfil = {
        ID_Usuario:       _usuarioId,
        ID_EPS:           epsIdFinal,
        ID_Tipo_EPS:      form.tipoEpsId,
        Fecha_Afiliacion: new Date().toISOString().split('T')[0],
    };

    if (_afiliacionId) {
        // Actualizar afiliación existente
        // PUT /api/afiliacion/<id>  (routes.py)
        try {
            const res  = await fetch(`${BASE_URL}/afiliacion/${_afiliacionId}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(bodyAfil),
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Error al actualizar afiliación: ${data.error}`);
                return;
            }
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ No se pudo actualizar la afiliación.');
            return;
        }
    } else {
        // Crear nueva afiliación
        // POST /api/afiliacion  (routes.py)
        try {
            const res  = await fetch(`${BASE_URL}/afiliacion`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(bodyAfil),
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Error al crear afiliación: ${data.error}`);
                return;
            }
            _afiliacionId = data.data.ID_Afiliacion;
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ No se pudo crear la afiliación.');
            return;
        }
    }

    // FIX: Accion_ID correcto: 1=Asegurar (nuevo), 2=Actualizar (existente)
    await registrarAuditoria(
        _usuarioId,
        _afiliacionId ? 2 : 1,
        'Datos de paciente asegurados desde módulo de aseguramiento'
    );

    mostrarMensajeGlobal('exito', `✅ Datos del paciente asegurados correctamente (Paciente #${_pacienteId}).`);
}

async function asegurarDatosEspecialista(form) {
    if (!_especialistaId) {
        // Crear especialista
        // POST /api/especialista  (app.py)
        try {
            const res  = await fetch(`${BASE_URL}/especialista`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    Usuario_ID:          _usuarioId,
                    Tarjeta_Profesional: form.tarjetaProfesional,
                    Especialidad_ID:     form.especialidadId,
                }),
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Error al registrar especialista: ${data.error}`);
                return;
            }
            _especialistaId = data.data.Especialista_ID;
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ No se pudo registrar al especialista.');
            return;
        }
    } else {
        // Actualizar especialista existente
        // PUT /api/especialista/<id>  (app.py)
        try {
            const res  = await fetch(`${BASE_URL}/especialista/${_especialistaId}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    Tarjeta_Profesional: form.tarjetaProfesional,
                    Especialidad_ID:     form.especialidadId,
                }),
            });
            const data = await res.json();
            if (!data.ok) {
                mostrarMensajeGlobal('error', `❌ Error al actualizar especialista: ${data.error}`);
                return;
            }
        } catch (err) {
            mostrarMensajeGlobal('error', '❌ No se pudo actualizar al especialista.');
            return;
        }
    }

    await registrarAuditoria(_usuarioId, 2, 'Datos de especialista actualizados desde módulo de aseguramiento');
    mostrarMensajeGlobal('exito', '✅ Datos del especialista actualizados correctamente.');
}

// =============================================================================
// REGISTRAR AUDITORÍA — no bloquea el flujo si falla
// POST /api/aseguramiento  (app.py)
// =============================================================================
async function registrarAuditoria(usuarioId, accionId, descripcion) {
    try {
        await fetch(`${BASE_URL}/aseguramiento`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                Usuario_ID:  usuarioId,
                Accion_ID:   accionId,
                Fecha:       new Date().toISOString().split('T')[0],
                Descripcion: descripcion,
            }),
        });
    } catch (_) { /* No crítico */ }
}

// =============================================================================
// PUNTO DE ENTRADA PRINCIPAL
// =============================================================================
async function validarYProcesar(accion) {
    if (!_usuarioId) {
        mostrarMensajeGlobal('error', '⚠️ Primero busque y seleccione un usuario.');
        return;
    }

    // Verificar Habeas Data antes de validar los campos
    if (!document.getElementById('terminos').checked) {
        mostrarMensajeGlobal('error',
            `⚠️ Para ${accion === 'asegurar' ? 'asegurar' : 'actualizar'} los datos, debe aceptar los términos de Habeas Data.`
        );
        return;
    }

    if (!validarFormulario()) return;

    const form = leerFormulario();
    setBotonesEstado(true);

    try {
        await asegurarDatos(form);
    } finally {
        setBotonesEstado(false);
    }
}

// =============================================================================
// INICIALIZACIÓN — carga catálogos en paralelo al cargar la página
// =============================================================================
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        cargarRegimenes(),
        cargarTiposEPS(),
        cargarTodasLasEPS(),
        cargarEspecialidades(),
    ]);
});