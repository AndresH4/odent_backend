// =============================================================================
// aseguramiento.js
// Lógica de validación + integración con el backend (módulo EPS / Flask)
// =============================================================================
 
// ---------------------------------------------------------------------------
// CONSTANTES DE API
// Ajusta BASE_URL si tu servidor Flask corre en otro puerto o prefijo.
// ---------------------------------------------------------------------------
const BASE_URL = '/api';   // ej: 'http://localhost:5000' en desarrollo local
 
// ---------------------------------------------------------------------------
// HELPERS DE VALIDACIÓN (código original conservado íntegramente)
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
// El módulo de login puede guardar la clave del ID con distintos nombres
// según quién lo haya implementado (ID_Usuario, id_usuario, usuario_id...).
// Esta función prueba todas las variantes conocidas para no fallar en falso.
// ---------------------------------------------------------------------------
function obtenerUsuarioIdDeSesion() {
    const sesion = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    return sesion.ID_Usuario || sesion.id_usuario || sesion.usuario_id || sesion.Usuario_ID || null;
}
 
// ---------------------------------------------------------------------------
// CARGA DINÁMICA DE SELECTORES AL INICIAR LA PÁGINA
// Llama a GET /api/tipo-eps    → rellena #tipo-eps-select
// Llama a GET /api/eps         → guarda todas las EPS para filtrar luego
// Llama a GET /api/regimen-eps → rellena #regimen-select
// ---------------------------------------------------------------------------
let todasLasEPS = [];   // caché global de EPS para el filtrado por tipo
 
