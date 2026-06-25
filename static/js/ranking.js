// =============================================================================
// ranking.js
// Módulo de Ranking de Satisfacción — los ESPECIALISTAS son los calificados,
// los PACIENTES son los calificantes.
// =============================================================================

const BASE_URL = '/api';

// ---------------------------------------------------------------------------
// ESTADO LOCAL
// ---------------------------------------------------------------------------
let estadoEnvioActivo  = true;
let preguntasCache     = [];
let idPreguntaPendente = null;

// ---------------------------------------------------------------------------
// HELPERS DE MENSAJES
// ---------------------------------------------------------------------------
function mostrarMensaje(elId, tipo, texto) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.className = tipo === 'exito' ? 'exito' : 'error';
    el.textContent = texto;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}

function lanzarToast(texto) {
    const toast = document.getElementById('toast-ranking');
    if (!toast) return;
    toast.textContent = texto;
    toast.className = 'toast-ranking show';
    setTimeout(() => { toast.className = 'toast-ranking'; }, 2600);
}

function mostrarError(inputEl, errEl, msg) {
    if (inputEl) inputEl.classList.add('input-error');
    if (errEl)   { errEl.textContent = msg; errEl.style.display = 'block'; }
}

function ocultarError(inputEl, errEl) {
    if (inputEl) inputEl.classList.remove('input-error');
    if (errEl)   errEl.style.display = 'none';
}

// ---------------------------------------------------------------------------
// RENDERIZADO DE ESTRELLAS
// ---------------------------------------------------------------------------
function renderEstrellas(promedio) {
    let html = '<div class="estrellas-display">';
    for (let i = 1; i <= 5; i++) {
        if (promedio >= i) {
            html += '<span class="star llena">★</span>';
        } else if (promedio >= i - 0.5) {
            html += '<span class="star media">★</span>';
        } else {
            html += '<span class="star">★</span>';
        }
    }
    html += '</div>';
    return html;
}

// ---------------------------------------------------------------------------
// NAVEGACIÓN ENTRE VISTAS
// ---------------------------------------------------------------------------
function mostrarConfig() {
    document.getElementById('rankingView').style.display = 'none';
    document.getElementById('configView').style.display  = 'block';
    cargarPreguntas();
}

function volverRanking() {
    document.getElementById('configView').style.display  = 'none';
    document.getElementById('rankingView').style.display = 'block';
    cargarRanking();
}

