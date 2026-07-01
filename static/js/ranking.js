// =============================================================================
// ranking.js  —  Stylo Dental · Ranking de Satisfacción
// VERSIÓN CORREGIDA (v3)
// =============================================================================
//
// CAMBIOS CLAVE respecto a la versión anterior:
//
// 1) ESTADO POR DEFECTO SIEMPRE ACTIVO (true), tanto en las variables
//    iniciales como en cualquier ruta de error. Antes, un fallo de red al
//    cargar la configuración ponía `estadoEnvioActivo = false` "por
//    seguridad" — eso es exactamente lo que hacía parecer que el ranking
//    "se apagaba solo" o "no se guardaba": no era un problema de guardado,
//    era la propia UI reescribiéndose a inactivo ante cualquier error.
//
// 2) El estado SOLO cambia a inactivo por una de estas dos causas:
//      a) El servidor respondió explícitamente Estado=2 (dato real de la BD).
//      b) El usuario dio clic en el toggle y luego en "Guardar cambios".
//    Un error de red, un fetch fallido, o una respuesta inesperada YA NO
//    fuerzan estadoEnvioActivo a false. En su lugar, se muestra un error
//    y se conserva el último estado conocido (o el default activo).
//
// 3) Se eliminó la llamada rota `fetch(`${BASE_URL}/encuesta/estado`)` que
//    leía `estadoData.activo` (campo que el backend nunca devolvía con ese
//    contrato). Ahora TODO el frontend usa una única función central
//    `_obtenerEstadoDesdeServidor()` que llama a GET /config-ranking,
//    la única fuente de verdad real.
//
// 4) `enviarRespuestaEncuesta()` ya no desactiva el estado local ante un
//    error de verificación — solo lo hace si el servidor confirma Estado=2.
// =============================================================================

const BASE_URL = '/api';

// Por defecto: ACTIVO. Este valor solo se usa hasta que la primera carga
// real desde el servidor confirme el estado verdadero.
let estadoEnvioActivo    = true;   // reflejo local del valor en DB
let estadoPendiente      = true;   // valor seleccionado pero aún no guardado
let cambiosPendientes    = false;  // hay cambios no persistidos
let preguntasCache       = [];
let idPreguntaPendente   = null;

// =============================================================================
// UTILIDADES DE UI
// =============================================================================

function mostrarMensaje(elId, tipo, texto) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.className     = tipo === 'exito' ? 'exito' : 'error';
    el.textContent   = texto;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}

/**
 * Toast corporativo con título y subtítulo opcionales.
 * @param {string} titulo   Texto principal
 * @param {string} subtexto Texto secundario (opcional)
 * @param {'ok'|'error'} tipo
 */
function lanzarToast(titulo, subtexto = '', tipo = 'ok') {
    const toast    = document.getElementById('toast-ranking');
    const iconoEl  = document.getElementById('toast-icono');
    const textoEl  = document.getElementById('toast-texto');
    const subEl    = document.getElementById('toast-subtexto');

    if (!toast) return;

    // Reiniciar animación
    toast.classList.remove('show');
    void toast.offsetWidth;

    textoEl.textContent = titulo;
    subEl.textContent   = subtexto;

    if (tipo === 'error') {
        toast.style.borderLeftColor = '#dc2626';
        iconoEl.className = 'toast-icono error-icono';
        iconoEl.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    } else {
        toast.style.borderLeftColor = '#0284c7';
        iconoEl.className = 'toast-icono';
        iconoEl.innerHTML = '<i class="fa-solid fa-check"></i>';
    }

    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
        toast.classList.remove('show');
    }, 3100);
}

function mostrarError(inputEl, errEl, msg) {
    if (inputEl) inputEl.classList.add('input-error');
    if (errEl)   { errEl.textContent = msg; errEl.style.display = 'block'; }
}

function ocultarError(inputEl, errEl) {
    if (inputEl) inputEl.classList.remove('input-error');
    if (errEl)   errEl.style.display = 'none';
}

function renderEstrellas(promedio) {
    let html = '<div class="estrellas-display">';
    for (let i = 1; i <= 5; i++) {
        if (promedio >= i)           html += '<span class="star llena">★</span>';
        else if (promedio >= i - 0.5) html += '<span class="star media">★</span>';
        else                          html += '<span class="star">★</span>';
    }
    return html + '</div>';
}

// =============================================================================
// NAVEGACIÓN ENTRE VISTAS
// =============================================================================

