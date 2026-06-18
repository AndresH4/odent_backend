'use strict';

let accionPendiente = null;
let indexPendiente  = null;

/* =====================================================================
   SESIÓN — carga y mapea los datos del paciente en el DOM
   ===================================================================== */

const cargarInfoSesionPaciente = async () => {
    const raw  = sessionStorage.getItem('odent_usuario');
    const user = raw ? JSON.parse(raw) : null;

    const correoLogueado = localStorage.getItem('usuario_logueado');
    const dbUsuarios     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    const userLegacy     = dbUsuarios[correoLogueado];

    // CORRECCIÓN: Si no es un paciente, no debería tomarse como un usuario válido en este dashboard
    const u = user || (userLegacy?.rol === 'Paciente' ? userLegacy : null);

    if (!u) { window.location.replace('/login'); return; }

    const nombreCompleto = u.Nombres
        ? `${u.Nombres} ${u.Apellidos || ''}`.trim()
        : `${u.nombre || ''} ${u.apellidos || ''}`.trim();

    const inicial    = nombreCompleto.charAt(0).toUpperCase();
    const correo     = u.Correo      || u.correo      || '';
    const telefono   = u.Telefono    || u.telefono    || 'No asignado';
    const nacimiento = u.Nacimiento  || u.nacimiento  || '---';
    const tipoDoc    = u.TipoDoc     || u.tipoDoc     || '---';
    const numDoc     = u.NumDoc      || u.numDoc      || '---';

    const displays = {
        'nombre-usuario':        nombreCompleto,
        'nombre-usuario-header': nombreCompleto,
        'avatar-letras':         inicial,
        'perfil-avatar-grande': inicial,
        'perfil-nombres':       u.Nombres   || u.nombre    || '---',
        'perfil-apellidos':     u.Apellidos || u.apellidos || '---',
        'perfil-tipoDoc':       tipoDoc,
        'perfil-numDoc':        numDoc,
        'perfil-correo':        correo,
        'perfil-nacimiento':    nacimiento,
        'edit-correo':          correo,
        'edit-telefono':        telefono,
        'edit-nacimiento':      nacimiento,
    };

    Object.entries(displays).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (!el) return;
        (el.tagName === 'INPUT' || el.tagName === 'SELECT')
            ? (el.value = val)
            : (el.innerText = val);
    });

    // Fecha en el header
    const fechaEl = document.getElementById('fecha-actual-paciente');
    if (fechaEl && !fechaEl.innerText) {
        fechaEl.innerText = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        }).toUpperCase();
    }

    // Cargar EPS desde el backend
    const usuarioId = u.Usuario_ID || u.usuario_id || null;
    if (usuarioId) await cargarEPSPaciente(usuarioId);
};

/* =====================================================================
   EPS — consulta al backend y rellena tarjetas + modal de perfil
   ===================================================================== */

