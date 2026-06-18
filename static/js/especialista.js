/**
 * especialista.js — Stylo Dental Pro v2.7 [INTEGRACIÓN BACKEND EPS + PACIENTE]
 */

'use strict';

let indexActualGlobal = null;
let historialTotal    = [];
let seccionActiva     = 'agenda';

/* =====================================================================
   UTILIDAD: mostrar/ocultar secciones
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
        dot.className   = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
        txt.innerText   = esHorarioLaboral ? 'Estado: En Jornada' : 'Estado: Fuera de Horario';
        txt.style.color = esHorarioLaboral ? '#10b981' : '#ef4444';
    }
};

/* =====================================================================
   SESIÓN
   ===================================================================== */

let usuarioSesionActual = null;

const cargarInfoSesion = () => {
    const raw  = sessionStorage.getItem('odent_usuario');
    const user = raw ? JSON.parse(raw) : null;
    const correoLogueado = localStorage.getItem('usuario_logueado');
    const dbUsuarios      = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const userLegacy      = dbUsuarios[correoLogueado];

    const u = user || (userLegacy && userLegacy.rol === 'Especialista' ? userLegacy : null);

    if (!u) {
        window.location.replace('/login');
        return;
    }

    usuarioSesionActual = u;

    const nombreCompleto = u.Nombres
        ? `${u.Nombres} ${u.Apellidos || ''}`.trim()
        : `${u.nombre || ''} ${u.apellidos || ''}`.trim();

    const inicial      = nombreCompleto.charAt(0).toUpperCase();
    const especialidad = u.Especialidad || u.especialidad || 'No asignada';
    const correo       = u.Correo       || u.correo       || '';
    const telefono     = u.Telefono     || u.celular      || 'No asignado';

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

    const setEl = (id, val) => {
        const e = document.getElementById(id);
        if (e) e.innerText = val;
    };
    setEl('stat-total',      hoyCitas.length);
    setEl('stat-pendientes', stats.pendientes);
    setEl('stat-atendidos',  stats.atendidos);
    setEl('stat-proxima',    stats.proxima);

    const noDatos = document.getElementById('no-datos');
    if (noDatos) {
        tbody.children.length > 0
            ? noDatos.classList.remove('visible')
            : noDatos.classList.add('visible');
    }
};

/* =====================================================================
   CARGA DE DATOS CLÍNICOS DEL PACIENTE DESDE BACKEND (EPS + CLÍNICO)
   ===================================================================== */

