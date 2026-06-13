/**
 * especialista.js — Stylo Dental Pro v2.5
 * =========================================
 * CORRECCIONES vs. versión anterior:
 *
 * 1. cambiarSeccion(): reemplaza classList.toggle('hidden') de Tailwind
 *    por classList.toggle('seccion-oculta') / classList.toggle('seccion-visible')
 *    para que las animaciones CSS no sean bloqueadas por display:none !important.
 *
 * 2. cargarDatosEspecialista(): reemplaza classList.toggle('hidden', ...)
 *    por gestión de clase 'visible' en #no-datos.
 *
 * 3. filtrarTabla(): mismo cambio en #no-datos.
 *
 * 4. toggleProfileDropdown(): ya usaba classList.toggle('show') → correcto,
 *    se mantiene igual.
 *
 * 5. cerrarSesion(): migrada de localStorage a sessionStorage para consistencia
 *    con el resto del proyecto (session.js).
 *
 * 6. cargarInfoSesion(): migrada de localStorage a sessionStorage.
 *
 * La lógica de negocio, cálculos y estructura de datos NO cambian.
 */
 
'use strict';
 
let indexActualGlobal = null;
let historialTotal    = [];
let seccionActiva     = 'agenda';
 
/* =====================================================================
   UTILIDAD: mostrar/ocultar elementos SIN usar 'hidden' de Tailwind
   ===================================================================== */
 
/**
 * Muestra un elemento usando la clase 'seccion-visible' (definida en el CSS).
 * Para el grid de stats funciona porque el CSS lo sobreescribe a display:grid.
 */
function mostrarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-oculta');
    el.classList.add('seccion-visible');
}
 
/**
 * Oculta un elemento usando 'seccion-oculta' (display:none en CSS propio,
 * NO con la clase 'hidden' de Tailwind que lleva !important y bloquea animaciones).
 */
function ocultarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-visible');
    el.classList.add('seccion-oculta');
}
 
/* =====================================================================
   GESTIÓN DE UI
   ===================================================================== */
 
const toggleProfileDropdown = () => {
    const dp = document.getElementById('profile-dropdown');
    if (dp) dp.classList.toggle('show');
};
 
window.onclick = (e) => {
    const trig = document.getElementById('profile-trigger');
    const drop = document.getElementById('profile-dropdown');
    if (trig && drop && !trig.contains(e.target) && !drop.contains(e.target)) {
        drop.classList.remove('show');
    }
};
 
const actualizarRelojYEstado = () => {
    const ahora = new Date();
    const horas = ahora.getHours();
    const dia   = ahora.getDay();
    const relojElem = document.getElementById('reloj');
 
    if (relojElem) {
        relojElem.innerText = ahora.toLocaleTimeString('es-CO', {
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        });
    }
 
    const esHorarioLaboral =
        (dia >= 1 && dia <= 5 && horas >= 8 && horas < 18) ||
        (dia === 6 && horas >= 8 && horas < 13);
 
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
 
    if (dot && txt) {
        dot.className = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
        txt.innerText = esHorarioLaboral ? 'Estado: En Jornada' : 'Estado: Fuera de Horario';
        txt.style.color = esHorarioLaboral ? '#10b981' : '#ef4444';
    }
};
 
/* =====================================================================
   SESIÓN
   ===================================================================== */
 
