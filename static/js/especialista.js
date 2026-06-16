/**
 * especialista.js — Stylo Dental Pro v2.5  [CORREGIDO]
 * =====================================================
 * ERRORES CORREGIDOS EN ESTA VERSIÓN:
 *
 * ERROR 1 (CRÍTICO) — Línea 153 del original:
 *   La función cargarInfoSesion() se cerraba con }; en la línea 153,
 *   pero DESPUÉS de ese cierre apareció código suelto:
 *       }; 'conf-nombre'; nombreCompleto,
 *   Esto es un SyntaxError que rompe TODO el script (nada se ejecuta).
 *   FIX: Se movió 'conf-nombre' DENTRO del objeto displays, antes del cierre.
 *
 * ERROR 2 (CRÍTICO) — Líneas 213-256 del original:
 *   Dentro de cargarDatosEspecialista() la llave de cierre } aparecía
 *   en la línea 221, pero el bloque de actualización de stats (setEl, noDatos)
 *   quedó FUERA de la función → ReferenceError en tiempo de ejecución porque
 *   hoyCitas y tbody no existen en el scope global.
 *   Además ese bloque estaba DUPLICADO (líneas 223-237 y 241-255).
 *   FIX: Se eliminó el cierre prematuro, se unificó el bloque de stats,
 *   y se cerró la función en el lugar correcto.
 *
 * ERROR 3 (MEDIO) — mostrarConfirmacionSimple / cerrarModalSimple:
 *   Usaban classList.add/remove('hidden') de Tailwind en el modal
 *   #modalConfirmarSimple. Pero el CSS del proyecto define .modal-overlay
 *   con display:none y .modal-overlay.flex con display:flex.
 *   Usar 'hidden' de Tailwind interfiere porque Tailwind lo define como
 *   display:none !important, bloqueando el .flex del CSS propio.
 *   FIX: Se reemplazó classList('hidden/flex') por style.display directo,
 *   igual que todos los demás modales del proyecto.
 *
 * ERROR 4 (MEDIO) — cerrarSesion() duplicada:
 *   Existían DOS implementaciones: una con confirm() nativo (línea 506)
 *   y otra con mostrarConfirmacionSimple (línea 532). El botón del sidebar
 *   llamaba a mostrarConfirmacionSimple pero el dropdown llamaba a cerrarSesion().
 *   FIX: cerrarSesion() ahora delega en mostrarConfirmacionSimple para
 *   mantener el diseño consistente con el resto de la UI.
 *
 * ERROR 5 (LEVE) — Botón "Cerrar Sesión" del sidebar (HTML, línea 49):
 *   class="..." era literal, no había clases reales.
 *   FIX: Documentado aquí; el HTML corregido lo incluye.
 *
 * CÓDIGO DUPLICADO ELIMINADO:
 *   - Bloque setEl() / noDatos duplicado (líneas 240-255 del original).
 *   - Función cerrarSesion con confirm() nativo (ya no se necesita).
 */
 
'use strict';
 
let indexActualGlobal = null;
let historialTotal    = [];
let seccionActiva     = 'agenda';
 
/* =====================================================================
   UTILIDAD: mostrar/ocultar secciones SIN usar 'hidden' de Tailwind
   ===================================================================== */
 
function mostrarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-oculta');
    el.classList.add('seccion-visible');
}
 
function ocultarSeccion(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('seccion-visible');
    el.classList.add('seccion-oculta');
}
 
/* =====================================================================
   GESTIÓN DE UI — dropdown de perfil
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
 
/* =====================================================================
   RELOJ Y ESTADO LABORAL
   ===================================================================== */
 
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
        dot.className  = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
        txt.innerText  = esHorarioLaboral ? 'Estado: En Jornada' : 'Estado: Fuera de Horario';
        txt.style.color = esHorarioLaboral ? '#10b981' : '#ef4444';
    }
};
 
/* =====================================================================
   SESIÓN
   ===================================================================== */
 