async function cargarTiposEPS() {
    try {
        const res  = await fetch(`${BASE_URL}/tipo-eps`);
        const data = await res.json();
 
        if (!data.ok) throw new Error(data.error || 'Error al cargar tipos de EPS');
 
        const select = document.getElementById('tipo-eps-select');
        select.innerHTML = '<option value="" disabled selected>Seleccione el tipo de EPS</option>';
 
        // El backend (tipo_eps.py) devuelve Nombre_Tipo como nombre de columna.
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
 
        todasLasEPS = data.data;   // guarda el listado completo en caché
        // Al inicio muestra todas mientras no se ha seleccionado tipo
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
 
        // El backend (regimen_eps.py) devuelve Nombre_Regimen como nombre de columna.
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
}
 
// Filtrado reactivo: cuando el usuario cambia el tipo, recarga el select de EPS
function filtrarEPSporTipo() {
    const tipoId = document.getElementById('tipo-eps-select').value;
 
    // Ocultar error de tipo EPS si existía
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
 
    // Resetea la selección de EPS al cambiar tipo
    document.getElementById('eps-select').value = '';
}
 
// ---------------------------------------------------------------------------
// VALIDACIÓN COMPLETA DEL FORMULARIO (lógica original + nuevos campos)
// Retorna true si todo es válido, false en caso contrario.
// ---------------------------------------------------------------------------
function validarFormulario() {
    const inputs = {
        nombre:   [document.getElementById('nombre'),         document.getElementById('err-nombre')],
        doc:      [document.getElementById('num-doc'),        document.getElementById('err-documento')],
        tel:      [document.getElementById('telefono'),       document.getElementById('err-telefono')],
        email:    [document.getElementById('correo'),         document.getElementById('err-correo')],
        dir:      [document.getElementById('direccion'),      document.getElementById('err-direccion')],
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
 
    // ── Dirección ─────────────────────────────────────────────────────────────
    if (inputs.dir[0].value.trim() === '') {
        mostrarError(inputs.dir[0], inputs.dir[1], '⚠️ Este campo es obligatorio.');
        todoValido = false;
    } else {
        ocultarError(inputs.dir[0], inputs.dir[1]);
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
    }
 
    // ── Régimen (nuevo: antes se enviaba fijo en 1, ahora se exige y se envía) ──
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
    }
 
    return todoValido;
}
 
// ---------------------------------------------------------------------------
// LEER VALORES DEL FORMULARIO (utilitario centralizado)
// ---------------------------------------------------------------------------
function leerFormulario() {
    return {
        nombre:         document.getElementById('nombre').value.trim(),
        tipoDoc:        document.getElementById('tipo-doc').value,
        numDoc:         document.getElementById('num-doc').value.trim(),
        telefono:       document.getElementById('telefono').value.trim(),
        correo:         document.getElementById('correo').value.trim(),
        direccion:      document.getElementById('direccion').value.trim(),
        epsId:          Number(document.getElementById('eps-select').value),
        tipoEpsId:      Number(document.getElementById('tipo-eps-select').value),
        regimenId:      Number(document.getElementById('regimen-select').value),
        numeroAfiliado: document.getElementById('numero-afiliado').value.trim(),
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
// MENSAJE GLOBAL DE ÉXITO / ERROR (reemplaza el alert final)
// Se inyecta en el div#mensaje-global definido en aseguramiento.html
// ---------------------------------------------------------------------------
function mostrarMensajeGlobal(tipo, texto) {
    const el = document.getElementById('mensaje-global');
    if (!el) return;
 
    el.className = tipo === 'exito' ? 'exito' : 'error';
    el.textContent = texto;
    el.style.display = 'block';
 
    // Ocultar automáticamente tras 6 segundos
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}
 
// ---------------------------------------------------------------------------
// ACCIÓN: ASEGURAR DATOS
// Flujo:
//   1. POST /api/paciente   → crea el registro de paciente
//   2. POST /api/afiliacion → crea la afiliación con la EPS
// Notas:
//   • ID_Usuario se obtiene de sessionStorage probando varias claves posibles
//     (ver obtenerUsuarioIdDeSesion), porque distintos módulos de login pueden
//     nombrar el campo de forma distinta.
//   • Fecha_Afiliacion se genera automáticamente como la fecha de hoy.
//   • ID_Regimen_EPS ahora viene del nuevo <select id="regimen-select">,
//     ya no se envía fijo en 1.
// ---------------------------------------------------------------------------
async function asegurarDatos(form) {
    const usuarioId = obtenerUsuarioIdDeSesion();
 
    if (!usuarioId) {
        mostrarMensajeGlobal('error', '❌ No hay sesión activa. Por favor inicie sesión antes de asegurar datos.');
        return;
    }
 
    // ── Paso 1: Crear paciente ────────────────────────────────────────────────
    const bodyPaciente = {
        ID_Usuario: usuarioId,
        // Estos campos son opcionales según paciente.py; los enviamos si los tienes en el form.
        // Si en el futuro añades Fecha_Nacimiento, Genero, etc., agrégalos aquí.
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
            // El servidor rechazó la creación del paciente
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
    // Las claves coinciden EXACTAMENTE con lo que routes.py extrae del body:
    // ID_Usuario, ID_EPS, ID_Regimen_EPS, Fecha_Afiliacion, Numero_Afiliado, Estado
    const bodyAfiliacion = {
        ID_Usuario:       usuarioId,
        ID_EPS:           form.epsId,
        ID_Regimen_EPS:   form.regimenId,
        Fecha_Afiliacion: new Date().toISOString().split('T')[0],  // "YYYY-MM-DD"
        Numero_Afiliado:  form.numeroAfiliado || null,
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
 
        // Guarda IDs en sesión para que actualizarDatos() los encuentre después
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
// Flujo:
//   1. Busca el paciente activo en sesión
//   2. PUT /api/paciente/<id>   → actualiza datos del paciente
//   3. PUT /api/afiliacion/<id> → actualiza la afiliación (EPS) si aplica
// ---------------------------------------------------------------------------
async function actualizarDatos(form) {
    const sesion       = JSON.parse(sessionStorage.getItem('usuario') || '{}');
    const pacienteId   = sesion.id_paciente   || null;
    const afiliacionId = sesion.id_afiliacion || null;
 
    if (!pacienteId) {
        mostrarMensajeGlobal('error', '❌ No se encontró el ID del paciente en la sesión. Use primero "Asegurar Datos".');
        return;
    }
 
    // ── Actualizar paciente ───────────────────────────────────────────────────
    const bodyPaciente = {
        // Añade aquí los campos opcionales que hayas capturado:
        // Fecha_Nacimiento: ...,
        // Genero: ...,
    };
 
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
            ID_EPS:           form.epsId,
            ID_Regimen_EPS:   form.regimenId,
            Fecha_Afiliacion: new Date().toISOString().split('T')[0],
            Numero_Afiliado:  form.numeroAfiliado || null,
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
// PUNTO DE ENTRADA PRINCIPAL — llamado por los botones del HTML
// Conserva la firma original: validarYProcesar('asegurar' | 'actualizar')
// ---------------------------------------------------------------------------
async function validarYProcesar(accion) {
    // 1. Validación del formulario (lógica original conservada)
    const esValido = validarFormulario();
    if (!esValido) return;
 
    // 2. Leer valores
    const form = leerFormulario();
 
    // 3. Deshabilitar botones mientras se procesa
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
    // Carga paralela de tipos de EPS, EPS y regímenes para mayor velocidad
    await Promise.all([
        cargarTiposEPS(),
        cargarTodasLasEPS(),
        cargarRegimenes()
    ]);
 
    // Listener de filtrado reactivo
    document.getElementById('tipo-eps-select')
            .addEventListener('change', filtrarEPSporTipo);
});