const cargarEPSPaciente = async (usuarioId) => {
    const idsEPS     = ['perfil-eps',     'stat-eps-nombre'];
    const idsRegimen = ['perfil-regimen', 'stat-regimen'];

    const setTexto = (ids, texto) =>
        ids.forEach(id => { const el = document.getElementById(id); if (el) el.innerText = texto; });

    setTexto(idsEPS,     'Cargando…');
    setTexto(idsRegimen, 'Cargando…');

    try {
        const resp = await fetch('/eps/afiliacion', { method: 'GET' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || 'Error en respuesta');

        const afiliacion = (data.data || []).find(
            a => String(a.ID_Usuario) === String(usuarioId)
        );

        if (afiliacion) {
            setTexto(idsEPS,     afiliacion.Nombre_EPS || '—');
            setTexto(idsRegimen, afiliacion.Regimen    || '—');

            const elNumAfil  = document.getElementById('perfil-num-afiliado');
            const elEstado   = document.getElementById('perfil-estado-afiliacion');
            if (elNumAfil) elNumAfil.innerText = afiliacion.Numero_Afiliado || '---';
            if (elEstado)  elEstado.innerText  = afiliacion.Estado          || '---';
        } else {
            setTexto(idsEPS,     'Sin afiliación');
            setTexto(idsRegimen, '—');
        }
    } catch (err) {
        console.error('[EPS]', err);
        setTexto(idsEPS,     'Error al cargar');
        setTexto(idsRegimen, '—');
    }
};

/* =====================================================================
   RELOJ
   ===================================================================== */

function actualizarReloj() {
    const el = document.getElementById('reloj');
    if (el) el.innerText = new Date().toLocaleTimeString('es-CO');
}

/* =====================================================================
   AUDITORÍA DE FECHAS — marca como "Cancelada con multa" las vencidas
   ===================================================================== */

function auditarFechas(historial) {
    const ahora = new Date();
    let huboCambios = false;

    historial.forEach(cita => {
        if (cita.estado !== 'Agendada') return;

        const [horaStr, meridiano] = cita.hora.split(' ');
        let [horas, minutos] = horaStr.split(':').map(Number);
        if (meridiano === 'PM' && horas !== 12) horas += 12;
        if (meridiano === 'AM' && horas === 12) horas = 0;

        const fechaCita = new Date(
            `${cita.fecha}T${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:00`
        );
        if (fechaCita < ahora) {
            cita.estado = 'Cancelada con multa';
            huboCambios = true;
        }
    });

    return huboCambios;
}

/* =====================================================================
   CARGA DE CITAS — panel principal
   ===================================================================== */

function cargarCitas() {
    cargarInfoSesionPaciente();

    const citasEntrantes = JSON.parse(localStorage.getItem('citasPacientes')) || [];
    let    historial       = JSON.parse(localStorage.getItem('historialCompleto')) || [];

    if (citasEntrantes.length > 0) {
        citasEntrantes.forEach(cita => {
            cita.estado           = 'Agendada';
            cita.ocultoEnPrincipal = false;
            historial.push(cita);
        });
        localStorage.setItem('historialCompleto', JSON.stringify(historial));
        localStorage.removeItem('citasPacientes');
    }

    if (auditarFechas(historial)) {
        localStorage.setItem('historialCompleto', JSON.stringify(historial));
    }

    const tbody      = document.getElementById('tabla-citas-body');
    const countCitas = document.getElementById('count-citas');
    if (tbody) tbody.innerHTML = '';

    const visibles = historial.filter(c => !c.ocultoEnPrincipal);
    if (countCitas) countCitas.innerText = visibles.length;

    const msgVacio = document.getElementById('no-citas-msg');

    if (visibles.length === 0) {
        msgVacio?.classList.remove('hidden');
        return;
    }

    msgVacio?.classList.add('hidden');

    historial.forEach((c, originalIndex) => {
        if (c.ocultoEnPrincipal) return;

        let badgeClass = 'status-agendada';
        if (c.estado === 'Cancelada')            badgeClass = 'status-cancelada';
        if (c.estado === 'Cancelada con multa')  badgeClass = 'status-multa';

        const accion = c.estado === 'Agendada'
            ? `<button onclick="verificarYPreparar(${originalIndex})"
                   class="text-red-400 hover:text-red-600 p-2 transition-transform hover:scale-125">
                   <i class="fas fa-ban"></i>
               </button>`
            : `<button onclick="mostrarConfirmacionSimple('¿Quitar de la vista principal? Seguirá en su historial.','eliminar',${originalIndex})"
                   class="text-slate-300 hover:text-red-500 p-2 transition-transform hover:scale-125">
                   <i class="fas fa-eye-slash"></i>
               </button>`;

        tbody?.insertAdjacentHTML('afterbegin', `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="p-5 font-black text-slate-800 uppercase text-xs">${c.nombre}</td>
                <td class="p-5 text-[10px] font-bold uppercase tracking-tighter">
                    ${c.tipoDoc}<br>
                    <span class="text-slate-400 font-medium">${c.numDoc}</span>
                </td>
                <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">${c.especialidad}</td>
                <td class="p-5 font-bold uppercase text-xs">
                    ${c.fecha}<br>
                    <span class="text-slate-400 text-[10px] tracking-tighter">${c.hora}</span>
                </td>
                <td class="p-5"><span class="${badgeClass}">${c.estado}</span></td>
                <td class="p-5 text-center">${accion}</td>
            </tr>`);
    });
}

/* =====================================================================
   HISTORIAL COMPLETO
   ===================================================================== */

function generarHistorialCompleto() {
    const historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
    const tbody     = document.getElementById('tabla-historial-completo');
    if (tbody) tbody.innerHTML = '';

    [...historial].reverse().forEach((c, i) => {
        const originalIndex = historial.length - 1 - i;

        let badgeClass = 'status-agendada';
        if (c.estado === 'Cancelada')           badgeClass = 'status-cancelada';
        if (c.estado === 'Cancelada con multa') badgeClass = 'status-multa';

        tbody?.insertAdjacentHTML('beforeend', `
            <tr class="hover:bg-slate-50">
                <td class="p-5 font-bold text-slate-700">
                    ${c.fecha}<br>
                    <span class="text-[10px] text-slate-400 font-black">${c.hora}</span>
                </td>
                <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">${c.especialidad}</td>
                <td class="p-5 font-bold uppercase text-xs text-slate-500">Stylo Dental Service</td>
                <td class="p-5"><span class="${badgeClass}">${c.estado}</span></td>
                <td class="p-5 text-center">
                    <button onclick="verificarYPreparar(${originalIndex})"
                        class="bg-slate-100 text-slate-600 px-3 py-1 rounded-lg text-[10px] font-black uppercase
                               hover:bg-sky-600 hover:text-white transition-all">
                        Ver Datos
                    </button>
                </td>
            </tr>`);
    });
}

/* =====================================================================
   CAMBIAR VISTA
   ===================================================================== */

function cambiarVista(vista) {
    const inicio      = document.getElementById('vista-inicio');
    const historial   = document.getElementById('vista-historial');
    const btnInicio   = document.getElementById('btn-inicio');
    const btnHistorial = document.getElementById('btn-historial');
    const titulo      = document.getElementById('titulo-principal');

    if (vista === 'inicio') {
        inicio?.classList.remove('hidden');
        historial?.classList.add('hidden');
        btnInicio?.classList.add('active');
        btnHistorial?.classList.remove('active');
        if (titulo) titulo.innerText = 'Panel de Control';
        cargarCitas();
    } else {
        inicio?.classList.add('hidden');
        historial?.classList.remove('hidden');
        btnInicio?.classList.remove('active');
        btnHistorial?.classList.add('active');
        if (titulo) titulo.innerText = 'Historial Completo';
        generarHistorialCompleto();
    }
}

/* =====================================================================
   MODAL PERFIL
   ===================================================================== */

function abrirModalPerfil() {
    cargarInfoSesionPaciente();
    const modal = document.getElementById('modalPerfil');
    if (modal) modal.style.display = 'flex';
}

function cerrarModalPerfil() {
    const modal = document.getElementById('modalPerfil');
    if (modal) modal.style.display = 'none';
}

/* =====================================================================
   MODAL CONFIGURACIÓN
   ===================================================================== */

function abrirConfiguracion() {
    cargarInfoSesionPaciente();
    cerrarModalPerfil();
    const modal = document.getElementById('modalConfig');
    if (modal) modal.style.display = 'flex';
}

function cerrarConfiguracion() {
    const modal = document.getElementById('modalConfig');
    if (modal) modal.style.display = 'none';
    const np = document.getElementById('nueva-pass');
    const cp = document.getElementById('confirmar-pass');
    if (np) np.value = '';
    if (cp) cp.value = '';
}

/* =====================================================================
   GUARDAR CONFIGURACIÓN — fetch al backend + fallback localStorage
   ===================================================================== */

async function guardarConfiguracionGeneral() {
    const raw        = sessionStorage.getItem('odent_usuario');
    const u          = raw ? JSON.parse(raw) : null;
    const usuarioId  = u ? (u.Usuario_ID || u.usuario_id) : null;

    const nuevoCorreo = document.getElementById('edit-correo').value.trim();
    const nuevoTel    = document.getElementById('edit-telefono').value.trim();
    const nuevaFecha  = document.getElementById('edit-nacimiento').value;
    const nuevaPass   = document.getElementById('nueva-pass').value;
    const confirmPass = document.getElementById('confirmar-pass').value;

    if (!nuevoCorreo) { mostrarToast('El correo es obligatorio.', 'error'); return; }

    if (nuevaPass) {
        if (nuevaPass.length < 6)       { mostrarToast('La contraseña debe tener al menos 6 caracteres.', 'error'); return; }
        if (nuevaPass !== confirmPass)  { mostrarToast('Las contraseñas no coinciden.', 'error'); return; }

        if (usuarioId) {
            try {
                const resp = await fetch('/usuarios/cambiar-password', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body:    JSON.stringify({
                        usuario_id:           usuarioId,
                        contrasena_nueva:     nuevaPass,
                        contrasena_confirmar: confirmPass,
                    }),
                });
                const data = await resp.json();
                if (!resp.ok || !data.ok) {
                    mostrarToast(data.error || 'Error al actualizar contraseña.', 'error');
                    return;
                }
            } catch {
                mostrarToast('Error de conexión al cambiar contraseña.', 'error');
                return;
            }
            
            // CORRECCIÓN: Se remueven las líneas huérfanas que llamaban a 'historial' aquí adentro
            cargarCitas();
        }
    }

    // Actualizar datos clínicos en el backend si el paciente tiene ID
    if (usuarioId) {
        try {
            const respPac = await fetch('/eps/paciente', { method: 'GET' });
            if (respPac.ok) {
                const dataPac  = await respPac.json();
                const paciente = (dataPac.data || []).find(
                    p => String(p.ID_Usuario) === String(usuarioId)
                );
                if (paciente) {
                    await fetch(`/eps/paciente/${paciente.ID_Paciente}`, {
                        method:  'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body:    JSON.stringify({
                            Fecha_Nacimiento: nuevaFecha || paciente.Fecha_Nacimiento,
                            Genero:           paciente.Genero,
                            Grupo_Sanguineo:  paciente.Grupo_Sanguineo,
                            Alergias:         paciente.Alergias,
                            Antecedentes:     paciente.Antecedentes,
                            Observaciones:    paciente.Observaciones,
                        }),
                    });
                }
            }
        } catch (err) {
            console.warn('[Config] No se pudo actualizar datos clínicos en backend:', err);
        }
    }

    // Fallback localStorage
    const sesion   = localStorage.getItem('usuario_logueado');
    const usuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    if (sesion && usuarios[sesion]) {
        usuarios[sesion].correo     = nuevoCorreo;
        usuarios[sesion].telefono   = nuevoTel;
        usuarios[sesion].nacimiento = nuevaFecha;
        if (nuevaPass) usuarios[sesion].password = nuevaPass;
        localStorage.setItem('usuarios_dental', JSON.stringify(usuarios));
    }

    // Actualizar sessionStorage
    if (u) {
        u.Correo     = nuevoCorreo;
        u.Telefono   = nuevoTel;
        u.Nacimiento = nuevaFecha;
        sessionStorage.setItem('odent_usuario', JSON.stringify(u));
    }

    mostrarToast('¡Perfil actualizado con éxito!', 'success');
    cerrarConfiguracion();
    cargarInfoSesionPaciente();
} // CORRECCIÓN: Estructura de llaves cerrada correctamente aquí.

