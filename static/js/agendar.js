// Archivo: agendar.js
'use strict';

// ─── Estado ──────────────────────────────────────────────────────────────────
let agendaDisponible   = [];
let slotSeleccionado   = null;
let pacienteIdAgendar  = null;
let especialistasData  = [];
let fechaISOAgendar    = '';

const HORAS_DEFAULT = [
    '07:00:00', '07:30:00', '08:00:00', '08:30:00', '09:00:00', '09:30:00',
    '10:00:00', '10:30:00', '11:00:00', '11:30:00', '14:00:00', '14:30:00',
    '15:00:00', '15:30:00', '16:00:00', '16:30:00', '17:00:00'
];

const ESPECIALIDADES_FIJAS = [
    'Endodoncia', 'Odontopediatria', 'Odontologia General',
    'Cirugia Oral', 'Ortodoncia', 'Control brackets'
];

// ─── Utilidades ──────────────────────────────────────────────────────────────
function mostrarError(el, pEl) {
    el?.classList.add('invalid');
    if (pEl) pEl.style.display = 'block';
}

function ocultarError(el, pEl) {
    el?.classList.remove('invalid');
    if (pEl) pEl.style.display = 'none';
}

function validarEmail(email) {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(String(email).toLowerCase());
}

function cerrarVentanaYVolver() { window.close(); }

function resetearFormulario() {
    ['nombre', 'apellido', 'tipo-doc', 'num-doc', 'telefono', 'correo', 'servicio', 'fecha', 'hora'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.value = ''; ocultarError(el, document.getElementById('err-' + id)); }
    });
    const fechaNativa = document.getElementById('fechaNativa');
    if (fechaNativa) fechaNativa.value = '';
    fechaISOAgendar   = '';
    slotSeleccionado  = null;
    pacienteIdAgendar = null;
    agendaDisponible  = [];
}

// ─── Campo Fecha ─────────────────────────────────────────────────────────────
function inicializarCampoFechaAgendar() {
    const inputTexto    = document.getElementById('fecha');
    const inputNativo   = document.getElementById('fechaNativa');
    const btnCalendario = document.getElementById('datePickerBtnAgendar');

    if (!inputTexto || !inputNativo || !btnCalendario) return;

    inputTexto.addEventListener('focus', () => {
        inputTexto.placeholder = 'DD/MM/AAAA';
        inputTexto.classList.add('typing-mode');
    });
    inputTexto.addEventListener('blur', () => {
        if (!inputTexto.value) {
            inputTexto.placeholder = 'Ingrese la fecha de la cita';
            inputTexto.classList.remove('typing-mode');
        }
    });
    inputTexto.addEventListener('input', () => {
        let raw = inputTexto.value.replace(/\D/g, '').slice(0, 8);
        let formatted = '';
        if (raw.length > 0) formatted += raw.slice(0, 2);
        if (raw.length > 2) formatted += '/' + raw.slice(2, 4);
        if (raw.length > 4) formatted += '/' + raw.slice(4, 8);
        inputTexto.value = formatted;
        if (raw.length === 8) {
            const isoDate = `${raw.slice(4, 8)}-${raw.slice(2, 4)}-${raw.slice(0, 2)}`;
            inputNativo.value = isoDate;
            fechaISOAgendar   = isoDate;
            cargarAgenda();
        } else {
            inputNativo.value = '';
            fechaISOAgendar   = '';
        }
    });
    btnCalendario.addEventListener('click', () => {
        inputNativo.style.pointerEvents = 'auto';
        if (inputNativo.showPicker) inputNativo.showPicker();
        else inputNativo.click();
    });
    inputNativo.addEventListener('change', () => {
        const val = inputNativo.value;
        if (!val) return;
        const [yyyy, mm, dd] = val.split('-');
        inputTexto.value = `${dd}/${mm}/${yyyy}`;
        fechaISOAgendar  = val;
        cargarAgenda();
    });
}

