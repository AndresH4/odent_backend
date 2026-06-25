// === administrador.js ===
'use strict';

// ─── Variables de módulo ─────────────────────────────────────────────────────
let adminData              = {};
let _accionPendienteSimple = '';
let _vistaActualLista      = '';
let _datosListaCache       = [];
let _passwordValidado      = false;

// ─── Utilidades DOM ───────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function mostrarToast(msg) {
    const t = document.getElementById('toast');
    if (t) {
        t.textContent = msg;
        t.classList.add('visible');
        setTimeout(() => t.classList.remove('visible'), 3000);
    } else {
        alert(msg);
    }
}

// ─── Sesión ───────────────────────────────────────────────────────────────────
async function cargarSesion() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) { window.location.replace('/login'); return; }

    const u = JSON.parse(raw);
    if (u.Rol_ID !== 1) { window.location.replace('/login'); return; }

    try {
        const res = await fetch(`/api/usuarios/${u.Usuario_ID}`);
        if (res.ok) {
            const datos = await res.json();
            if (datos && !datos.error) {
                Object.assign(u, datos);
                sessionStorage.setItem('odent_usuario', JSON.stringify(u));
            }
        }
    } catch (e) {
        console.warn('[admin] No se pudo refrescar desde BD:', e);
    }

    const nombre   = `${u.Nombres || ''} ${u.Apellidos || ''}`.trim();
    const inicial  = nombre.charAt(0).toUpperCase() || 'A';
    const tipoDoc  = u.Nombre_Tipo_Documento || u.TipoDocumento || '';
    const numDoc   = u.NumeroDocumento || '';
    const docLabel = tipoDoc ? `${tipoDoc}: ${numDoc}` : (numDoc || '—');

    adminData = { id: u.Usuario_ID, nombre, email: u.Correo || '', tel: u.Telefono || '', inicial, tipoDoc, numDoc, docLabel };

    setText('header-name', nombre);

    const trigIni = document.getElementById('trigger-inicial');
    if (trigIni) trigIni.textContent = inicial;

    const dropIni = document.getElementById('drop-inicial');
    if (dropIni) dropIni.textContent = inicial;

    setText('drop-name',      nombre.toUpperCase());
    setText('drop-email',     u.Correo    || '—');
    setText('drop-tel',       u.Telefono  || '—');
    setText('drop-documento', docLabel);
    setText('drop-doc-badge', numDoc      || '—');

    await actualizarStats();
}

// ─── Reloj ────────────────────────────────────────────────────────────────────
function actualizarReloj() {
    const ahora = new Date();
    const dia   = ahora.getDay();
    const horas = ahora.getHours();
    const mins  = String(ahora.getMinutes()).padStart(2, '0');
    const segs  = String(ahora.getSeconds()).padStart(2, '0');
    const hh    = horas % 12 || 12;
    const ampm  = horas < 12 ? 'A.M.' : 'P.M.';

    const elReloj = document.getElementById('reloj');
    if (elReloj) elReloj.innerText = `${String(hh).padStart(2, '0')}:${mins}:${segs} ${ampm}`;

    const esHorarioLaboral =
        (dia >= 1 && dia <= 5 && horas >= 8 && horas < 18) ||
        (dia === 6 && horas >= 8 && horas < 13);

    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot && txt) {
        dot.className   = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
        txt.innerText   = esHorarioLaboral ? 'Estado: En Jornada' : 'Estado: Fuera de Horario';
        txt.style.color = esHorarioLaboral ? '#10b981' : '#ef4444';
    }
}

// ─── Estadísticas dashboard ───────────────────────────────────────────────────
async function actualizarStats() {
    try {
        const res      = await fetch('/api/usuarios');
        const data     = await res.json();
        const usuarios = Array.isArray(data) ? data : [];
        setText('stat-esp',   usuarios.filter(u => u.Rol_ID === 2).length);
        setText('stat-pac',   usuarios.filter(u => u.Rol_ID === 3).length);
        setText('stat-total', usuarios.length);
    } catch (e) {
        console.error('[admin] Error cargando stats:', e);
    }
}