/* =====================================================================
   MODAL CANCELAR CITA — verificar y preparar
   ===================================================================== */

function verificarYPreparar(index) {
    indexPendiente  = index;
    const historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
    const cita      = historial[index];

    if (!cita) return;

    const infoContenedor = document.getElementById('detalles-completos');
    if (infoContenedor) {
        infoContenedor.innerHTML = `
            <div><p class="data-label">Nombre</p>
                 <p class="data-value uppercase">${cita.nombre || ''}</p></div>
            <div><p class="data-label">Documento</p>
                 <p class="data-value uppercase">${cita.tipoDoc || ''} ${cita.numDoc || ''}</p></div>
            <div class="col-span-2 mt-2">
                 <p class="data-label">Especialidad</p>
                 <p class="data-value uppercase text-sky-700 font-black tracking-widest">${cita.especialidad || ''}</p></div>
            <div><p class="data-label">Fecha</p>
                 <p class="data-value">${cita.fecha || ''}</p></div>
            <div><p class="data-label">Hora</p>
                 <p class="data-value">${cita.hora || ''}</p></div>`;
    }

    const modal = document.getElementById('modalCancelarCita');
    if (modal) modal.style.display = 'flex';
}

function cerrarModalCancelar() {
    const modal = document.getElementById('modalCancelarCita');
    if (modal) modal.style.display = 'none';
}