function leerFechaISO() {
    const inputNativo = document.getElementById('fechaNativa');
    if (inputNativo?.value) return inputNativo.value;
    const inputTexto = document.getElementById('fecha');
    if (inputTexto?.value) {
        const parts = inputTexto.value.split('/');
        if (parts.length === 3 && parts[2].length === 4)
            return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    return '';
}

// ─── Helpers de horario ───────────────────────────────────────────────────────
function calcularHoraFin(horaInicio) {
    const [h, m]   = horaInicio.split(':').map(Number);
    const totalMin = h * 60 + m + 30;
    const hFin     = Math.floor(totalMin / 60) % 24;
    const mFin     = totalMin % 60;
    return `${String(hFin).padStart(2, '0')}:${String(mFin).padStart(2, '0')}:00`;
}

function formatHora(hora) { return hora ? hora.slice(0, 5) : ''; }

// ─── Fallback: slots sintéticos ───────────────────────────────────────────────
function poblarHorasFallback(especialidad, fecha) {
    const horaSelect = document.getElementById('hora');
    if (!horaSelect) return;

    const especialistasConEsp = especialistasData.filter(e =>
        e.Especialidades.split(', ').includes(especialidad)
    );

    if (especialistasConEsp.length === 0) {
        horaSelect.innerHTML = '<option value="" disabled selected>Sin especialistas disponibles para esta especialidad</option>';
        agendaDisponible = [];
        return;
    }

    agendaDisponible = HORAS_DEFAULT.map((hora, idx) => {
        const esp = especialistasConEsp[idx % especialistasConEsp.length];
        return {
            Agenda_ID:           null,
            _esSintetico:        true,
            Hora_Inicio:         hora,
            Hora_Fin:            calcularHoraFin(hora),
            Fecha:               fecha || '',
            Nombre_Especialidad: especialidad,
            NombreEspecialista:  esp.NombreCompleto,
            Especialista_ID:     esp.Especialista_ID
        };
    });

    horaSelect.innerHTML = '<option value="" disabled selected>Seleccione la hora disponible</option>';
    agendaDisponible.forEach((slot, idx) => {
        const opt = document.createElement('option');
        opt.value       = `s_${idx}`;
        opt.textContent = `${formatHora(slot.Hora_Inicio)} — Dr(a). ${slot.NombreEspecialista}`;
        horaSelect.appendChild(opt);
    });
}

// ─── GET /api/especialistas ───────────────────────────────────────────────────
async function cargarEspecialistas() {
    const sel = document.getElementById('servicio');
    if (!sel) return;

    try {
        const res  = await fetch('/api/especialistas');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        especialistasData = data;

        sel.innerHTML = '<option value="" disabled selected>Seleccione la especialidad</option>';
        const especialidades = [...new Set(data.flatMap(e => e.Especialidades.split(', ')))];
        const lista = especialidades.length > 0 ? especialidades : ESPECIALIDADES_FIJAS;

        lista.forEach(esp => {
            const opt = document.createElement('option');
            opt.value = esp; opt.textContent = esp;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('[agendar] Error cargando especialistas, usando fallback:', e);
        sel.innerHTML = '<option value="" disabled selected>Seleccione la especialidad</option>';
        ESPECIALIDADES_FIJAS.forEach(esp => {
            const opt = document.createElement('option');
            opt.value = esp; opt.textContent = esp;
            sel.appendChild(opt);
        });
    }
}

// ─── GET /api/agenda?fecha= ───────────────────────────────────────────────────
async function cargarAgenda() {
    const especialidad = document.getElementById('servicio')?.value;
    const fecha        = leerFechaISO();
    const horaSelect   = document.getElementById('hora');
    if (!horaSelect) return;

    horaSelect.innerHTML = '<option value="" disabled selected>Seleccione la hora disponible</option>';
    slotSeleccionado = null;
    agendaDisponible = [];
    if (!especialidad) return;

    try {
        const params = new URLSearchParams();
        if (fecha) params.append('fecha', fecha);
        const res  = await fetch(`/api/agenda?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const slotsFiltrados = data.filter(slot => slot.Nombre_Especialidad === especialidad);
        if (slotsFiltrados.length === 0) { poblarHorasFallback(especialidad, fecha); return; }

        agendaDisponible = slotsFiltrados;
        slotsFiltrados.forEach(slot => {
            const opt = document.createElement('option');
            opt.value       = `r_${slot.Agenda_ID}`;
            opt.textContent = `${formatHora(slot.Hora_Inicio)} — Dr(a). ${slot.NombreEspecialista}`;
            horaSelect.appendChild(opt);
        });
    } catch (e) {
        console.error('[agendar] Error cargando agenda, usando horas por defecto:', e);
        poblarHorasFallback(especialidad, fecha);
    }
}

// ─── Seleccionar slot ─────────────────────────────────────────────────────────
function seleccionarSlot() {
    const horaSelect = document.getElementById('hora');
    const val        = horaSelect?.value || '';
    slotSeleccionado = null;
    if (val.startsWith('r_')) {
        const agendaId = parseInt(val.replace('r_', ''), 10);
        slotSeleccionado = agendaDisponible.find(s => s.Agenda_ID === agendaId) || null;
    } else if (val.startsWith('s_')) {
        const idx = parseInt(val.replace('s_', ''), 10);
        slotSeleccionado = !isNaN(idx) ? agendaDisponible[idx] : null;
    }
}

// ─── POST /api/agenda — crear slot sintético en BD ────────────────────────────
async function crearSlotEnBD(slot) {
    const fecha = leerFechaISO();
    if (!fecha) return null;
    try {
        const res = await fetch('/api/agenda', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                Especialista_ID: slot.Especialista_ID,
                Fecha:           fecha,
                Hora_Inicio:     slot.Hora_Inicio,
                Hora_Fin:        slot.Hora_Fin,
                Estado_ID:       1
            })
        });
        if (!res.ok) return null;
        const data = await res.json();
        return data.ok ? (data.Agenda_ID || data.agenda_id) : null;
    } catch (err) {
        console.warn('[agendar] No se pudo crear slot en BD:', err);
        return null;
    }
}

// ─── GET /api/paciente/<id>/multa-activa ─────────────────────────────────────
async function _verificarMultaActiva(pacId) {
    try {
        const res  = await fetch(`/api/paciente/${pacId}/multa-activa`);
        if (!res.ok) return false;
        const data = await res.json();
        return data.tiene_multa === true;
    } catch {
        return false;
    }
}

// ─── Validar y abrir modal de verificación ────────────────────────────────────
async function validarYAgendar() {
    const campos   = ['nombre', 'apellido', 'tipo-doc', 'num-doc', 'telefono', 'correo', 'servicio', 'fecha', 'hora'];
    const regexLetr = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$/;
    let valido = true;

    campos.forEach(id => {
        const input = document.getElementById(id);
        const errEl = document.getElementById('err-' + id);
        let rawVal  = (id === 'fecha') ? leerFechaISO() : input?.value;
        let esInval = !rawVal || !String(rawVal).trim();

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

    seleccionarSlot();
    if (!slotSeleccionado) { alert('Seleccione un horario disponible.'); return; }

    // GET /api/usuarios — buscar paciente por número de documento
    const numDoc = document.getElementById('num-doc').value.trim();
    try {
        const res   = await fetch('/api/usuarios');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const usu   = await res.json();
        const match = (Array.isArray(usu) ? usu : []).find(
            u => u.NumeroDocumento === numDoc && u.Rol_ID === 3
        );

        if (!match) {
            alert('No se encontró un paciente registrado con ese número de documento.\nPor favor regístrese primero.');
            return;
        }

        // GET /api/paciente/por-usuario/<uid>
        const resPac = await fetch(`/api/paciente/por-usuario/${match.Usuario_ID}`);
        if (resPac.ok) {
            const pac     = await resPac.json();
            pacienteIdAgendar = pac.Paciente_ID;
        } else {
            alert('Error obteniendo datos del paciente.');
            return;
        }

        // GET /api/paciente/<id>/multa-activa — verificar multa antes de permitir agendar
        const tieneMulta = await _verificarMultaActiva(pacienteIdAgendar);

        const alerta = document.getElementById('alertaMulta');
        const header = document.getElementById('headerVerificacion');
        const btnFin = document.getElementById('btnFinal');

        if (tieneMulta) {
            alerta?.classList.remove('hidden');
            if (header) header.className = 'modal-header modal-header-orange';
            if (btnFin) btnFin.className = 'btn-primario btn-naranja';
        } else {
            alerta?.classList.add('hidden');
            if (header) header.className = 'modal-header modal-header-blue';
            if (btnFin) btnFin.className = 'btn-primario btn-azul';
        }

    } catch (e) {
        console.error('[agendar] Error verificando paciente:', e);
        alert('Error de conexión. Intente de nuevo.');
        return;
    }

    // Mostrar resumen en modal
    const fecha   = leerFechaISO();
    const numDoc2 = document.getElementById('num-doc').value.trim();
    const resumen = document.getElementById('resumen');
    if (resumen) {
        resumen.innerHTML = `
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Paciente</span>
                <p style="font-size:14px;color:#1e293b;font-weight:600;margin:0;text-transform:uppercase;">
                    ${document.getElementById('nombre').value} ${document.getElementById('apellido').value}
                </p>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Documento</span>
                    <p style="font-size:13px;color:#1e293b;margin:0;">${document.getElementById('tipo-doc').value}: ${numDoc2}</p>
                </div>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Teléfono</span>
                    <p style="font-size:13px;color:#1e293b;margin:0;">${document.getElementById('telefono').value}</p>
                </div>
            </div>
            <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:12px 14px;">
                <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Cita</span>
                <p style="font-size:14px;color:#1e293b;font-weight:700;margin:0 0 4px;text-transform:uppercase;">${slotSeleccionado.Nombre_Especialidad}</p>
                <p style="font-size:12px;color:#475569;margin:0;">
                    Dr(a). ${slotSeleccionado.NombreEspecialista} &nbsp;|&nbsp;
                    ${fecha} &nbsp;${formatHora(slotSeleccionado.Hora_Inicio)}
                </p>
            </div>`;
    }

    document.getElementById('modalVerificacion').style.display = 'flex';
}

// ─── POST /api/citas — confirmar y guardar cita ───────────────────────────────
async function finalizarTodo() {
    if (!slotSeleccionado || !pacienteIdAgendar) {
        alert('Datos incompletos. Vuelva a intentarlo.');
        return;
    }

    // Segunda verificación de multa activa antes de confirmar (seguridad doble)
    const tieneMulta = await _verificarMultaActiva(pacienteIdAgendar);
    if (tieneMulta) {
        const confirmar = confirm(
            'Tiene una multa pendiente. Al confirmar la cita acepta pagarla el día de su atención. ¿Desea continuar?'
        );
        if (!confirmar) return;
    }

    const motivo = document.getElementById('servicio').value;

    // Si slot sintético → persistirlo primero via POST /api/agenda
    if (slotSeleccionado._esSintetico) {
        const nuevoAgendaId = await crearSlotEnBD(slotSeleccionado);
        if (nuevoAgendaId) {
            slotSeleccionado.Agenda_ID    = nuevoAgendaId;
            slotSeleccionado._esSintetico = false;
        } else {
            cerrarModal();
            const msgEl = document.getElementById('mensajeExito');
            if (msgEl) msgEl.textContent = 'Solicitud recibida. Seleccione una fecha para confirmar el horario con el especialista.';
            document.getElementById('modalExito').style.display = 'flex';
            return;
        }
    }

    // POST /api/citas
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
    inicializarCampoFechaAgendar();
    cargarEspecialistas();
    document.getElementById('servicio')?.addEventListener('change', cargarAgenda);
    document.getElementById('hora')?.addEventListener('change', seleccionarSlot);
});