const cargarPerfilClinicoPaciente = async (numDoc) => {
    // Panel de EPS en el modal de consulta
    const panelEPS = document.getElementById('panel-eps-paciente');
    if (panelEPS) {
        panelEPS.innerHTML = `
            <div class="flex items-center gap-3 text-slate-400 text-xs font-bold">
                <i class="fas fa-spinner fa-spin"></i> Cargando datos de aseguramiento...
            </div>`;
    }

    try {
        // 1. Buscar paciente por documento en el backend
        const respPac = await fetch('/eps/paciente', { method: 'GET' });
        let pacienteBackend = null;
        let pacienteId = null;

        if (respPac.ok) {
            const dataPac = await respPac.json();
            pacienteBackend = (dataPac.data || []).find(
                p => String(p.Correo).toLowerCase().includes(numDoc.toLowerCase()) ||
                     String(p.ID_Usuario) === String(numDoc) ||
                     (p.Nombre_Completo && p.Nombre_Completo.toUpperCase().includes(numDoc.toUpperCase()))
            );
            if (pacienteBackend) pacienteId = pacienteBackend.ID_Paciente;
        }

        // 2. Buscar afiliación EPS por numDoc como búsqueda aproximada
        const respAfil = await fetch('/eps/afiliacion', { method: 'GET' });
        let afiliacion = null;

        if (respAfil.ok) {
            const dataAfil = await respAfil.json();
            // Intentar match por nombre o por usuario_id si el paciente fue encontrado
            if (pacienteBackend) {
                afiliacion = (dataAfil.data || []).find(
                    a => String(a.ID_Usuario) === String(pacienteBackend.ID_Usuario)
                );
            }
        }

        // 3. Renderizar panel EPS
        if (panelEPS) {
            if (afiliacion) {
                panelEPS.innerHTML = `
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div class="bg-white rounded-2xl p-4 border border-sky-100">
                            <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">EPS</p>
                            <p class="font-black text-sky-700 text-sm">${afiliacion.Nombre_EPS || '---'}</p>
                        </div>
                        <div class="bg-white rounded-2xl p-4 border border-sky-100">
                            <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Régimen</p>
                            <p class="font-black text-slate-700 text-sm">${afiliacion.Regimen || '---'}</p>
                        </div>
                        <div class="bg-white rounded-2xl p-4 border border-sky-100">
                            <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">N° Afiliado</p>
                            <p class="font-black text-slate-700 text-sm">${afiliacion.Numero_Afiliado || '---'}</p>
                        </div>
                        <div class="bg-white rounded-2xl p-4 border border-sky-100">
                            <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Estado</p>
                            <p class="font-black ${afiliacion.Estado === 'Activo' ? 'text-emerald-600' : 'text-amber-600'} text-sm">${afiliacion.Estado || '---'}</p>
                        </div>
                    </div>`;
            } else {
                panelEPS.innerHTML = `
                    <div class="flex items-center gap-3 text-slate-400 text-xs font-bold italic">
                        <i class="fas fa-info-circle text-slate-300"></i> Sin afiliación EPS registrada en el sistema.
                    </div>`;
            }
        }

        // 4. Rellenar datos clínicos si existen
        if (pacienteBackend) {
            const camposClinicos = {
                'modal-genero':          pacienteBackend.Genero          || '---',
                'modal-grupo-sanguineo': pacienteBackend.Grupo_Sanguineo || '---',
                'modal-alergias':        pacienteBackend.Alergias        || 'Ninguna registrada',
                'modal-antecedentes':    pacienteBackend.Antecedentes    || 'Ninguno registrado',
                'modal-observaciones':   pacienteBackend.Observaciones   || '---',
            };
            Object.entries(camposClinicos).forEach(([id, val]) => {
                const el = document.getElementById(id);
                if (el) el.innerText = val;
            });
        }

        // 5. Cargar respuestas del formulario clínico si hay ID de paciente
        if (pacienteId) {
            await cargarRespuestasFormulario(pacienteId);
        }

    } catch (err) {
        console.error('[Especialista] Error al cargar perfil clínico:', err);
        if (panelEPS) {
            panelEPS.innerHTML = `
                <div class="flex items-center gap-3 text-red-400 text-xs font-bold">
                    <i class="fas fa-exclamation-circle"></i> Error al cargar datos de aseguramiento.
                </div>`;
        }
    }
};

/* =====================================================================
   CARGA DE RESPUESTAS DEL FORMULARIO CLÍNICO (ANAMNESIS)
   ===================================================================== */

const cargarRespuestasFormulario = async (pacienteId) => {
    const contenedor = document.getElementById('panel-anamnesis');
    if (!contenedor) return;

    try {
        const resp = await fetch(`/eps/reporte/respuestas-paciente/${pacienteId}`, { method: 'GET' });
        if (!resp.ok) {
            contenedor.innerHTML = '';
            return;
        }
        const data = await resp.json();
        if (!data.ok || !data.data || data.data.length === 0) {
            contenedor.innerHTML = `<p class="text-xs text-slate-400 font-bold italic">Sin formulario de anamnesis registrado.</p>`;
            return;
        }

        contenedor.innerHTML = data.data.map(item => `
            <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">${item.Texto_Pregunta || ''}</p>
                <p class="font-bold text-slate-700 text-sm">${item.Texto_Respuesta || '---'}</p>
            </div>
        `).join('');
    } catch (err) {
        console.warn('[Anamnesis] Error al cargar respuestas:', err);
    }
};

/* =====================================================================
   NAVEGACIÓN ENTRE SECCIONES
   ===================================================================== */