// ─── Helper de extracción segura de ID por rol ───────────────────────────────
function _extraerId(u, ...claves) {
    for (const k of claves) {
        if (u && u[k] !== undefined && u[k] !== null) return u[k];
    }
    return null;
}

// ─── Especialistas y Pacientes ────────────────────────────────────────────────
async function renderUsuarios(rolNombre) {
    _vistaActualLista = rolNombre;

    try {
        let filas = [];

        if (rolNombre === 'Especialista') {
            const [resEsp, resUsr] = await Promise.all([
                fetch('/api/especialistas'),
                fetch('/api/usuarios'),
            ]);
            const dataEsp = await resEsp.json();
            const dataUsr = await resUsr.json();

            const especialistas = Array.isArray(dataEsp) ? dataEsp : [];
            const usuarios      = Array.isArray(dataUsr) ? dataUsr : [];
            const usrEsp        = usuarios.filter(u => u.Rol_ID === 2);

            const mapaEspecialidad = {};
            especialistas.forEach(e => {
                mapaEspecialidad[(e.NombreCompleto || '').toUpperCase()] = e.Especialidades || '—';
            });

            filas = usrEsp.map(u => ({
                Usuario_ID:      u.Usuario_ID,
                Especialista_ID: _extraerId(u, 'Especialista_ID', 'especialista_id'),
                NombreCompleto:  `${u.Nombres || ''} ${u.Apellidos || ''}`.trim(),
                Correo:          u.Correo   || '—',
                Telefono:        u.Telefono || '—',
                Especialidades:  mapaEspecialidad[`${u.Nombres || ''} ${u.Apellidos || ''}`.trim().toUpperCase()] || '—',
                Estado_ID:       u.Estado_ID,
            }));

        } else if (rolNombre === 'Paciente') {
            const res      = await fetch('/api/usuarios');
            const data     = await res.json();
            const usrPac   = (Array.isArray(data) ? data : []).filter(u => u.Rol_ID === 3);

            filas = usrPac.map(u => ({
                Usuario_ID:     u.Usuario_ID,
                Paciente_ID:    _extraerId(u, 'Paciente_ID', 'paciente_id'),
                NombreCompleto: `${u.Nombres || ''} ${u.Apellidos || ''}`.trim(),
                Correo:         u.Correo   || '—',
                Telefono:       u.Telefono || '—',
                Estado_ID:      u.Estado_ID,
            }));
        }

        _datosListaCache = filas;
        _mostrarListaDinamica(rolNombre, filas, false);

    } catch (e) {
        console.error('[admin] Error cargando usuarios:', e);
    }
}

// ─── Todos los usuarios ───────────────────────────────────────────────────────
async function renderTodosUsuarios() {
    _vistaActualLista = 'Todos';

    try {
        const res  = await fetch('/api/usuarios');
        const data = await res.json();

        let tiposDoc = [];
        try {
            const resT = await fetch('/api/tipos_documento');
            tiposDoc   = resT.ok ? await resT.json() : [];
        } catch (_) {}

        const mapaDoc = {};
        tiposDoc.forEach(t => { mapaDoc[t.TipoDoc_ID] = t.Nombre_Tipo_Documento || ''; });

        const filas = (Array.isArray(data) ? data : []).map(u => ({
            Usuario_ID:      u.Usuario_ID,
            NombreCompleto:  `${u.Nombres || ''} ${u.Apellidos || ''}`.trim(),
            NumeroDocumento: u.NumeroDocumento || '—',
            TipoDoc:         mapaDoc[u.TipoDoc_ID] || '—',
            Telefono:        u.Telefono || '—',
            Correo:          u.Correo   || '—',
            Estado_ID:       u.Estado_ID,
        }));

        _datosListaCache = filas;
        _mostrarListaDinamica('Todos', filas, true);

    } catch (e) {
        console.error('[admin] Error cargando todos los usuarios:', e);
    }
}