function mostrarConfig() {
    document.getElementById('rankingView').style.display = 'none';
    document.getElementById('configView').style.display  = 'block';
    cambiosPendientes = false;
    cargarPreguntas();
    cargarEstadoEnvio();
}

function volverRanking() {
    document.getElementById('configView').style.display  = 'none';
    document.getElementById('rankingView').style.display = 'block';
    cargarRanking();
}

// =============================================================================
// ESTADO DE ENVÍO — fuente única de verdad + carga + UI + bloqueo
// =============================================================================

/**
 * Única función que consulta el estado real en el servidor.
 * Devuelve { ok: true, estado: 1|2 } si pudo leerlo, o { ok: false, error }
 * si hubo un problema de red/servidor. NUNCA decide por sí sola apagar el
 * envío: eso es responsabilidad de quien la llama, y solo debe hacerlo si
 * ok === true y estado === 2.
 */
async function _obtenerEstadoDesdeServidor() {
    try {
        const res  = await fetch(`${BASE_URL}/config-ranking`);
        const data = await res.json();

        if (!res.ok || !data.ok) {
            return { ok: false, error: data?.error || `Error HTTP ${res.status}` };
        }

        const estadoRaw = data.data?.Estado ?? data.Estado;
        const estado    = parseInt(estadoRaw, 10);

        if (estado !== 1 && estado !== 2) {
            return { ok: false, error: 'Respuesta de configuración inválida.' };
        }

        return { ok: true, estado };

    } catch (err) {
        return { ok: false, error: err.message || 'Error de red.' };
    }
}

/**
 * Carga el estado persistido en BD y sincroniza la UI.
 * El estado en DB es la fuente de verdad.
 *
 * CORREGIDO: si la carga falla (red caída, servidor no responde, etc.),
 * YA NO se fuerza estadoEnvioActivo = false. Se conserva el último estado
 * conocido (o el default `true` si es la primera carga) y solo se informa
 * el error, para no apagar el envío de encuestas por un problema transitorio.
 */
async function cargarEstadoEnvio() {
    const resultado = await _obtenerEstadoDesdeServidor();

    if (!resultado.ok) {
        console.error('[cargarEstadoEnvio]', resultado.error);
        mostrarMensaje(
            'mensaje-global-config',
            'error',
            `⚠️ No se pudo verificar el estado del envío (se mantiene el último valor conocido: ${estadoEnvioActivo ? 'Activo' : 'Inactivo'}).`
        );
        // No tocamos estadoEnvioActivo/estadoPendiente: se conserva tal cual.
        _aplicarEstadoUI();
        return;
    }

    // Éxito: el servidor es la única fuente de verdad, se adopta tal cual.
    estadoEnvioActivo = resultado.estado === 1;
    estadoPendiente   = estadoEnvioActivo;
    cambiosPendientes = false;

    _aplicarEstadoUI();
}

/**
 * Propaga el estado visual a todos los elementos de la UI.
 */
function _aplicarEstadoUI() {
    const btn   = document.getElementById('btn-toggle-estado');
    const label = document.getElementById('toggle-label-text');

    if (btn && label) {
        if (estadoPendiente) {
            btn.classList.remove('inactivo');
            btn.setAttribute('aria-pressed', 'true');
            label.textContent = 'Activo';
            label.classList.remove('inactivo');
        } else {
            btn.classList.add('inactivo');
            btn.setAttribute('aria-pressed', 'false');
            label.textContent = 'Inactivo';
            label.classList.add('inactivo');
        }
    }

    // Banner en vista ranking refleja el estado PERSISTIDO (no el pendiente)
    _actualizarBannerEstado();

    // Controles de envío se bloquean según estado PERSISTIDO
    _bloquearControlesEnvio(!estadoEnvioActivo);

    // Botón guardar: indicar si hay cambios pendientes
    _actualizarBotonGuardar();
}

function _actualizarBotonGuardar() {
    const btn = document.getElementById('btn-guardar-cambios');
    if (!btn) return;
    const textoEl = btn.querySelector('.btn-guardar-texto');
    if (cambiosPendientes) {
        btn.style.boxShadow = '0 0 0 3px rgba(2, 132, 199, 0.18), 0 2px 12px rgba(2, 132, 199, 0.28)';
        if (textoEl) textoEl.textContent = 'Guardar cambios';
    } else {
        btn.style.boxShadow = '';
    }
}