const cargarInfoSesion = () => {
    const raw  = sessionStorage.getItem('odent_usuario');
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
 
    const nombreCompleto = u.Nombres
        ? `${u.Nombres} ${u.Apellidos || ''}`.trim()
        : `${u.nombre || ''} ${u.apellidos || ''}`.trim();
 
    const inicial      = nombreCompleto.charAt(0).toUpperCase();
    const especialidad = u.Especialidad || u.especialidad || 'No asignada';
    const correo       = u.Correo       || u.correo       || '';
    const telefono     = u.Telefono     || u.celular      || 'No asignado';
 
    // ── FIX ERROR 1 ──────────────────────────────────────────────────
    // 'conf-nombre' estaba fuera del objeto (después del cierre de la
    // función) con sintaxis inválida: }; 'conf-nombre'; nombreCompleto,
    // Se incorpora aquí dentro como entrada válida del objeto.
    // ─────────────────────────────────────────────────────────────────
    const displays = {
        'doctor-nombre-display': nombreCompleto,
        'doctor-avatar':         inicial,
        'avatar-grande':         inicial,
        'nombre-menu':           `Dr. ${nombreCompleto}`,
        'esp-menu':              especialidad,
        'email-menu':            correo,
        'tel-menu':              telefono,
        'conf-nombre':           nombreCompleto,   // ← CORREGIDO (antes flotaba fuera)
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
};   // ← cierre real de cargarInfoSesion
 
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
        c && c.estado && !c.estado.toLowerCase().includes('cancelada')
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
 
    // ── FIX ERROR 2 ──────────────────────────────────────────────────
    // Este bloque estaba FUERA de la función (después de la llave 221)
    // Y DUPLICADO (aparecía dos veces). Se unifica aquí dentro, antes
    // del cierre real de cargarDatosEspecialista().
    // ─────────────────────────────────────────────────────────────────
    const setEl = (id, val) => {
        const e = document.getElementById(id);
        if (e) e.innerText = val;
    };
    setEl('stat-total',      hoyCitas.length);
    setEl('stat-pendientes', stats.pendientes);
    setEl('stat-atendidos',  stats.atendidos);
    setEl('stat-proxima',    stats.proxima);
 
    // Control del aviso "sin datos"
    const noDatos = document.getElementById('no-datos');
    if (noDatos) {
        tbody.children.length > 0
            ? noDatos.classList.remove('visible')
            : noDatos.classList.add('visible');
    }
};   // ← cierre real de cargarDatosEspecialista
 
/* =====================================================================
   NAVEGACIÓN ENTRE SECCIONES
   ===================================================================== */
 
const cambiarSeccion = (nombreSeccion) => {
    seccionActiva = nombreSeccion;

    // Cerrar dropdown si está abierto
    const dpMenu = document.getElementById('profile-dropdown');
    if (dpMenu) dpMenu.classList.remove('show');

    const config = {
        agenda:    { title: 'Agenda Médica',  table: 'Pacientes del Día',     stats: true  },
        pacientes: { title: 'Mis Pacientes',  table: 'Archivo de Atenciones', stats: false },
        config:    { title: 'Mi Perfil',      table: '',                       stats: false }
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
    if (tabTitle && current.table) tabTitle.innerText = current.table;

    // Botones de nav (btn-config ahora existe en el HTML)
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.id === `btn-${nombreSeccion}`);
    });

    cargarDatosEspecialista();
};
 
/* =====================================================================
   MÓDULO DE CONSULTA CLÍNICA
   ===================================================================== */
 
const abrirModuloConsulta = (indice) => {
    indexActualGlobal = indice;
    const cita = historialTotal[indice];
    localStorage.setItem('pacienteActivoDoc', cita.numDoc);
 
    const fields = {
        'paciente-nombre-modal': cita.nombre,
        'paciente-doc-modal':    `${cita.tipoDoc} ID: ${cita.numDoc}`,
        'nota-clinica':          cita.evolucion    || '',
        'receta-clinica':        cita.prescripcion || '',
        'diag-clinica':          cita.cie10         || ''
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
        estado:        'Atendido',
        evolucion:     notaC,
        cie10:         diagC,
        prescripcion:  document.getElementById('receta-clinica').value.trim(),
        fechaAtencion: new Date().toLocaleString('es-CO')
    });
 
    let historiaClinica = JSON.parse(localStorage.getItem('historia_clinica')) || [];
    historiaClinica.push({
        numDoc:      citaActual.numDoc,
        nombre:      citaActual.nombre,
        fecha:       new Date().toLocaleString('es-CO'),
        diagnostico: citaActual.cie10,
        evolucion:   citaActual.evolucion,
        tratamiento: citaActual.prescripcion
    });
    localStorage.setItem('historia_clinica',  JSON.stringify(historiaClinica));
    localStorage.setItem('historialCompleto', JSON.stringify(historialTotal));
 
    cerrarConsulta();
    alert('✅ Atención registrada con éxito.');
    cargarDatosEspecialista();
};
 
/* =====================================================================
   REPORTE PROFESIONAL
   ===================================================================== */
 