const cargarInfoSesion = () => {
    // Migrado de localStorage → sessionStorage para consistencia con session.js
    const raw = sessionStorage.getItem('odent_usuario');
    const user = raw ? JSON.parse(raw) : null;
 
    // Fallback a localStorage por compatibilidad con el flujo anterior
    const correoLogueado = localStorage.getItem('usuario_logueado');
    const dbUsuarios     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const userLegacy     = dbUsuarios[correoLogueado];
 
    const u = user || (userLegacy && userLegacy.rol === 'Especialista' ? userLegacy : null);
 
    if (!u) {
        window.location.replace('/login');
        return;
    }
 
    // Normalizar campos (sessionStorage usa Nombres/Apellidos; localStorage usaba nombre/apellidos)
    const nombreCompleto = u.Nombres
        ? `${u.Nombres} ${u.Apellidos || ''}`.trim()
        : `${u.nombre || ''} ${u.apellidos || ''}`.trim();
 
    const inicial       = nombreCompleto.charAt(0).toUpperCase();
    const especialidad  = u.Especialidad || u.especialidad || 'No asignada';
    const correo        = u.Correo       || u.correo       || '';
    const telefono      = u.Telefono     || u.celular      || 'No asignado';
 
    const displays = {
        'doctor-nombre-display': nombreCompleto,
        'doctor-avatar':         inicial,
        'avatar-grande':         inicial,
        'nombre-menu':           `Dr. ${nombreCompleto}`,
        'esp-menu':              especialidad,
        'email-menu':            correo,
        'tel-menu':              telefono,
        'conf-nombre':           nombreCompleto,
        'conf-email':            correo,
        'conf-tel':              telefono,
        'esp-1':                 especialidad
    };
 
    Object.entries(displays).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) {
            (el.tagName === 'INPUT' || el.tagName === 'SELECT')
                ? el.value     = val
                : el.innerText = val;
        }
    });
};
 
/* =====================================================================
   CARGA DE DATOS
   ===================================================================== */
 
const cargarDatosEspecialista = () => {
    historialTotal = JSON.parse(localStorage.getItem('historialCompleto')) || [];
    const tbody    = document.getElementById('tabla-especialista');
    if (!tbody) return;
 
    tbody.innerHTML = '';
    let stats = { atendidos: 0, pendientes: 0, proxima: '--:--' };
 
    const hoyCitas = historialTotal.filter(c =>
        !c.estado.toLowerCase().includes('cancelada')
    );
 
    hoyCitas.forEach((cita) => {
        const esAtendido = (cita.estado === 'Atendido');
        esAtendido ? stats.atendidos++ : stats.pendientes++;
 
        if (!esAtendido && stats.proxima === '--:--') stats.proxima = cita.hora;
 
        const mostrarFila =
            seccionActiva === 'agenda' ||
            (seccionActiva === 'pacientes' && esAtendido);
 
        if (mostrarFila) {
            const idxReal = historialTotal.indexOf(cita);
            const row     = document.createElement('tr');
            row.className = `transition-all duration-300 ${esAtendido ? 'bg-slate-50/50 opacity-80' : 'hover:bg-sky-50/30'}`;
            row.innerHTML = `
                <td class="p-8">
                    <p class="font-black text-slate-800 text-base">${cita.hora}</p>
                    <p class="text-[10px] text-slate-400 font-bold uppercase mt-1">${cita.fecha || 'Hoy'}</p>
                </td>
                <td class="p-8">
                    <p class="font-black text-slate-700 uppercase text-xs tracking-tight">${cita.nombre}</p>
                    <p class="text-[11px] text-slate-400 font-bold mt-1">${cita.tipoDoc}: ${cita.numDoc}</p>
                </td>
                <td class="p-8 font-black text-sky-600 uppercase text-[11px] tracking-widest">${cita.especialidad}</td>
                <td class="p-8">
                    <span class="${esAtendido ? 'status-atendido' : 'status-pendiente'} uppercase">
                        <i class="fas ${esAtendido ? 'fa-check-circle' : 'fa-clock'} mr-2"></i>
                        ${cita.estado}
                    </span>
                </td>
                <td class="p-8 text-right">
                    ${!esAtendido
                        ? `<button onclick="abrirModuloConsulta(${idxReal})" class="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black text-[10px] hover:bg-sky-600 transition-all uppercase shadow-lg btn-action">Atender</button>`
                        : `<button onclick="verReporteProfesional(${idxReal})" class="text-sky-600 bg-sky-50 hover:bg-sky-100 w-14 h-14 rounded-2xl transition-all shadow-sm active:scale-95 flex items-center justify-center mx-auto"><i class="fas fa-file-medical text-2xl"></i></button>`
                    }
                </td>`;
            tbody.appendChild(row);
        }
    });
 
    // Stats
    const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.innerText = val; };
    setEl('stat-total',     hoyCitas.length);
    setEl('stat-pendientes', stats.pendientes);
    setEl('stat-atendidos',  stats.atendidos);
    setEl('stat-proxima',    stats.proxima);
 
    // CORRECCIÓN: usamos clase 'visible' en vez de quitar 'hidden' de Tailwind
    const noDatos = document.getElementById('no-datos');
    if (noDatos) {
        if (tbody.children.length > 0) {
            noDatos.classList.remove('visible');
        } else {
            noDatos.classList.add('visible');
        }
    }
};
 