const cambiarSeccion = (nombreSeccion) => {
    seccionActiva = nombreSeccion;

    const dpMenu = document.getElementById('profile-dropdown');
    if (dpMenu) dpMenu.classList.remove('show');

    const config = {
        agenda:    { title: 'Agenda Médica',  table: 'Pacientes del Día',     stats: true  },
        pacientes: { title: 'Mis Pacientes',  table: 'Archivo de Atenciones', stats: false },
        config:    { title: 'Mi Perfil',      table: '',                       stats: false }
    };

    const current = config[nombreSeccion];
    if (!current) return;

    current.stats ? mostrarSeccion('contenedor-stats') : ocultarSeccion('contenedor-stats');

    if (nombreSeccion === 'config') {
        ocultarSeccion('sec-tabla');
        mostrarSeccion('sec-config');
        resetFormularioPassword();
    } else {
        mostrarSeccion('sec-tabla');
        ocultarSeccion('sec-config');
    }

    const mainTitle = document.getElementById('main-title');
    if (mainTitle) mainTitle.innerText = current.title;

    const tabTitle = document.getElementById('tabla-titulo');
    if (tabTitle && current.table) tabTitle.innerText = current.table;

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

    // Limpiar datos clínicos previos
    const camposClinicos = ['modal-genero', 'modal-grupo-sanguineo', 'modal-alergias', 'modal-antecedentes', 'modal-observaciones'];
    camposClinicos.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerText = '---';
    });

    document.getElementById('modalConsulta').style.display = 'flex';

    // Cargar perfil clínico y EPS del paciente desde el backend
    cargarPerfilClinicoPaciente(cita.numDoc);
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
   PERFIL — CAMBIO DE CONTRASEÑA EN DOS PASOS (SEGURO, VÍA BACKEND)
   ===================================================================== */

const obtenerUsuarioIdSesion = () => {
    if (!usuarioSesionActual) return null;
    return usuarioSesionActual.Usuario_ID || usuarioSesionActual.usuario_id || null;
};

const resetFormularioPassword = () => {
    const inputActual  = document.getElementById('pass-actual');
    const errorActual  = document.getElementById('error-pass-actual');
    const step2        = document.getElementById('pass-step2');
    const errorNueva   = document.getElementById('error-pass-nueva');
    const passNueva    = document.getElementById('conf-pass-nueva');
    const passConfirm  = document.getElementById('conf-pass-confirmar');

    if (inputActual) { inputActual.value = ''; inputActual.disabled = false; }
    if (errorActual) errorActual.style.display = 'none';
    if (step2)       step2.style.display = 'none';
    if (errorNueva)  errorNueva.style.display = 'none';
    if (passNueva)   passNueva.value = '';
    if (passConfirm) passConfirm.value = '';
};

const validarPasswordActual = async () => {
    const usuarioId   = obtenerUsuarioIdSesion();
    const inputActual = document.getElementById('pass-actual');
    const errorActual = document.getElementById('error-pass-actual');
    const step2       = document.getElementById('pass-step2');

    if (!usuarioId) {
        errorActual.innerText     = 'No se pudo identificar la sesión actual. Vuelve a iniciar sesión.';
        errorActual.style.display = 'block';
        return;
    }

    const contrasenaActual = inputActual.value;
    if (!contrasenaActual) {
        errorActual.innerText     = 'Ingresa tu contraseña actual.';
        errorActual.style.display = 'block';
        return;
    }

    try {
        const resp = await fetch('/usuarios/verificar-password', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                usuario_id:        usuarioId,
                contrasena_actual: contrasenaActual
            })
        });

        const data = await resp.json();

        if (!resp.ok || !data.ok) {
            errorActual.innerText     = data.error || 'Contraseña incorrecta';
            errorActual.style.display = 'block';
            return;
        }

        errorActual.style.display = 'none';
        inputActual.disabled = true;
        step2.style.display  = 'grid';

    } catch (err) {
        errorActual.innerText     = 'Error de conexión al verificar la contraseña. Intenta de nuevo.';
        errorActual.style.display = 'block';
    }
};