// ─── Renderizador base ────────────────────────────────────────────────────────
function _mostrarListaDinamica(tipo, filas, conToggle) {
    const body      = document.getElementById('body-lista-dinamica');
    const cont      = document.getElementById('container-lista-rapida');
    const tit       = document.getElementById('titulo-lista-dinamica');
    const head      = document.getElementById('head-lista-dinamica');
    const buscCont  = document.getElementById('container-buscador-lista');
    const buscInput = document.getElementById('busqueda-lista-dinamica');

    if (!body || !cont || !tit) return;

    if (buscCont)  { buscCont.classList.remove('seccion-oculta'); buscCont.classList.add('seccion-visible'); }
    if (buscInput) buscInput.value = '';

    cont.classList.remove('seccion-oculta');
    cont.classList.add('seccion-visible');

    const titulos = { Especialista: 'ESPECIALISTAS', Paciente: 'PACIENTES', Todos: 'TOTAL REGISTROS' };
    tit.textContent = titulos[tipo] || tipo.toUpperCase();

    if (head) {
        if (tipo === 'Especialista') {
            head.innerHTML = `
                <th class="p-5">ID</th>
                <th class="p-5">Nombre</th>
                <th class="p-5">Especialidad</th>
                <th class="p-5">Correo</th>
                <th class="p-5">Teléfono</th>
                <th class="p-5">Estado</th>`;
        } else if (tipo === 'Paciente') {
            head.innerHTML = `
                <th class="p-5">ID</th>
                <th class="p-5">Nombre</th>
                <th class="p-5">Correo</th>
                <th class="p-5">Teléfono</th>
                <th class="p-5">Estado</th>`;
        } else {
            head.innerHTML = `
                <th class="p-5">ID</th>
                <th class="p-5">Nombre Completo</th>
                <th class="p-5">Tipo Documento</th>
                <th class="p-5">Número Documento</th>
                <th class="p-5">Teléfono</th>
                <th class="p-5">Correo</th>
                <th class="p-5">Estado</th>`;
        }
    }

    _renderFilas(filas, tipo, conToggle);
}

// ─── Pintar filas ─────────────────────────────────────────────────────────────
function _renderFilas(filas, tipo) {
    const body = document.getElementById('body-lista-dinamica');
    const noD  = document.getElementById('no-datos-lista');
    if (!body) return;

    body.innerHTML = '';

    if (filas.length === 0) { noD?.classList.remove('hidden'); return; }
    noD?.classList.add('hidden');

    filas.forEach(u => {
        const tr          = document.createElement('tr');
        tr.className      = 'hover:bg-sky-50/50 transition-all';
        tr.dataset.nombre = (u.NombreCompleto || '').toUpperCase();

        const estadoActivo = u.Estado_ID === 1;
        const badgeEstado  = estadoActivo
            ? '<span class="text-[9px] font-bold uppercase px-2 py-1 rounded-full bg-green-100 text-green-700">Activo</span>'
            : '<span class="text-[9px] font-bold uppercase px-2 py-1 rounded-full bg-red-100 text-red-700">Inactivo</span>';

        if (tipo === 'Especialista') {
            const idEsp = u.Especialista_ID == null ? '—' : `#${u.Especialista_ID}`;
            tr.innerHTML = `
                <td class="p-5 font-black text-slate-500 text-[11px]">${idEsp}</td>
                <td class="p-5 font-black text-slate-800 text-[11px] uppercase">${u.NombreCompleto}</td>
                <td class="p-5 text-[10px] font-bold text-sky-600 uppercase">${u.Especialidades || '—'}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Correo}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Telefono}</td>
                <td class="p-5">${badgeEstado}</td>`;

        } else if (tipo === 'Paciente') {
            const idPac = u.Paciente_ID == null ? '—' : `#${u.Paciente_ID}`;
            tr.innerHTML = `
                <td class="p-5 font-black text-slate-500 text-[11px]">${idPac}</td>
                <td class="p-5 font-black text-slate-800 text-[11px] uppercase">${u.NombreCompleto}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Correo}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Telefono}</td>
                <td class="p-5">${badgeEstado}</td>`;

        } else {
            tr.innerHTML = `
                <td class="p-5 font-black text-slate-500 text-[11px]">#${u.Usuario_ID}</td>
                <td class="p-5 font-black text-slate-800 text-[11px] uppercase">${u.NombreCompleto}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.TipoDoc || '—'}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.NumeroDocumento}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Telefono}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">${u.Correo}</td>
                <td class="p-5">
                    <button
                        onclick="toggleEstadoUsuario(${u.Usuario_ID}, ${u.Estado_ID}, this)"
                        class="text-[9px] font-black uppercase px-3 py-1.5 rounded-full border transition-all
                            ${estadoActivo
                                ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                                : 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200'}">
                        ${estadoActivo ? 'Activo' : 'Inactivo'}
                    </button>
                </td>`;
        }

        body.appendChild(tr);
    });
}