/* =====================================================================
   NAVEGACIÓN — CORRECCIÓN PRINCIPAL
   Antes: element.classList.toggle('hidden', condicion)
   Ahora: mostrarSeccion() / ocultarSeccion() → sin conflicto con Tailwind
   ===================================================================== */
 
const cambiarSeccion = (nombreSeccion) => {
    seccionActiva = nombreSeccion;
 
    const config = {
        agenda:    { title: 'Agenda Médica',    table: 'Pacientes del Día',      stats: true  },
        pacientes: { title: 'Mis Pacientes',    table: 'Archivo de Atenciones',  stats: false },
        config:    { title: 'Mi Perfil',        table: '',                        stats: false }
    };
 
    const current = config[nombreSeccion];
    if (!current) return;
 
    // Stats
    current.stats ? mostrarSeccion('contenedor-stats') : ocultarSeccion('contenedor-stats');
 
    // Secciones de contenido
    if (nombreSeccion === 'config') {
        ocultarSeccion('sec-tabla');
        mostrarSeccion('sec-config');
    } else {
        mostrarSeccion('sec-tabla');
        ocultarSeccion('sec-config');
    }
 
    // Títulos
    const mainTitle = document.getElementById('main-title');
    if (mainTitle) mainTitle.innerText = current.title;
 
    const tabTitle = document.getElementById('tabla-titulo');
    if (tabTitle) tabTitle.innerText = current.table;
 
    // Botones de nav
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.id === `btn-${nombreSeccion}`);
    });
 
    cargarDatosEspecialista();
};
 
/* =====================================================================
   MÓDULO DE CONSULTA CLÍNICA — lógica de negocio sin cambios
   ===================================================================== */
 
const abrirModuloConsulta = (indice) => {
    indexActualGlobal = indice;
    const cita = historialTotal[indice];
    localStorage.setItem('pacienteActivoDoc', cita.numDoc);
 
    const fields = {
        'paciente-nombre-modal': cita.nombre,
        'paciente-doc-modal':    `${cita.tipoDoc} ID: ${cita.numDoc}`,
        'nota-clinica':          cita.evolucion   || '',
        'receta-clinica':        cita.prescripcion || '',
        'diag-clinica':          cita.cie10        || ''
    };
 
    Object.entries(fields).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) {
            (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')
                ? el.value     = val
                : el.innerText = val;
        }
    });
 
    document.getElementById('modalConsulta').style.display = 'flex';
};
 
const finalizarAtencion = () => {
    const notaC = document.getElementById('nota-clinica').value.trim();
    const diagC = document.getElementById('diag-clinica').value.trim();
 
    if (!notaC || !diagC) {
        alert('⚠️ Registro incompleto: Debe ingresar la evolución y el diagnóstico clínico.');
        return;
    }
 
    const citaActual = historialTotal[indexActualGlobal];
    Object.assign(citaActual, {
        estado:       'Atendido',
        evolucion:    notaC,
        cie10:        diagC,
        prescripcion: document.getElementById('receta-clinica').value.trim(),
        fechaAtencion: new Date().toLocaleString('es-CO')
    });
 
    // Guardar en historia clínica
    let historiaClinica = JSON.parse(localStorage.getItem('historia_clinica')) || [];
    historiaClinica.push({
        numDoc:      citaActual.numDoc,
        nombre:      citaActual.nombre,
        fecha:       new Date().toLocaleString('es-CO'),
        diagnostico: citaActual.cie10,
        evolucion:   citaActual.evolucion,
        tratamiento: citaActual.prescripcion
    });
    localStorage.setItem('historia_clinica', JSON.stringify(historiaClinica));
    localStorage.setItem('historialCompleto', JSON.stringify(historialTotal));
 
    cerrarConsulta();
    alert('✅ Atención registrada con éxito.');
    cargarDatosEspecialista();
};
 