const verReporteProfesional = (indice) => {
    const cita    = historialTotal[indice];
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
    const query  = document.getElementById('busqueda-paciente').value.toLowerCase();
    const filas  = document.getElementById('tabla-especialista').getElementsByTagName('tr');
    let visibles = 0;
 
    Array.from(filas).forEach(fila => {
        const coincide = fila.innerText.toLowerCase().includes(query);
        fila.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
 
    const noDatos = document.getElementById('no-datos');
    if (noDatos) {
        visibles > 0
            ? noDatos.classList.remove('visible')
            : noDatos.classList.add('visible');
    }
};
 
/* =====================================================================
   PERFIL — CAMBIO DE CONTRASEÑA EN DOS PASOS
   ===================================================================== */
 
const validarPasswordActual = () => {
    const correoActual = localStorage.getItem('usuario_logueado');
    const database     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const userRef      = database[correoActual];
 
    const inputActual = document.getElementById('pass-actual');
    const errorActual = document.getElementById('error-pass-actual');
    const step2       = document.getElementById('pass-step2');
    const passGuardada = userRef ? userRef.password : undefined;
 
    if (!userRef || inputActual.value !== passGuardada) {
        errorActual.style.display = 'block';
        return;
    }
 
    errorActual.style.display = 'none';
    inputActual.disabled = true;
    step2.style.display  = 'grid';
};
 
const guardarPerfilCompleto = () => {
    const correoActual = localStorage.getItem('usuario_logueado');
    const database     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const nuevoCorreo  = document.getElementById('conf-email').value.trim();
 
    const step2       = document.getElementById('pass-step2');
    const errorNueva  = document.getElementById('error-pass-nueva');
    let nuevaPassFinal = null;
 
    if (step2 && step2.style.display === 'grid') {
        const passNueva     = document.getElementById('conf-pass-nueva').value;
        const passConfirmar = document.getElementById('conf-pass-confirmar').value;
 
        if (passNueva || passConfirmar) {
            if (passNueva !== passConfirmar) {
                errorNueva.innerText     = 'Las contraseñas no coinciden.';
                errorNueva.style.display = 'block';
                return;
            }
            if (passNueva.length < 4) {
                errorNueva.innerText     = 'La nueva contraseña debe tener mínimo 4 caracteres.';
                errorNueva.style.display = 'block';
                return;
            }
            nuevaPassFinal = passNueva;
        }
        errorNueva.style.display = 'none';
    }
 
    if (database[correoActual]) {
        const nombreFull = document.getElementById('conf-nombre').value.trim();
        const [nombre, ...apellidos] = nombreFull.split(' ');
 
        const userRef        = database[correoActual];
        userRef.nombre       = nombre;
        userRef.apellidos    = apellidos.join(' ');
        userRef.especialidad = document.getElementById('esp-1').value;
        userRef.celular      = document.getElementById('conf-tel').value;
        userRef.correo       = nuevoCorreo;
 
        if (nuevaPassFinal) userRef.password = nuevaPassFinal;
 
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
   UTILIDADES — MODALES Y NAVEGACIÓN
   ===================================================================== */
 
const cerrarConsulta     = () => { document.getElementById('modalConsulta').style.display  = 'none'; };
const irAHistoriaClinica = () => { window.location.href = '/historia_clinica.html'; };
const irAOdontograma     = () => { window.location.href = '/odontograma.html'; };
 
/* =====================================================================
   CONFIRMACIÓN SIMPLE (CERRAR SESIÓN, LIMPIAR, ETC.)
   ──────────────────────────────────────────────────
   FIX ERROR 3: Se reemplaza classList.add/remove('hidden'/'flex')
   por style.display = 'flex'/'none', igual que todos los demás modales
   del proyecto. Usar 'hidden' de Tailwind aquí bloqueaba la apertura
   del modal porque Tailwind lo define con display:none !important,
   prevaleciendo sobre la clase .flex del CSS propio.
 
   FIX ERROR 4: cerrarSesion() ahora delega en mostrarConfirmacionSimple
   para que el diseño del diálogo sea coherente con la UI. Se eliminó
   la versión con confirm() nativo que coexistía en el original.
   ===================================================================== */
 
let accionPendienteSimple = '';
 
function mostrarConfirmacionSimple(mensaje, accion) {
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');
 
    if (modal && texto) {
        texto.innerText = mensaje;
        accionPendienteSimple = accion;
        modal.style.display = 'flex';       // ← FIX: antes usaba classList('flex')
    }
}
 
function cerrarModalSimple() {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none'; // ← FIX: antes usaba classList('hidden')
    accionPendienteSimple = '';
}
 
function ejecutarAccionSimple() {
    if (accionPendienteSimple === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');  // ruta unificada con el resto del proyecto
    }
    cerrarModalSimple();
}
 
// cerrarSesion() es llamada desde el dropdown → ahora usa el modal de diseño propio
const cerrarSesion = () => mostrarConfirmacionSimple('¿Finalizar turno de especialista?', 'salir');
 
/* =====================================================================
   INICIALIZACIÓN
   ===================================================================== */
 
window.onload = () => {
    // Estado inicial correcto: tabla visible, config oculta
    const secTabla  = document.getElementById('sec-tabla');
    const secConfig = document.getElementById('sec-config');
    if (secTabla)  { secTabla.classList.remove('seccion-oculta');  secTabla.classList.add('seccion-visible'); }
    if (secConfig) { secConfig.classList.remove('seccion-visible'); secConfig.classList.add('seccion-oculta'); }

    cargarInfoSesion();
    setInterval(actualizarRelojYEstado, 1000);
    actualizarRelojYEstado();
    cargarDatosEspecialista();

    const fechaEl = document.getElementById('fecha-actual');
    if (fechaEl) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }
};