function solicitarConfirmacionFinal() {
    const modalCancel = document.getElementById('modalCancelarCita');
    const modalConfirm = document.getElementById('modalConfirmacionFinal');
    if (modalCancel) modalCancel.style.display   = 'none';
    if (modalConfirm) modalConfirm.style.display = 'flex';
}

function confirmarAccionCancelado() {
    cerrarConfirmacionFinal();
    const historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
    if (historial[indexPendiente]) {
        historial[indexPendiente].estado = 'Cancelada';
        localStorage.setItem('historialCompleto', JSON.stringify(historial));
        cargarCitas();
    }
}

function cerrarConfirmacionFinal() {
    const modal = document.getElementById('modalConfirmacionFinal');
    if (modal) modal.style.display = 'none';
}

/* =====================================================================
   MODAL CONFIRMACIÓN SIMPLE
   ===================================================================== */

function mostrarConfirmacionSimple(mensaje, tipo, index = null) {
    accionPendiente = tipo;
    indexPendiente  = index;
    const txt = document.getElementById('confirm-text-simple');
    if (txt) txt.innerText = mensaje;
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'flex';
}

function cerrarModalSimple() {
    const modal = document.getElementById('modalConfirmarSimple');
    if (modal) modal.style.display = 'none';
}

function ejecutarAccionSimple() {
    cerrarModalSimple();
    let historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];

    if (accionPendiente === 'eliminar') {
        if (historial[indexPendiente]) historial[indexPendiente].ocultoEnPrincipal = true;
    } else if (accionPendiente === 'limpiar') {
        historial.forEach(cita => {
            if (cita.estado === 'Cancelada' || cita.estado === 'Cancelada con multa') {
                cita.ocultoEnPrincipal = true;
            }
        });
    } else if (accionPendiente === 'salir') {
        sessionStorage.removeItem('odent_usuario');
        localStorage.removeItem('usuario_logueado');
        window.location.href = '/login';
        return;
    }

    localStorage.setItem('historialCompleto', JSON.stringify(historial));
    cargarCitas();
}