// ─── Toggle estado usuario ────────────────────────────────────────────────────
async function toggleEstadoUsuario(usuarioId, estadoActual, btnEl) {
    const nuevoEstado = estadoActual === 1 ? 2 : 1;
    const nuevoLabel  = nuevoEstado  === 1 ? 'Activo' : 'Inactivo';

    try {
        const res  = await fetch(`/api/usuario/${usuarioId}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ Estado_ID: nuevoEstado }),
        });
        const data = await res.json();

        if (data.ok) {
            btnEl.setAttribute('onclick', `toggleEstadoUsuario(${usuarioId}, ${nuevoEstado}, this)`);
            btnEl.textContent = nuevoLabel;
            btnEl.className   = `text-[9px] font-black uppercase px-3 py-1.5 rounded-full border transition-all
                ${nuevoEstado === 1
                    ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                    : 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200'}`;
            const idx = _datosListaCache.findIndex(u => u.Usuario_ID === usuarioId);
            if (idx !== -1) _datosListaCache[idx].Estado_ID = nuevoEstado;
            await actualizarStats();
        } else {
            alert(`Error: ${data.error || 'No se pudo actualizar el estado.'}`);
        }
    } catch (e) {
        console.error('[admin] Error toggle estado:', e);
        alert('Error de conexión al actualizar estado.');
    }
}

// ─── Filtrar lista dinámica ───────────────────────────────────────────────────
function filtrarListaDinamica() {
    const filtro = (document.getElementById('busqueda-lista-dinamica')?.value || '').toUpperCase();
    document.querySelectorAll('#body-lista-dinamica tr').forEach(fila => {
        fila.style.display = (fila.dataset.nombre || '').toUpperCase().includes(filtro) ? '' : 'none';
    });
}

function ocultarListaRapida() {
    const cont     = document.getElementById('container-lista-rapida');
    const buscCont = document.getElementById('container-buscador-lista');
    cont?.classList.remove('seccion-visible');    cont?.classList.add('seccion-oculta');
    buscCont?.classList.remove('seccion-visible'); buscCont?.classList.add('seccion-oculta');
    _vistaActualLista = '';
    _datosListaCache  = [];
}

// ─── Filtrar historial de citas ───────────────────────────────────────────────
function filtrarTablaCitas() {
    const filtro = (document.getElementById('busqueda-citas')?.value || '').toLowerCase();
    document.querySelectorAll('#tabla-body tr').forEach(fila => {
        fila.style.display = fila.textContent.toLowerCase().includes(filtro) ? '' : 'none';
    });
}

// ─── Historial de citas ───────────────────────────────────────────────────────
async function renderCitas() {
    try {
        const res  = await fetch('/api/citas');
        const data = await res.json();

        const head = document.getElementById('tabla-head');
        const body = document.getElementById('tabla-body');
        const noD  = document.getElementById('no-datos');
        if (!head || !body) return;

        head.innerHTML = `
            <tr>
                <th class="p-6">Paciente</th>
                <th class="p-6">Especialista</th>
                <th class="p-6">Especialidad</th>
                <th class="p-6">Fecha / Hora</th>
                <th class="p-6">Estado</th>
            </tr>`;

        const citas = Array.isArray(data) ? data : [];
        if (citas.length === 0) { noD?.classList.remove('hidden'); body.innerHTML = ''; return; }
        noD?.classList.add('hidden');

        body.innerHTML = citas.map(c => {
            const estado = c.EstadoAgenda || '—';
            const el     = estado.toLowerCase();
            let cls = 'bg-slate-100 text-slate-600';
            if      (el.includes('disponible') || el.includes('pendiente'))                       cls = 'bg-green-100 text-green-700';
            else if (el.includes('ocup') || el.includes('proceso') || el.includes('atend'))       cls = 'bg-sky-100 text-sky-700';
            else if (el.includes('cancel') || el.includes('multa'))                               cls = 'bg-red-100 text-red-700';
            else if (el.includes('cumplid') || el.includes('finaliz'))                            cls = 'bg-emerald-100 text-emerald-700';

            return `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="p-6 font-bold text-slate-800 text-[11px] uppercase">${c.NombrePaciente || '—'}</td>
                <td class="p-6 text-[10px] font-black text-slate-600 uppercase">
                    <i class="fas fa-user-md mr-2 text-sky-500"></i>${c.NombreEspecialista || '—'}
                </td>
                <td class="p-6 text-sky-600 font-black text-[10px] uppercase">${c.Nombre_Especialidad || '—'}</td>
                <td class="p-6 text-[10px] font-bold">${c.Fecha || '—'}<br><span class="text-slate-400">${c.Hora_Inicio || ''}</span></td>
                <td class="p-6">
                    <span class="text-[9px] font-black uppercase px-2 py-1 rounded-full ${cls}">${estado}</span>
                </td>
            </tr>`;
        }).join('');

    } catch (e) {
        console.error('[admin] Error cargando citas:', e);
    }
}

// ─── Multas ───────────────────────────────────────────────────────────────────
async function renderMultas() {
    try {
        const res    = await fetch('/api/multas');
        const json   = await res.json();
        const multas = json.ok ? json.data : (Array.isArray(json) ? json : []);

        const head     = document.getElementById('tabla-head');
        const body     = document.getElementById('tabla-body');
        const noD      = document.getElementById('no-datos');
        const filtroEl = document.getElementById('busqueda-multas');
        if (!head || !body) return;

        filtroEl?.closest('.filtro-multas-wrapper')?.classList.remove('hidden');

        head.innerHTML = `
            <tr>
                <th class="p-5">ID Multa</th>
                <th class="p-5">Paciente</th>
                <th class="p-5">Doc. Identidad</th>
                <th class="p-5">Concepto</th>
                <th class="p-5">Fecha Cita</th>
                <th class="p-5 text-center">Estado</th>
                <th class="p-5 text-center">Acción</th>
            </tr>`;

        if (multas.length === 0) { noD?.classList.remove('hidden'); body.innerHTML = ''; return; }
        noD?.classList.add('hidden');

        body.innerHTML = multas.map(m => {
            const esPagada  = m.EstadoMulta_ID === 2 || (m.EstadoMulta || '').toLowerCase() === 'pagada';
            const badgeCls  = esPagada
                ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                : 'bg-amber-100 text-amber-700 border border-amber-200';
            const badgeIcon = esPagada ? 'fa-circle-check' : 'fa-clock';
            const tipoDoc   = m.Nombre_Tipo_Documento ? `${m.Nombre_Tipo_Documento}: ` : '';

            return `
            <tr class="hover:bg-slate-50/70 transition-colors" data-nombre="${(m.NombrePaciente || '').toUpperCase()}">
                <td class="p-5 font-black text-slate-500 text-[11px]">#${m.Multa_ID}</td>
                <td class="p-5 font-black text-slate-800 text-[11px] uppercase">${m.NombrePaciente || '—'}</td>
                <td class="p-5 text-[10px] font-bold text-slate-500">${tipoDoc}${m.NumeroDocumento || '—'}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600 uppercase">${m.Concepto || '—'}</td>
                <td class="p-5 text-[10px] font-bold text-slate-600">
                    ${m.Fecha || '—'}<br>
                    <span class="text-slate-400">${m.Hora_Inicio || ''}</span>
                </td>
                <td class="p-5 text-center">
                    <span class="inline-flex items-center gap-1.5 text-[9px] font-black uppercase px-3 py-1.5 rounded-full ${badgeCls}">
                        <i class="fas ${badgeIcon} text-[10px]"></i>
                        ${m.EstadoMulta || '—'}
                    </span>
                </td>
                <td class="p-5 text-center">
                    ${!esPagada
                        ? `<button
                               onclick="pagarMulta(${m.Multa_ID}, this)"
                               class="inline-flex items-center gap-2 text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-4 py-2 rounded-xl font-black hover:bg-emerald-100 transition-all uppercase active:scale-95">
                               <i class="fas fa-check"></i> Marcar Pagada
                           </button>`
                        : '<span class="text-slate-300 text-[10px] font-bold italic">— Pagada —</span>'}
                </td>
            </tr>`;
        }).join('');

    } catch (e) {
        console.error('[admin] Error cargando multas:', e);
    }
}

// ─── Filtrar tabla de multas ──────────────────────────────────────────────────
function filtrarTablaMultas() {
    const filtro = (document.getElementById('busqueda-multas')?.value || '').toUpperCase();
    document.querySelectorAll('#tabla-body tr').forEach(fila => {
        fila.style.display = (fila.dataset.nombre || '').toUpperCase().includes(filtro) ? '' : 'none';
    });
}

// ─── Pagar multa ──────────────────────────────────────────────────────────────
async function pagarMulta(multaId, btnEl) {
    try {
        const res  = await fetch(`/api/multas/${multaId}/pagar`, { method: 'PUT' });
        const data = await res.json();

        if (data.ok) {
            mostrarToast(`Multa #${multaId} marcada como Pagada.`);
            const tr = btnEl.closest('tr');
            if (tr) {
                const badgeTd  = tr.querySelector('td:nth-child(6)');
                const accionTd = tr.querySelector('td:nth-child(7)');
                if (badgeTd)  badgeTd.innerHTML  = `
                    <span class="inline-flex items-center gap-1.5 text-[9px] font-black uppercase px-3 py-1.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
                        <i class="fas fa-circle-check text-[10px]"></i> Pagada
                    </span>`;
                if (accionTd) accionTd.innerHTML = '<span class="text-slate-300 text-[10px] font-bold italic">— Pagada —</span>';
            }
        } else {
            alert(`Error: ${data.error || 'No se pudo marcar como pagada.'}`);
        }
    } catch (e) {
        console.error('[admin] Error pagando multa:', e);
        alert('Error de conexión al procesar la multa.');
    }
}

// ─── Navegación ───────────────────────────────────────────────────────────────
function cambiarSeccion(sec) {
    ['sec-dashboard', 'sec-citas', 'sec-multas', 'sec-config'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.classList.remove('seccion-visible'); el.classList.add('seccion-oculta'); }
    });
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const filtroWrapper = document.getElementById('filtro-multas-wrapper');
    if (filtroWrapper) filtroWrapper.classList.add('hidden');

    const secEl = document.getElementById(`sec-${sec}`);
    const btnEl = document.getElementById(`btn-${sec}`);
    if (secEl) { secEl.classList.remove('seccion-oculta'); secEl.classList.add('seccion-visible'); }
    if (btnEl) btnEl.classList.add('active');

    const titles = { dashboard: 'Administrador', citas: 'Historial de Citas', multas: 'Gestión de Multas', config: 'Mi Perfil' };
    const mainTitle = document.getElementById('main-title');
    if (mainTitle) mainTitle.textContent = titles[sec] || 'Administrador';

    if (sec === 'citas')  renderCitas();
    if (sec === 'multas') renderMultas();
    if (sec === 'config') _precargarPerfilAdmin();
}