const verReporteProfesional = (indice) => {
    const cita = historialTotal[indice];
    const mapping = {
        'rep-paciente':       cita.nombre,
        'rep-fecha-atencion': `Finalizado el ${cita.fechaAtencion || 'N/A'}`,
        'rep-diagnostico':    cita.cie10        || 'No codificado',
        'rep-evolucion':      cita.evolucion    || 'Sin registro',
        'rep-prescripcion':   cita.prescripcion || 'Sin prescripción'
    };
 
    Object.entries(mapping).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    });
 
    document.getElementById('modalReporte').style.display = 'flex';
};
 
/* =====================================================================
   FILTRO DE TABLA
   ===================================================================== */
 
const filtrarTabla = () => {
    const query = document.getElementById('busqueda-paciente').value.toLowerCase();
    const filas = document.getElementById('tabla-especialista').getElementsByTagName('tr');
    let visibles = 0;
 
    Array.from(filas).forEach(fila => {
        const coincide = fila.innerText.toLowerCase().includes(query);
        fila.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
 
    // CORRECCIÓN: clase 'visible' en vez de quitar 'hidden' de Tailwind
    const noDatos = document.getElementById('no-datos');
    if (noDatos) {
        visibles > 0
            ? noDatos.classList.remove('visible')
            : noDatos.classList.add('visible');
    }
};
 
/* =====================================================================
   PERFIL — lógica sin cambios
   ===================================================================== */
 
const guardarPerfilCompleto = () => {
    const correoActual = localStorage.getItem('usuario_logueado');
    const database     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const nuevoCorreo  = document.getElementById('conf-email').value.trim();
    const nuevaPass    = document.getElementById('conf-pass').value;
 
    if (database[correoActual]) {
        const nombreFull    = document.getElementById('conf-nombre').value.trim();
        const [nombre, ...apellidos] = nombreFull.split(' ');
 
        const userRef        = database[correoActual];
        userRef.nombre       = nombre;
        userRef.apellidos    = apellidos.join(' ');
        userRef.especialidad = document.getElementById('esp-1').value;
        userRef.celular      = document.getElementById('conf-tel').value;
        userRef.correo       = nuevoCorreo;
 
        if (nuevaPass && nuevaPass.length >= 4) userRef.password = nuevaPass;
 
        if (nuevoCorreo !== correoActual) {
            database[nuevoCorreo] = userRef;
            delete database[correoActual];
            localStorage.setItem('usuario_logueado', nuevoCorreo);
        }
 
        localStorage.setItem('usuarios_dental', JSON.stringify(database));
        alert('✨ Perfil actualizado correctamente.');
        cargarInfoSesion();
        cambiarSeccion('agenda');
    }
};
 
/* =====================================================================
   UTILIDADES
   ===================================================================== */
 
const cerrarConsulta    = () => document.getElementById('modalConsulta').style.display = 'none';
const irAHistoriaClinica = () => window.location.href = '/historia_clinica.html';
const irAOdontograma    = () => window.location.href = '/odontograma.html';
 
const cerrarSesion = () => {
    if (confirm('¿Finalizar turno de especialista?')) {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
};
 
/* =====================================================================
   INICIALIZACIÓN
   ===================================================================== */
 
window.onload = () => {
    cargarInfoSesion();
    setInterval(actualizarRelojYEstado, 1000);
    actualizarRelojYEstado();
    cargarDatosEspecialista();
 
    const fechaStr = new Date().toLocaleDateString('es-CO', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    const fechaEl = document.getElementById('fecha-actual');
    if (fechaEl) fechaEl.innerText = fechaStr;
};
 