// ---------------------------------------------------------------------------
// TOGGLE DE ESTADO DE ENVÍO AUTOMÁTICO
// ---------------------------------------------------------------------------
function toggleEstado() {
    estadoEnvioActivo = !estadoEnvioActivo;
    const btn   = document.getElementById('btn-toggle-estado');
    const label = document.getElementById('toggle-label-text');
    if (estadoEnvioActivo) {
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

// ---------------------------------------------------------------------------
// CARGA DEL RANKING — GET /api/reporte/ranking-especialistas
// ---------------------------------------------------------------------------
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
        const totalEvaluaciones  = ranking.reduce((acc, e) => acc + e.Total_Evaluaciones, 0);
        const promedioGeneral    = totalEvaluaciones > 0
            ? (ranking.reduce((acc, e) => acc + e.Promedio * e.Total_Evaluaciones, 0) / totalEvaluaciones)
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
            const clases = pos === 1 ? 'oro' : pos === 2 ? 'plata' : pos === 3 ? 'bronce' : 'otro';
            const pct    = Math.round((e.Promedio / 5) * 100);
            const tr     = document.createElement('tr');
            tr.innerHTML = `
                <td class="pos">
                    <span class="badge-pos ${clases}">${pos}</span>
                </td>
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

// ---------------------------------------------------------------------------
// CARGA DE PREGUNTAS — GET /api/pregunta
// ---------------------------------------------------------------------------
async function cargarPreguntas() {
    const loadingEl = document.getElementById('preguntas-loading');
    const listaEl   = document.getElementById('lista-preguntas');

    loadingEl.style.display = 'flex';
    listaEl.innerHTML       = '';

    try {
        const res  = await fetch(`${BASE_URL}/pregunta`);
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al obtener preguntas');

        preguntasCache = data.data;
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
        listaEl.innerHTML = '<p style="font-size:13px; color:#94a3b8; margin:8px 0;">No hay preguntas registradas.</p>';
        return;
    }

    lista.forEach(p => {
        const div = document.createElement('div');
        div.className  = 'pregunta-item';
        div.dataset.id = p.ID_Pregunta;
        div.innerHTML  = `
            <span class="pregunta-texto">${p.Texto_Pregunta}</span>
            <div class="pregunta-acciones">
                <button class="btn-icono editar" title="Editar pregunta" onclick="abrirModalEditar(${p.ID_Pregunta})">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button class="btn-icono eliminar" title="Eliminar pregunta" onclick="abrirModalConfirmarEliminar(${p.ID_Pregunta})">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </div>
        `;
        listaEl.appendChild(div);
    });
}

// ---------------------------------------------------------------------------
// CREAR PREGUNTA — POST /api/pregunta
// ---------------------------------------------------------------------------
async function crearPregunta() {
    const inputEl = document.getElementById('input-nueva-pregunta');
    const errEl   = document.getElementById('err-pregunta');
    const texto   = (inputEl.value || '').trim();

    if (!texto) {
        mostrarError(inputEl, errEl, '⚠️ Escriba el texto de la pregunta.');
        return;
    }
    ocultarError(inputEl, errEl);

    const orden = preguntasCache.length + 1;

    try {
        const res  = await fetch(`${BASE_URL}/pregunta`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Texto_Pregunta: texto, Orden: orden, Activa: 1 })
        });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al crear la pregunta');

        inputEl.value = '';
        lanzarToast('✅ Pregunta agregada correctamente');
        await cargarPreguntas();

    } catch (err) {
        console.error('[crearPregunta]', err);
        mostrarMensaje('mensaje-global-config', 'error', `❌ ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// MODAL DE EDICIÓN
// ---------------------------------------------------------------------------
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
    if (event.target === document.getElementById('modal-editar')) {
        document.getElementById('modal-editar').style.display = 'none';
    }
}

function cerrarModalBtn() {
    document.getElementById('modal-editar').style.display = 'none';
}

// ---------------------------------------------------------------------------
// GUARDAR EDICIÓN — PUT /api/pregunta/<id>
// ---------------------------------------------------------------------------
async function guardarEdicion() {
    const id      = Number(document.getElementById('modal-pregunta-id').value);
    const inputEl = document.getElementById('modal-texto-pregunta');
    const errEl   = document.getElementById('err-modal-pregunta');
    const texto   = (inputEl.value || '').trim();

    if (!texto) {
        mostrarError(inputEl, errEl, '⚠️ El texto no puede estar vacío.');
        return;
    }
    ocultarError(inputEl, errEl);

    const preguntaActual = preguntasCache.find(p => p.ID_Pregunta === id);
    const orden = preguntaActual ? preguntaActual.Orden : null;

    try {
        const res  = await fetch(`${BASE_URL}/pregunta/${id}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Texto_Pregunta: texto, Orden: orden, Activa: 1 })
        });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al actualizar la pregunta');

        document.getElementById('modal-editar').style.display = 'none';
        lanzarToast('✅ Pregunta actualizada correctamente');
        await cargarPreguntas();

    } catch (err) {
        console.error('[guardarEdicion]', err);
        mostrarMensaje('mensaje-global-config', 'error', `❌ ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// MODAL DE CONFIRMACIÓN DE ELIMINACIÓN
// ---------------------------------------------------------------------------
function abrirModalConfirmarEliminar(id) {
    const pregunta = preguntasCache.find(p => p.ID_Pregunta === id);
    const textoCorto = pregunta
        ? `"${pregunta.Texto_Pregunta.substring(0, 60)}${pregunta.Texto_Pregunta.length > 60 ? '...' : ''}"`
        : `la pregunta #${id}`;

    document.getElementById('modal-confirmar-texto').textContent =
        `¿Estás seguro de que deseas eliminar ${textoCorto}? Esta acción no se puede deshacer.`;

    idPreguntaPendente = id;
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

    const id = idPreguntaPendente;
    document.getElementById('modal-confirmar-eliminar').style.display = 'none';
    idPreguntaPendente = null;

    try {
        const res  = await fetch(`${BASE_URL}/pregunta/${id}`, { method: 'DELETE' });
        const data = await res.json();

        if (!data.ok) throw new Error(data.error || 'Error al eliminar la pregunta');

        lanzarToast('🗑️ Pregunta eliminada');
        await cargarPreguntas();

    } catch (err) {
        console.error('[confirmarEliminar]', err);
        mostrarMensaje('mensaje-global-config', 'error', `❌ ${err.message}`);
    }
}

// ---------------------------------------------------------------------------
// INICIALIZACIÓN
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    cargarRanking();

    const modalInput = document.getElementById('modal-texto-pregunta');
    if (modalInput) {
        modalInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') guardarEdicion();
        });
    }

    const nuevaInput = document.getElementById('input-nueva-pregunta');
    if (nuevaInput) {
        nuevaInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') crearPregunta();
        });
    }
});