// ─── Dropdown de perfil ───────────────────────────────────────────────────────
function toggleProfileDropdown() {
    document.getElementById('profile-dropdown')?.classList.toggle('show');
}

window.addEventListener('click', e => {
    const trig = document.getElementById('profile-trigger');
    const drop = document.getElementById('profile-dropdown');
    if (trig && drop && !trig.contains(e.target) && !drop.contains(e.target)) {
        drop.classList.remove('show');
    }
});

// ─── Perfil admin — precarga ──────────────────────────────────────────────────
function _precargarPerfilAdmin() {
    const el = id => document.getElementById(id);
    if (el('edit-nombre')) el('edit-nombre').value = adminData.nombre || '';
    if (el('edit-email'))  el('edit-email').value  = adminData.email  || '';
    if (el('edit-tel'))    el('edit-tel').value    = adminData.tel    || '';
    _resetearPasswordAdmin();
}

function _resetearPasswordAdmin() {
    ['pass-actual', 'conf-pass-nueva', 'conf-pass-confirmar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.value = ''; el.type = 'password'; }
    });
    document.querySelectorAll('.pass-toggle-btn i').forEach(icon => {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    });
    const step1 = document.getElementById('pass-step1');
    const step2 = document.getElementById('pass-step2');
    if (step1) step1.style.display = '';
    if (step2) step2.style.display = 'none';
    ['error-pass-actual', 'error-pass-nueva'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    ['req-length', 'req-upper', 'req-lower', 'req-number', 'req-special'].forEach(id => {
        _aplicarEstadoRequisito(id, false, false);
    });
    _passwordValidado = false;
}