/**
 * Banner de advertencia en rankingView con diseño corporativo.
 * Refleja estado PERSISTIDO (estadoEnvioActivo), no el pendiente.
 */
function _actualizarBannerEstado() {
    const bannerId = 'banner-envio-inactivo';
    let   banner   = document.getElementById(bannerId);

    if (!estadoEnvioActivo) {
        if (!banner) {
            banner           = document.createElement('div');
            banner.id        = bannerId;
            banner.className = 'banner-estado-inactivo';
            banner.innerHTML = `
                <div class="banner-icono-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                         viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
                    </svg>
                </div>
                <div class="banner-cuerpo">
                    <span class="banner-titulo">Envío de encuestas suspendido</span>
                    <span class="banner-desc">
                        Las encuestas no se enviarán a los pacientes mientras el envío esté
                        desactivado. Para reactivarlo, accede a
                        <button class="banner-link-config" onclick="mostrarConfig()">Configuración</button>.
                    </span>
                </div>
            `;
            const body  = document.querySelector('#rankingView .body');
            const tabla = document.getElementById('ranking-tabla-container');
            const load  = document.getElementById('ranking-loading');
            const ref   = tabla || load;
            if (body && ref) body.insertBefore(banner, ref);
            else if (body) body.prepend(banner);
        }
        banner.style.display = 'flex';
    } else {
        if (banner) {
            banner.style.display = 'none';
        }
    }
}

function _bloquearControlesEnvio(bloquear) {
    const selectores = [
        '[data-envio="true"]',
        '.btn-enviar-encuesta',
        '#btn-enviar-encuesta',
        'button[data-accion="enviar"]'
    ];
    selectores.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            el.disabled = bloquear;
            el.classList.toggle('btn-bloqueado', bloquear);
            el.title = bloquear
                ? 'El envío de encuestas está desactivado. Actívalo en Configuración.'
                : '';
        });
    });
}

// =============================================================================
// TOGGLE — actualiza estado pendiente (NO persiste hasta "Guardar cambios")
// =============================================================================
//
// Este es el ÚNICO punto donde el usuario puede iniciar un cambio a
// inactivo. Nada más en este archivo puede poner estadoPendiente en false
// salvo esta función o la confirmación real del servidor en
// cargarEstadoEnvio() / guardarCambiosConfig().
// =============================================================================

function toggleEstado() {
    estadoPendiente   = !estadoPendiente;
    cambiosPendientes = estadoPendiente !== estadoEnvioActivo;
    _aplicarEstadoUI();
}

// =============================================================================
// GUARDAR CAMBIOS — persiste el estado pendiente en DB (única vía de escritura)
// =============================================================================

async function guardarCambiosConfig() {
    const btn     = document.getElementById('btn-guardar-cambios');
    const textoEl = btn?.querySelector('.btn-guardar-texto');

    if (btn) {
        btn.disabled = true;
        btn.classList.add('cargando');
        if (textoEl) textoEl.textContent = 'Guardando…';
    }

    try {
        const res = await fetch(`${BASE_URL}/config-ranking`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Estado: estadoPendiente ? 1 : 2 })
        });
        const data = await res.json();

        if (!res.ok || !data.ok) throw new Error(data.error || 'Error al guardar la configuración');

        // Confirmar con el valor que retorna el servidor (fuente de verdad)
        const estadoConfirmado = data.data?.Estado ?? (estadoPendiente ? 1 : 2);
        estadoEnvioActivo      = parseInt(estadoConfirmado, 10) === 1;
        estadoPendiente        = estadoEnvioActivo;
        cambiosPendientes      = false;

        _aplicarEstadoUI();

        lanzarToast(
            'Cambios guardados correctamente',
            estadoEnvioActivo
                ? 'El envío automático está activo.'
                : 'El envío automático está suspendido.',
            'ok'
        );

    } catch (err) {
        console.error('[guardarCambiosConfig]', err);
        // Fallo al GUARDAR: revertimos el toggle visual al último estado
        // confirmado por el servidor (no lo forzamos a inactivo).
        estadoPendiente   = estadoEnvioActivo;
        cambiosPendientes = false;
        _aplicarEstadoUI();
        lanzarToast('No se pudieron guardar los cambios', err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('cargando');
            if (textoEl) textoEl.textContent = 'Guardar cambios';
            btn.style.boxShadow = '';
        }
    }
}