const guardarPerfilCompleto = async () => {
    const usuarioId  = obtenerUsuarioIdSesion();
    const step2      = document.getElementById('pass-step2');
    const errorNueva = document.getElementById('error-pass-nueva');

    const cambioPasswordSolicitado = step2 && step2.style.display === 'grid';

    if (cambioPasswordSolicitado) {
        const contrasenaActual = document.getElementById('pass-actual').value;
        const passNueva        = document.getElementById('conf-pass-nueva').value;
        const passConfirmar    = document.getElementById('conf-pass-confirmar').value;

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

            errorNueva.style.display = 'none';

            try {
                const resp = await fetch('/usuarios/cambiar-password', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({
                        usuario_id:            usuarioId,
                        contrasena_actual:     contrasenaActual,
                        contrasena_nueva:      passNueva,
                        contrasena_confirmar:  passConfirmar
                    })
                });

                const data = await resp.json();

                if (!resp.ok || !data.ok) {
                    errorNueva.innerText     = data.error || 'No se pudo actualizar la contraseña.';
                    errorNueva.style.display = 'block';
                    return;
                }

            } catch (err) {
                errorNueva.innerText     = 'Error de conexión al actualizar la contraseña.';
                errorNueva.style.display = 'block';
                return;
            }
        }
    }

    const correoActual = localStorage.getItem('usuario_logueado');
    const database     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const nuevoCorreo  = document.getElementById('conf-email').value.trim();

    if (database[correoActual]) {
        const nombreFull = document.getElementById('conf-nombre').value.trim();
        const [nombre, ...apellidos] = nombreFull.split(' ');

        const userRef        = database[correoActual];
        userRef.nombre       = nombre;
        userRef.apellidos    = apellidos.join(' ');
        userRef.especialidad = document.getElementById('esp-1').value;
        userRef.celular      = document.getElementById('conf-tel').value;
        userRef.correo       = nuevoCorreo;

        if (nuevoCorreo !== correoActual) {
            database[nuevoCorreo] = userRef;
            delete database[correoActual];
            localStorage.setItem('usuario_logueado', nuevoCorreo);
        }

        localStorage.setItem('usuarios_dental', JSON.stringify(database));
    }

    // Actualizar sessionStorage con nuevos datos
    if (usuarioSesionActual) {
        const nombreFull = document.getElementById('conf-nombre').value.trim();
        const partes = nombreFull.split(' ');
        usuarioSesionActual.Nombres    = partes[0] || usuarioSesionActual.Nombres;
        usuarioSesionActual.Apellidos  = partes.slice(1).join(' ') || usuarioSesionActual.Apellidos;
        usuarioSesionActual.Correo     = nuevoCorreo;
        usuarioSesionActual.Telefono   = document.getElementById('conf-tel').value;
        usuarioSesionActual.Especialidad = document.getElementById('esp-1').value;
        sessionStorage.setItem('odent_usuario', JSON.stringify(usuarioSesionActual));
    }

    alert('✨ Perfil actualizado correctamente.');
    cargarInfoSesion();
    cambiarSeccion('agenda');
};

/* =====================================================================
   UTILIDADES — MODALES Y NAVEGACIÓN
   ===================================================================== */

const cerrarConsulta     = () => { document.getElementById('modalConsulta').style.display  = 'none'; };
const irAHistoriaClinica = () => { window.location.href = '/historia_clinica.html'; };
const irAOdontograma     = () => { window.location.href = '/odontograma.html'; };

/* =====================================================================
   CONFIRMACIÓN SIMPLE (CERRAR SESIÓN, LIMPIAR, ETC.)
   ===================================================================== */

let accionPendienteSimple = '';

function mostrarConfirmacionSimple(mensaje, accion) {
    const modal = document.getElementById('modalConfirmarSimple');
    const texto = document.getElementById('confirm-text-simple');

    if (modal && texto) {
        texto.innerText = mensaje;
        accionPendienteSimple = accion;
        modal.style.display = 'flex';
    }
}

function cerrarModalSimple() {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
    accionPendienteSimple = '';
}

function ejecutarAccionSimple() {
    if (accionPendienteSimple === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.replace('/login');
    }
    cerrarModalSimple();
}

const cerrarSesion = () => mostrarConfirmacionSimple('¿Finalizar turno de especialista?', 'salir');

/* =====================================================================
   INICIALIZACIÓN
   ===================================================================== */

window.onload = () => {
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