// ─── Toggle visibilidad de contraseña ────────────────────────────────────────
window.togglePassVisibility = function (inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon?.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon?.classList.replace('fa-eye-slash', 'fa-eye');
    }
};

// ─── Requisitos de contraseña ─────────────────────────────────────────────────
function _cumpleRequisitos(pass) {
    return {
        length:  pass.length >= 8,
        upper:   /[A-Z]/.test(pass),
        lower:   /[a-z]/.test(pass),
        number:  /[0-9]/.test(pass),
        special: /[^A-Za-z0-9]/.test(pass),
    };
}

window.validarRequisitosEnTiempoReal = function () {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitos(pass);
    _aplicarEstadoRequisito('req-length',  res.length,  false);
    _aplicarEstadoRequisito('req-upper',   res.upper,   false);
    _aplicarEstadoRequisito('req-lower',   res.lower,   false);
    _aplicarEstadoRequisito('req-number',  res.number,  false);
    _aplicarEstadoRequisito('req-special', res.special, false);
};

function _aplicarEstadoRequisito(id, cumple, marcarRojo) {
    const el = document.getElementById(id);
    if (!el) return;
    const icon = el.querySelector('.req-icon');
    if (cumple) {
        el.className = 'req-item req-ok';
        if (icon) icon.textContent = '✓';
    } else if (marcarRojo) {
        el.className = 'req-item req-error';
        if (icon) icon.textContent = '-';
    } else {
        el.className = 'req-item req-pending';
        if (icon) icon.textContent = '-';
    }
}