// =============================================================================
// ENVÍO DE RESPUESTA — doble validación local + servidor
// =============================================================================
//
// CORREGIDO:
//  - Se usa _obtenerEstadoDesdeServidor() (GET /config-ranking) en vez del
//    endpoint roto `/encuesta/estado` con el campo inexistente `activo`.
//  - Si la verificación con el servidor FALLA (red, timeout, etc.), ya NO
//    se desactiva el estado local. Se informa el error y se detiene el
//    envío de forma segura, pero sin reescribir la configuración persistida.
//  - El estado local solo se pone en false aquí si el servidor CONFIRMA
//    Estado=2, o si el propio backend rechaza el POST /respuesta con
//    bloqueado:true (que también es una confirmación real del servidor).
// =============================================================================

async function enviarRespuestaEncuesta(citaId, preguntaId, respuesta) {

    // 1. Verificación local inmediata (evita una llamada innecesaria si ya
    //    sabemos, por la última sincronización real, que está inactivo).
    if (!estadoEnvioActivo) {
        return {
            ok:        false,
            bloqueado: true,
            error:     'El envío de encuestas está desactivado. Actívalo en Configuración.'
        };
    }

    // 2. Confirmación con el servidor antes de enviar (fuente de verdad real)
    const verificacion = await _obtenerEstadoDesdeServidor();

    if (!verificacion.ok) {
        // Fallo de red/servidor al verificar: NO tocamos estadoEnvioActivo.
        console.error('[enviarRespuestaEncuesta] verificación fallida', verificacion.error);
        return { ok: false, error: 'No se pudo verificar el estado del sistema. Intenta nuevamente.' };
    }

    if (verificacion.estado === 2) {
        // Confirmado por el servidor: sí está inactivo. Ahora sí sincronizamos.
        estadoEnvioActivo = false;
        estadoPendiente   = false;
        cambiosPendientes = false;
        _aplicarEstadoUI();
        return {
            ok:        false,
            bloqueado: true,
            error:     'El envío de encuestas está desactivado.'
        };
    }

    // 3. Envío real
    try {
        const res  = await fetch(`${BASE_URL}/respuesta`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Cita_ID: citaId, Pregunta_ID: preguntaId, Respuesta: respuesta })
        });
        const data = await res.json();

        if (!data.ok) {
            if (data.bloqueado) {
                // El backend confirma explícitamente que está inactivo.
                estadoEnvioActivo = false;
                estadoPendiente   = false;
                cambiosPendientes = false;
                _aplicarEstadoUI();
            }
            return { ok: false, bloqueado: !!data.bloqueado, error: data.error };
        }

        return { ok: true, data: data.data };

    } catch (err) {
        console.error('[enviarRespuestaEncuesta] error de red', err);
        return { ok: false, error: 'Error de red al enviar la encuesta.' };
    }
}

// =============================================================================
// CARGA DEL RANKING
// =============================================================================

async function cargarRanking() {
    const loading   = document.getElementById('ranking-loading');
    const container = document.getElementById('ranking-tabla-container');
    const vacio     = document.getElementById('ranking-vacio');
    const tbody     = document.getElementById('ranking-tbody');

    loading.style.display   = 'flex';
    container.style.display = 'none';
    vacio.style.display     = 'none';

    try {
        const res  = await fetch(`${BASE_URL}/reporte/ranking-especialistas`);
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al obtener el ranking');

        const ranking = data.data;

        const totalEspecialistas = ranking.length;
        const totalEvaluaciones  = ranking.reduce((a, e) => a + e.Total_Evaluaciones, 0);
        const promedioGeneral    = totalEvaluaciones > 0
            ? ranking.reduce((a, e) => a + e.Promedio * e.Total_Evaluaciones, 0) / totalEvaluaciones
            : 0;

        document.getElementById('stat-especialistas').textContent = totalEspecialistas;
        document.getElementById('stat-respondidas').textContent   = totalEvaluaciones;
        document.getElementById('stat-promedio').textContent      = promedioGeneral > 0
            ? promedioGeneral.toFixed(1) + ' ★'
            : '—';

        if (ranking.length === 0) {
            loading.style.display = 'none';
            vacio.style.display   = 'flex';
            return;
        }

        tbody.innerHTML = '';
        ranking.forEach((e, i) => {
            const pos    = i + 1;
            const clase  = pos === 1 ? 'oro' : pos === 2 ? 'plata' : pos === 3 ? 'bronce' : 'otro';
            const pct    = Math.round((e.Promedio / 5) * 100);
            const tr     = document.createElement('tr');
            tr.innerHTML = `
                <td class="pos"><span class="badge-pos ${clase}">${pos}</span></td>
                <td><strong>${e.Nombre_Especialista}</strong></td>
                <td><span class="chip-especialidad">${e.Especialidad || '—'}</span></td>
                <td>
                    <div class="estrellas-celda">
                        ${renderEstrellas(e.Promedio)}
                        <div class="promedio-barra-bg">
                            <div class="promedio-barra-fill" style="width:${pct}%"></div>
                        </div>
                        <span class="promedio-num">${e.Promedio.toFixed(1)}</span>
                    </div>
                </td>
                <td>${e.Total_Evaluaciones}</td>
            `;
            tbody.appendChild(tr);
        });

        loading.style.display   = 'none';
        container.style.display = 'block';

    } catch (err) {
        console.error('[cargarRanking]', err);
        loading.style.display = 'none';
        mostrarMensaje('mensaje-global-ranking', 'error', `⚠️ ${err.message}`);
    }
}

