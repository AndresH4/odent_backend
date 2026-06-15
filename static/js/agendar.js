/**
 * agendar.js — Stylo Dental
 * Carga especialistas y slots de agenda desde la API Flask.
 * Al confirmar, envía la cita a /api/citas (guarda en SQLite, no localStorage).
 */

'use strict';

// ─── Estado ──────────────────────────────────────────────────────────────────
let agendaDisponible = [];   // slots cargados de la API
let slotSeleccionado = null; // { Agenda_ID, ... }
let pacienteIdAgendar = null;

// ─── Utilidades ──────────────────────────────────────────────────────────────
function mostrarError(el, pEl) { el?.classList.add('input-error'); if (pEl) pEl.style.display = 'flex'; }
function ocultarError(el, pEl) { el?.classList.remove('input-error'); if (pEl) pEl.style.display = 'none'; }
function validarEmail(email) { return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(String(email).toLowerCase()); }
function cerrarVentanaYVolver() { window.close(); }

function resetearFormulario() {
    ['nombre','apellido','tipo-doc','num-doc','telefono','correo','servicio','fecha','hora'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.value = ''; ocultarError(el, document.getElementById('err-' + id)); }
    });
    slotSeleccionado = null;
}

// ─── Carga inicial de especialistas ──────────────────────────────────────────
async function cargarEspecialistas() {
    try {
        const res  = await fetch('/api/especialistas');
        const data = await res.json();

        const sel = document.getElementById('servicio');
        if (!sel) return;

        sel.innerHTML = '<option value="" disabled selected>Seleccione la especialidad</option>';

        // Agrupar especialidades únicas
        const especialidades = [...new Set(
            data.flatMap(e => e.Especialidades.split(', '))
        )];

        especialidades.forEach(esp => {
            const opt = document.createElement('option');
            opt.value       = esp;
            opt.textContent = esp;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('[agendar] Error cargando especialistas:', e);
    }
}

// ─── Carga de slots de agenda al seleccionar especialidad o fecha ─────────────
async function cargarAgenda() {
    const especialidad = document.getElementById('servicio')?.value;
    const fecha        = document.getElementById('fecha')?.value;
    const horaSelect   = document.getElementById('hora');
    if (!horaSelect) return;

    horaSelect.innerHTML = '<option value="" disabled selected>Seleccione la hora disponible</option>';
    slotSeleccionado = null;

    if (!especialidad && !fecha) return;

    try {
        const params = new URLSearchParams();
        if (fecha) params.append('fecha', fecha);

        const res  = await fetch(`/api/agenda?${params}`);
        const data = await res.json();

        // Filtrar por especialidad si hay selección
        agendaDisponible = especialidad
            ? data.filter(slot => slot.Nombre_Especialidad === especialidad)
            : data;

        if (agendaDisponible.length === 0) {
            const opt = document.createElement('option');
            opt.disabled = true;
            opt.textContent = 'Sin disponibilidad para esa fecha/especialidad';
            horaSelect.appendChild(opt);
            return;
        }

        agendaDisponible.forEach(slot => {
            const opt = document.createElement('option');
            opt.value       = slot.Agenda_ID;
            opt.textContent = `${slot.Hora_Inicio} — ${slot.NombreEspecialista}`;
            horaSelect.appendChild(opt);
        });

    } catch (e) {
        console.error('[agendar] Error cargando agenda:', e);
    }
}

// ─── Guardar slot seleccionado ────────────────────────────────────────────────
function seleccionarSlot() {
    const horaSelect = document.getElementById('hora');
    const agendaId   = parseInt(horaSelect?.value, 10);
    slotSeleccionado = agendaDisponible.find(s => s.Agenda_ID === agendaId) || null;
}

// ─── Validación y apertura del modal de verificación ─────────────────────────
async function validarYAgendar() {
    const campos    = ['nombre','apellido','tipo-doc','num-doc','telefono','correo','servicio','fecha','hora'];
    const regexLetr = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$/;
    let valido = true;

    campos.forEach(id => {
        const input  = document.getElementById(id);
        const errEl  = document.getElementById('err-' + id);
        let esInval  = !input?.value || !input.value.trim();

        if (errEl) errEl.innerText = '⚠ Este campo es obligatorio.';

        if (!esInval && (id === 'nombre' || id === 'apellido') && !regexLetr.test(input.value)) {
            if (errEl) errEl.innerText = '⚠ Solo se permiten letras.';
            esInval = true;
        }
        if (!esInval && id === 'telefono' && input.value.length !== 10) {
            if (errEl) errEl.innerText = '⚠ El teléfono debe tener 10 dígitos.';
            esInval = true;
        }
        if (!esInval && id === 'correo' && !validarEmail(input.value)) {
            if (errEl) errEl.innerText = '⚠ Ingrese un correo válido.';
            esInval = true;
        }

        if (esInval) { mostrarError(input, errEl); valido = false; }
        else          ocultarError(input, errEl);
    });

    if (!valido) return;

    // Seleccionar slot
    seleccionarSlot();
    if (!slotSeleccionado) {
        alert('Seleccione un horario disponible.');
        return;
    }

    // Buscar Paciente_ID por número de documento
    const numDoc = document.getElementById('num-doc').value.trim();
    try {
        const res  = await fetch('/api/usuarios');
        const usu  = await res.json();
        const match = usu.find(u => u.NumeroDocumento === numDoc && u.Rol_ID === 3);

        if (!match) {
            alert('No se encontró un paciente registrado con ese número de documento.\nPor favor regístrese primero.');
            return;
        }

        // Obtener Paciente_ID
        const resPac = await fetch(`/api/paciente/por-usuario/${match.Usuario_ID}`);
        if (resPac.ok) {
            const pac = await resPac.json();
            pacienteIdAgendar = pac.Paciente_ID;
        } else {
            alert('Error obteniendo datos del paciente.');
            return;
        }

        // Verificar multa activa
        const resMulta = await fetch(`/api/paciente/${pacienteIdAgendar}/multa-activa`);
        const dataMulta = await resMulta.json();

        const alerta = document.getElementById('alertaMulta');
        const header = document.getElementById('headerVerificacion');
        const btnFin = document.getElementById('btnFinal');

        if (dataMulta.tiene_multa) {
            alerta?.classList.remove('hidden');
            if (header) header.className = 'bg-orange-600 p-4 text-center';
            if (btnFin) btnFin.className = 'flex-1 bg-orange-600 text-white py-3 rounded-xl font-bold hover:bg-orange-700 transition-all uppercase text-xs shadow-lg';
        } else {
            alerta?.classList.add('hidden');
            if (header) header.className = 'bg-blue-600 p-4 text-center';
            if (btnFin) btnFin.className = 'flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition-all uppercase text-xs shadow-lg';
        }

    } catch (e) {
        console.error('[agendar] Error verificando paciente:', e);
        alert('Error de conexión. Intente de nuevo.');
        return;
    }

    // Mostrar resumen en el modal
    const resumen = document.getElementById('resumen');
    if (resumen) {
        resumen.innerHTML = `
            <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Paciente</span>
                <p class="text-sm text-slate-800 font-semibold uppercase">
                    ${document.getElementById('nombre').value} ${document.getElementById('apellido').value}
                </p>
            </div>
            <div class="grid grid-cols-2 gap-2">
                <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Documento</span>
                    <p class="text-sm text-slate-800">${document.getElementById('tipo-doc').value}: ${numDoc}</p>
                </div>
                <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Teléfono</span>
                    <p class="text-sm text-slate-800">${document.getElementById('telefono').value}</p>
                </div>
            </div>
            <div class="bg-blue-50 p-3 rounded-lg border border-blue-100">
                <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Cita</span>
                <p class="text-sm text-slate-800 font-bold uppercase">${slotSeleccionado.Nombre_Especialidad}</p>
                <p class="text-xs text-slate-600 mt-1">
                    Dr. ${slotSeleccionado.NombreEspecialista} |
                    ${slotSeleccionado.Fecha} ${slotSeleccionado.Hora_Inicio}
                </p>
            </div>`;
    }

    document.getElementById('modalVerificacion').style.display = 'flex';
}

// ─── Confirmar y guardar cita ─────────────────────────────────────────────────
async function finalizarTodo() {
    if (!slotSeleccionado || !pacienteIdAgendar) {
        alert('Datos incompletos. Vuelva a intentarlo.');
        return;
    }

    const motivo = document.getElementById('servicio').value;

    try {
        const res  = await fetch('/api/citas', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                Paciente_ID:     pacienteIdAgendar,
                Agenda_ID:       slotSeleccionado.Agenda_ID,
                Motivo_Consulta: motivo
            })
        });
        const data = await res.json();

        cerrarModal();

        if (data.ok) {
            const msgEl = document.getElementById('mensajeExito');
            if (msgEl) msgEl.textContent = 'Su cita ha sido registrada exitosamente. ¡Gracias por confiar en Stylo Dental!';
            document.getElementById('modalExito').style.display = 'flex';
        } else {
            alert(`No se pudo agendar: ${data.error}`);
        }
    } catch (e) {
        cerrarModal();
        alert('Error de conexión. Intente de nuevo.');
    }
}

function cerrarModal()         { document.getElementById('modalVerificacion').style.display = 'none'; }
function cerrarModalBloqueo()  { document.getElementById('modalBloqueo').style.display      = 'none'; }
function cerrarExitoYLimpiar() { document.getElementById('modalExito').style.display = 'none'; resetearFormulario(); }

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    cargarEspecialistas();

    // Recargar agenda cuando cambia especialidad o fecha
    document.getElementById('servicio')?.addEventListener('change', cargarAgenda);
    document.getElementById('fecha')?.addEventListener('change', cargarAgenda);
    document.getElementById('hora')?.addEventListener('change', seleccionarSlot);
});