function _marcarRequisitosIncumplidos() {
    const pass = document.getElementById('conf-pass-nueva')?.value || '';
    const res  = _cumpleRequisitos(pass);
    _aplicarEstadoRequisito('req-length',  res.length,  !res.length);
    _aplicarEstadoRequisito('req-upper',   res.upper,   !res.upper);
    _aplicarEstadoRequisito('req-lower',   res.lower,   !res.lower);
    _aplicarEstadoRequisito('req-number',  res.number,  !res.number);
    _aplicarEstadoRequisito('req-special', res.special, !res.special);
    return res.length && res.upper && res.lower && res.number && res.special;
}

// ─── Validar contraseña actual (paso 1) ──────────────────────────────────────
window.validarPasswordActual = function () {
    const inputActual = document.getElementById('pass-actual');
    const errActual   = document.getElementById('error-pass-actual');
    const step1       = document.getElementById('pass-step1');
    const step2       = document.getElementById('pass-step2');

    if (!inputActual?.value.trim()) {
        if (errActual) { errActual.textContent = 'Ingresa tu contraseña actual.'; errActual.style.display = 'block'; }
        return;
    }

    fetch('/api/usuarios/verificar-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ usuario_id: adminData.id, contrasena_actual: inputActual.value }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            if (errActual) errActual.style.display = 'none';
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = '';
            _passwordValidado = true;
        } else {
            document.getElementById('modalErrorPassword').style.display = 'flex';
            _passwordValidado = false;
        }
    })
    .catch(() => {
        if (errActual) { errActual.textContent = 'Error de conexión.'; errActual.style.display = 'block'; }
    });
};