// =============================================================================
// CARGA Y RENDER DE PREGUNTAS
// =============================================================================

async function cargarPreguntas() {
    const loadingEl = document.getElementById('preguntas-loading');
    const listaEl   = document.getElementById('lista-preguntas');

    loadingEl.style.display = 'flex';
    listaEl.innerHTML       = '';

    try {
        const res  = await fetch(`${BASE_URL}/pregunta`);
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al obtener preguntas');

        preguntasCache          = data.data;
        loadingEl.style.display = 'none';
        renderizarPreguntas(preguntasCache);

    } catch (err) {
        console.error('[cargarPreguntas]', err);
        loadingEl.style.display = 'none';
        mostrarMensaje('mensaje-global-config', 'error', `⚠️ ${err.message}`);
    }
}

function renderizarPreguntas(lista) {
    const listaEl = document.getElementById('lista-preguntas');
    listaEl.innerHTML = '';

    if (lista.length === 0) {
        listaEl.innerHTML = '<p style="font-size:13px;color:#94a3b8;margin:8px 0;">No hay preguntas registradas.</p>';
        return;
    }

    lista.forEach(p => {
        const div = document.createElement('div');
        div.className  = 'pregunta-item';
        div.dataset.id = p.ID_Pregunta;
        div.innerHTML  = `
            <span class="pregunta-texto">${p.Texto_Pregunta}</span>
            <div class="pregunta-acciones">
                <button type="button" class="btn-icono editar" title="Editar pregunta"
                        onclick="abrirModalEditar(${p.ID_Pregunta})">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="btn-icono eliminar" title="Eliminar pregunta"
                        onclick="abrirModalConfirmarEliminar(${p.ID_Pregunta})">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </div>
        `;
        listaEl.appendChild(div);
    });
}

// =============================================================================
// CRUD DE PREGUNTAS
// =============================================================================

async function crearPregunta() {
    const inputEl = document.getElementById('input-nueva-pregunta');
    const errEl   = document.getElementById('err-pregunta');
    const texto   = (inputEl.value || '').trim();

    if (!texto) { mostrarError(inputEl, errEl, '⚠️ Escriba el texto de la pregunta.'); return; }
    ocultarError(inputEl, errEl);

    try {
        const res  = await fetch(`${BASE_URL}/pregunta`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Texto_Pregunta: texto, Orden: preguntasCache.length + 1, Activa: 1 })
        });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al crear la pregunta');

        inputEl.value = '';
        lanzarToast('Pregunta agregada', texto.substring(0, 50) + (texto.length > 50 ? '…' : ''));
        await cargarPreguntas();

    } catch (err) {
        console.error('[crearPregunta]', err);
        mostrarMensaje('mensaje-global-config', 'error', `❌ ${err.message}`);
    }
}

function abrirModalEditar(id) {
    const pregunta = preguntasCache.find(p => p.ID_Pregunta === id);
    if (!pregunta) return;

    document.getElementById('modal-pregunta-id').value    = id;
    document.getElementById('modal-texto-pregunta').value = pregunta.Texto_Pregunta;
    ocultarError(
        document.getElementById('modal-texto-pregunta'),
        document.getElementById('err-modal-pregunta')
    );
    document.getElementById('modal-editar').style.display = 'flex';
}

function cerrarModal(event) {
    if (event.target === document.getElementById('modal-editar'))
        document.getElementById('modal-editar').style.display = 'none';
}

function cerrarModalBtn() {
    document.getElementById('modal-editar').style.display = 'none';
}