/* =====================================================================
   TOAST — notificaciones no bloqueantes
   ===================================================================== */

function mostrarToast(mensaje, tipo = 'info') {
    let toast = document.getElementById('toast-paciente');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-paciente';
        Object.assign(toast.style, {
            position: 'fixed', bottom: '32px', right: '32px', zIndex: '9999',
            padding: '16px 28px', borderRadius: '20px', fontWeight: '800',
            fontSize: '13px', letterSpacing: '0.05em',
            boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
            transition: 'all 0.4s cubic-bezier(0.23,1,0.32,1)',
            opacity: '0', transform: 'translateY(20px)',
            fontFamily: "'Open Sans', sans-serif",
        });
        document.body.appendChild(toast);
    }

    const temas = {
        success: { background: '#f0fdf4', color: '#15803d', border: '2px solid #bbf7d0' },
        error:   { background: '#fff1f2', color: '#be123c', border: '2px solid #fecdd3' },
        info:    { background: '#f0f9ff', color: '#0369a1', border: '2px solid #bae6fd' },
    };

    Object.assign(toast.style, temas[tipo] || temas.info);
    toast.innerText = mensaje;

    requestAnimationFrame(() => {
        toast.style.opacity   = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity   = '0';
        toast.style.transform = 'translateY(20px)';
    }, 3500);
}

/* =====================================================================
   INICIALIZACIÓN
   ===================================================================== */

window.onfocus = cargarCitas;

window.onload = () => {
    actualizarReloj();
    setInterval(actualizarReloj, 1000);

    // CORRECCIÓN: Se eliminó la duplicidad del formateo de fecha que ya realiza cargarCitas() de manera asíncrona.
    try {
        cargarCitas();
    } catch (err) {
        console.error('[Init] Error al cargar citas:', err);
    }
};