// ─── Guardar perfil completo ──────────────────────────────────────────────────
window.guardarPerfilCompleto = async function () {
    const nombre     = (document.getElementById('edit-nombre')?.value || '').trim();
    const email      = (document.getElementById('edit-email')?.value  || '').trim();
    const tel        = (document.getElementById('edit-tel')?.value    || '').trim();
    const passActual = document.getElementById('pass-actual')?.value           || '';
    const passNueva  = document.getElementById('conf-pass-nueva')?.value       || '';
    const passConf   = document.getElementById('conf-pass-confirmar')?.value   || '';
    const errNueva   = document.getElementById('error-pass-nueva');
    const step2      = document.getElementById('pass-step2');

    const cambiandoPassword = step2?.style.display !== 'none' && !!passNueva;

    if (cambiandoPassword) {
        const todosOk = _marcarRequisitosIncumplidos();
        if (!todosOk) return;
        if (passNueva !== passConf) {
            if (errNueva) { errNueva.textContent = 'Las contraseñas no coinciden.'; errNueva.style.display = 'block'; }
            return;
        }
        if (errNueva) errNueva.style.display = 'none';

        try {
            const res  = await fetch('/api/usuarios/cambiar-password', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    usuario_id:           adminData.id,
                    contrasena_actual:    passActual,
                    contrasena_nueva:     passNueva,
                    contrasena_confirmar: passConf,
                }),
            });
            const data = await res.json();
            if (!data.ok) {
                if (errNueva) { errNueva.textContent = data.error || 'No se pudo actualizar la contraseña.'; errNueva.style.display = 'block'; }
                return;
            }
        } catch {
            if (errNueva) { errNueva.textContent = 'Error de conexión.'; errNueva.style.display = 'block'; }
            return;
        }
    }

    if (nombre || email || tel) {
        const partes    = (nombre || '').split(/\s+/);
        const mitad     = Math.ceil(partes.length / 2);
        const nombres   = partes.slice(0, mitad).join(' ');
        const apellidos = partes.slice(mitad).join(' ');

        try {
            const res  = await fetch(`/api/usuarios/${adminData.id}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    Nombres:          nombres,
                    Apellidos:        apellidos,
                    Correo:           email,
                    Telefono:         tel,
                    ContrasenaActual: passActual || '_skip_',
                }),
            });
            const data = await res.json();
            if (!data.ok && res.status !== 401) {
                alert(`Error al guardar: ${data.error || 'No se pudo actualizar.'}`);
                return;
            }
        } catch {
            alert('Error de conexión al guardar perfil.');
            return;
        }
    }

    const raw = sessionStorage.getItem('odent_usuario');
    if (raw) {
        const u      = JSON.parse(raw);
        const partes = (nombre || '').split(/\s+/);
        const mitad  = Math.ceil(partes.length / 2);
        if (nombre) { u.Nombres = partes.slice(0, mitad).join(' '); u.Apellidos = partes.slice(mitad).join(' '); }
        if (email)  u.Correo   = email;
        if (tel)    u.Telefono = tel;
        sessionStorage.setItem('odent_usuario', JSON.stringify(u));
    }

    adminData = { ...adminData, nombre, email, tel };
    await cargarSesion();
    cambiarSeccion('dashboard');
    mostrarToast('Perfil actualizado correctamente.');
};

// ─── Modal confirmación simple ────────────────────────────────────────────────
window.mostrarConfirmacionSimple = function (mensaje, accion) {
    _accionPendienteSimple = accion;
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');
    if (texto) texto.textContent = mensaje;
    if (modal) modal.style.display = 'flex';
};

window.cerrarModalSimple = function () {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
    _accionPendienteSimple = '';
};

window.ejecutarAccionSimple = function () {
    if (_accionPendienteSimple === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
    window.cerrarModalSimple();
};

const cerrarSesion = () => window.mostrarConfirmacionSimple('¿Quiere salir de la sesión?', 'salir');

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    setInterval(actualizarReloj, 1000);
    actualizarReloj();

    const fechaEl = document.getElementById('fecha-actual');
    if (fechaEl) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }).toUpperCase();
    }

    cargarSesion();
    cambiarSeccion('dashboard');
});