async function guardarEdicion() {
    const id      = Number(document.getElementById('modal-pregunta-id').value);
    const inputEl = document.getElementById('modal-texto-pregunta');
    const errEl   = document.getElementById('err-modal-pregunta');
    const texto   = (inputEl.value || '').trim();

    if (!texto) { mostrarError(inputEl, errEl, '⚠️ El texto no puede estar vacío.'); return; }
    ocultarError(inputEl, errEl);

    const preguntaActual = preguntasCache.find(p => p.ID_Pregunta === id);
    if (!preguntaActual) {
        mostrarMensaje('mensaje-global-config', 'error', '❌ Pregunta no encontrada en memoria.');
        return;
    }

    try {
        const res  = await fetch(`${BASE_URL}/pregunta/${id}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                Texto_Pregunta: texto,
                Orden:  preguntaActual.Orden,
                Activa: preguntaActual.Activa !== undefined ? preguntaActual.Activa : 1
            })
        });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al actualizar la pregunta');

        preguntaActual.Texto_Pregunta = texto;
        const nodo = document.querySelector(`.pregunta-item[data-id="${id}"] .pregunta-texto`);
        if (nodo) nodo.textContent = texto;
        else renderizarPreguntas(preguntasCache);

        document.getElementById('modal-editar').style.display = 'none';
        lanzarToast('Pregunta actualizada', texto.substring(0, 50) + (texto.length > 50 ? '…' : ''));

    } catch (err) {
        console.error('[guardarEdicion]', err);
        mostrarMensaje('mensaje-global-config', 'error', `❌ ${err.message}`);
    }
}

function abrirModalConfirmarEliminar(id) {
    const idNum    = Number(id);
    const pregunta = preguntasCache.find(p => Number(p.ID_Pregunta) === idNum);
    const recorte  = pregunta
        ? `"${pregunta.Texto_Pregunta.substring(0, 60)}${pregunta.Texto_Pregunta.length > 60 ? '…' : ''}"`
        : `la pregunta #${idNum}`;

    document.getElementById('modal-confirmar-texto').textContent =
        `¿Estás seguro de que deseas eliminar ${recorte}? Esta acción no se puede deshacer.`;

    idPreguntaPendente = idNum;
    document.getElementById('modal-confirmar-eliminar').style.display = 'flex';
}

function cerrarModalConfirmar(event) {
    if (event.target === document.getElementById('modal-confirmar-eliminar')) {
        document.getElementById('modal-confirmar-eliminar').style.display = 'none';
        idPreguntaPendente = null;
    }
}

function cerrarModalConfirmarBtn() {
    document.getElementById('modal-confirmar-eliminar').style.display = 'none';
    idPreguntaPendente = null;
}

async function confirmarEliminar() {
    if (idPreguntaPendente === null) return;

    const id           = idPreguntaPendente;
    const btnConfirmar = document.querySelector('#modal-confirmar-eliminar .btn-eliminar-confirmar');
    if (btnConfirmar) btnConfirmar.disabled = true;

    try {
        const res = await fetch(`${BASE_URL}/pregunta/${id}`, {
            method:  'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        let data = {};
        try { data = await res.json(); } catch (_) { /* vacío */ }

        if (!res.ok || !data.ok)
            throw new Error(data.error || `Error al eliminar la pregunta (HTTP ${res.status}).`);

        preguntasCache = preguntasCache.filter(p => Number(p.ID_Pregunta) !== Number(id));

        const nodo = document.querySelector(`.pregunta-item[data-id="${id}"]`);
        if (nodo) nodo.remove();
        if (preguntasCache.length === 0) renderizarPreguntas(preguntasCache);

        document.getElementById('modal-confirmar-eliminar').style.display = 'none';
        idPreguntaPendente = null;
        lanzarToast('Pregunta eliminada');

    } catch (err) {
        console.error('[confirmarEliminar]', err);
        document.getElementById('modal-confirmar-eliminar').style.display = 'none';
        idPreguntaPendente = null;
        lanzarToast('No se pudo eliminar la pregunta', err.message, 'error');
    } finally {
        if (btnConfirmar) btnConfirmar.disabled = false;
    }
}

// =============================================================================
// INICIALIZACIÓN
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    Promise.all([cargarRanking(), cargarEstadoEnvio()]);

    document.getElementById('modal-texto-pregunta')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') guardarEdicion();
    });

    document.getElementById('input-nueva-pregunta')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') crearPregunta();
    });
});