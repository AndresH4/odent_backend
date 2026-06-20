// Archivo: agendar.js
'use strict';

// ─── Estado ──────────────────────────────────────────────────────────────────
let agendaDisponible   = [];
let slotSeleccionado   = null;
let pacienteIdAgendar  = null;
let especialistasData  = [];
let fechaISOAgendar    = '';
let _sesionPacienteAgendar = null;

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

function cerrarVentanaYVolver() {
    if (document.referrer) {
        history.back();
    } else {
        window.location.href = '/paciente.html';
    }
}

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

// ─── Autocompletar datos del paciente logueado ────────────────────────────────
async function autocompletarDatosPaciente() {
    const raw = sessionStorage.getItem('odent_usuario');
    if (!raw) {
        window.location.replace('/login');
        return;
    }

    let sesion;
    try {
        sesion = JSON.parse(raw);
    } catch (e) {
        window.location.replace('/login');
        return;
    }

    if (!sesion || sesion.Rol_ID !== 3) {
        window.location.replace('/login');
        return;
    }

    _sesionPacienteAgendar = sesion;

    // Rellenar campos de texto con datos de sesión (precarga inmediata)
    _setFieldValue('nombre',    sesion.Nombres    || '');
    _setFieldValue('apellido',  sesion.Apellidos  || '');
    _setFieldValue('telefono',  sesion.Telefono   || '');
    _setFieldValue('correo',    sesion.Correo     || '');
    _setFieldValue('num-doc',   sesion.NumeroDocumento || '');

    // Los campos quedan editables: el paciente puede modificar los datos
    // autocompletados antes de confirmar el agendamiento.

    // Obtener Paciente_ID
    try {
        const resPac = await fetch(`/api/paciente/por-usuario/${sesion.Usuario_ID}`);
        if (resPac.ok) {
            const pac = await resPac.json();
            pacienteIdAgendar = pac.Paciente_ID;
        }
    } catch (e) {
        console.warn('[agendar] No se pudo obtener Paciente_ID:', e);
    }

    // Obtener tipo de documento, asignar valores reales y autoseleccionar
    try {
        const resTipos = await fetch('/api/tipos_documento');
        if (resTipos.ok) {
            const tipos = await resTipos.json();
            const selectTipoDoc = document.getElementById('tipo-doc');

            // Asignar el TipoDoc_ID real como value de cada opción (por coincidencia
            // de texto), para que al editar/enviar el formulario se use el ID correcto.
            if (selectTipoDoc) {
                for (let i = 0; i < selectTipoDoc.options.length; i++) {
                    const opt = selectTipoDoc.options[i];
                    if (!opt.value && opt.text) {
                        const matchOpt = tipos.find(t =>
                            (t.Nombre_Tipo_Documento || '').toLowerCase().split(' ')[0] === opt.text.toLowerCase().split(' ')[0]
                        );
                        if (matchOpt) opt.value = matchOpt.TipoDoc_ID;
                    }
                }
            }

            const tipoDoc = tipos.find(t => String(t.TipoDoc_ID) === String(sesion.TipoDoc_ID));
            if (selectTipoDoc && tipoDoc) {
                // Buscar la opción que coincida (por texto aproximado)
                const nombreTipo = tipoDoc.Nombre_Tipo_Documento || '';
                let encontrado = false;
                for (let i = 0; i < selectTipoDoc.options.length; i++) {
                    if (selectTipoDoc.options[i].text.toLowerCase().includes(nombreTipo.toLowerCase().split(' ')[0])) {
                        selectTipoDoc.selectedIndex = i;
                        encontrado = true;
                        break;
                    }
                }
                if (!encontrado && selectTipoDoc.options.length > 1) {
                    selectTipoDoc.selectedIndex = 1;
                }
            }
        }
    } catch (e) {
        console.warn('[agendar] No se pudo cargar tipo de documento:', e);
        // Seleccionar primera opción disponible como fallback
        const selectTipoDoc = document.getElementById('tipo-doc');
        if (selectTipoDoc && selectTipoDoc.options.length > 1) {
            selectTipoDoc.selectedIndex = 1;
        }
    }
}

function _setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

function _bloquearCampo(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.setAttribute('readonly', true);
    el.style.backgroundColor = '#f1f5f9';
    el.style.color = '#64748b';
    el.style.cursor = 'not-allowed';
    if (el.tagName === 'SELECT') {
        el.setAttribute('disabled', true);
        // Para selects disabled, creamos un input hidden para que el valor se envíe
        el.style.pointerEvents = 'none';
    }
}

// ─── Campo Fecha ─────────────────────────────────────────────────────────────
function inicializarCampoFechaAgendar() {
    const inputTexto    = document.getElementById('fecha');
    const inputNativo   = document.getElementById('fechaNativa');
    const btnCalendario = document.getElementById('datePickerBtnAgendar');

    if (!inputTexto || !inputNativo || !btnCalendario) return;

    // Establecer fecha mínima como hoy
    const hoy = new Date().toISOString().split('T')[0];
    inputNativo.min = hoy;

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

            // Validar que la fecha no sea anterior a hoy
            const errFecha = document.getElementById('err-fecha');
            if (!_validarFechaNoAnterior(isoDate)) {
                if (errFecha) {
                    errFecha.innerText = '⚠ No se puede agendar una cita con fecha anterior a la actual.';
                    errFecha.style.display = 'block';
                }
                mostrarError(inputTexto, null);
                inputNativo.value = '';
                fechaISOAgendar = '';
                // Limpiar horas
                const horaSelect = document.getElementById('hora');
                if (horaSelect) horaSelect.innerHTML = '<option value="" disabled selected>Seleccione la hora disponible</option>';
                return;
            } else {
                ocultarError(inputTexto, errFecha);
            }

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

        // Validar que la fecha no sea anterior a hoy
        const errFecha = document.getElementById('err-fecha');
        const inputTexto2 = document.getElementById('fecha');
        if (!_validarFechaNoAnterior(val)) {
            if (errFecha) {
                errFecha.innerText = '⚠ No se puede agendar una cita con fecha anterior a la actual.';
                errFecha.style.display = 'block';
            }
            mostrarError(inputTexto2, null);
            inputNativo.value = '';
            fechaISOAgendar = '';
            const horaSelect = document.getElementById('hora');
            if (horaSelect) horaSelect.innerHTML = '<option value="" disabled selected>Seleccione la hora disponible</option>';
            return;
        } else {
            ocultarError(inputTexto2, errFecha);
        }

        const [yyyy, mm, dd] = val.split('-');
        inputTexto.value = `${dd}/${mm}/${yyyy}`;
        fechaISOAgendar  = val;
        cargarAgenda();
    });
}

// ─── Validación de fecha no anterior a hoy ────────────────────────────────────
function _validarFechaNoAnterior(isoDate) {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fecha = new Date(isoDate + 'T00:00:00');
    return fecha >= hoy;
}

// ─── Validación de hora mínima (3 horas después si es hoy) ───────────────────
function _horaEsValida(horaStr, fechaISO) {
    const hoy = new Date().toISOString().split('T')[0];
    if (fechaISO !== hoy) return true; // Si no es hoy, todas las horas son válidas

    const ahora = new Date();
    const [h, m] = horaStr.split(':').map(Number);
    const horaSlot = new Date();
    horaSlot.setHours(h, m, 0, 0);

    // Mínimo 3 horas después de la hora actual
    const limiteMs = ahora.getTime() + (3 * 60 * 60 * 1000);
    return horaSlot.getTime() >= limiteMs;
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

    // Filtrar horas según validación de fecha/hora
    const horasFiltradas = HORAS_DEFAULT.filter(hora => _horaEsValida(hora, fecha));

    if (horasFiltradas.length === 0) {
        horaSelect.innerHTML = '<option value="" disabled selected>No hay horarios disponibles para hoy (mínimo 3 horas de anticipación)</option>';
        agendaDisponible = [];
        return;
    }

    agendaDisponible = horasFiltradas.map((hora, idx) => {
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

    // Validar fecha antes de cargar
    if (fecha && !_validarFechaNoAnterior(fecha)) {
        horaSelect.innerHTML = '<option value="" disabled selected>Fecha no válida</option>';
        return;
    }

    try {
        const params = new URLSearchParams();
        if (fecha) params.append('fecha', fecha);
        const res  = await fetch(`/api/agenda?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const slotsFiltrados = data
            .filter(slot => slot.Nombre_Especialidad === especialidad)
            .filter(slot => _horaEsValida(slot.Hora_Inicio, fecha));

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

// ─── POST /api/actualizar-perfil-paciente — sincronizar datos editados ────────
async function _sincronizarDatosPaciente() {
    const nombres   = document.getElementById('nombre')?.value.trim()    || '';
    const apellidos = document.getElementById('apellido')?.value.trim() || '';
    const documento = document.getElementById('num-doc')?.value.trim()  || '';
    const telefono  = document.getElementById('telefono')?.value.trim() || '';
    const correo    = document.getElementById('correo')?.value.trim()  || '';
    const tipoDocEl = document.getElementById('tipo-doc');
    const tipoDocId = tipoDocEl ? tipoDocEl.value : '';

    if (!_sesionPacienteAgendar || !_sesionPacienteAgendar.Usuario_ID) return;

    try {
        const res = await fetch('/api/actualizar-perfil-paciente', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                usuario_id:        _sesionPacienteAgendar.Usuario_ID,
                nombres,
                apellidos,
                documento,
                telefono,
                correo,
                tipo_documento_id: tipoDocId
            })
        });
        if (res.ok) {
            const data = await res.json();
            if (data.ok) {
                // Mantener la sesión local congruente con lo guardado en BD
                _sesionPacienteAgendar.Nombres         = nombres;
                _sesionPacienteAgendar.Apellidos       = apellidos;
                _sesionPacienteAgendar.NumeroDocumento = documento;
                _sesionPacienteAgendar.Telefono        = telefono;
                _sesionPacienteAgendar.Correo          = correo;
                _sesionPacienteAgendar.TipoDoc_ID       = tipoDocId;
                sessionStorage.setItem('odent_usuario', JSON.stringify(_sesionPacienteAgendar));
            }
        }
    } catch (e) {
        console.warn('[agendar] No se pudo sincronizar datos del paciente:', e);
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

        // Para el select tipo-doc que puede estar disabled, leer el value igualmente
        let rawVal;
        if (id === 'fecha') {
            rawVal = leerFechaISO();
        } else if (id === 'tipo-doc') {
            rawVal = input?.value;
        } else {
            rawVal = input?.value;
        }

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
        // Validar fecha no anterior a hoy
        if (!esInval && id === 'fecha') {
            const fechaISO = leerFechaISO();
            if (!_validarFechaNoAnterior(fechaISO)) {
                if (errEl) errEl.innerText = '⚠ No se puede agendar una cita con fecha anterior a la actual.';
                esInval = true;
            }
        }

        if (esInval) { mostrarError(input, errEl); valido = false; }
        else          ocultarError(input, errEl);
    });

    if (!valido) return;

    seleccionarSlot();
    if (!slotSeleccionado) { alert('Seleccione un horario disponible.'); return; }

    // Validación adicional de hora (mínimo 3 horas si es hoy)
    const fechaSeleccionada = leerFechaISO();
    if (!_horaEsValida(slotSeleccionado.Hora_Inicio, fechaSeleccionada)) {
        alert('La hora seleccionada debe ser al menos 3 horas posterior a la hora actual para citas del día de hoy.');
        return;
    }

    if (!_sesionPacienteAgendar || !_sesionPacienteAgendar.Usuario_ID) {
        alert('Sesión no válida. Por favor inicie sesión nuevamente.');
        window.location.replace('/login');
        return;
    }

    // ── VERIFICACIÓN SEGURA: identificar al paciente directamente desde el
    // endpoint /api/paciente/por-usuario (fuente única y confiable que ya
    // resuelve Paciente_ID a partir de la sesión activa) ───────────────────
    try {
        const resPac = await fetch(`/api/paciente/por-usuario/${_sesionPacienteAgendar.Usuario_ID}`);
        if (!resPac.ok) {
            alert('No se encontró el paciente en el sistema. Por favor contacte soporte.');
            return;
        }
        const pac = await resPac.json();
        if (!pac || !pac.Paciente_ID) {
            alert('No se encontró el paciente en el sistema. Por favor contacte soporte.');
            return;
        }
        pacienteIdAgendar = pac.Paciente_ID;

        // Sincronizar con la BD los datos del formulario (autocompletados o editados)
        await _sincronizarDatosPaciente();

        // Verificar multa activa
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

    // Mostrar resumen en modal usando datos de sesión ya sincronizados con la BD
    const fecha   = leerFechaISO();
    const resumen = document.getElementById('resumen');
    if (resumen) {
        const nombres   = _sesionPacienteAgendar.Nombres   || '';
        const apellidos = _sesionPacienteAgendar.Apellidos  || '';
        const numDoc    = _sesionPacienteAgendar.NumeroDocumento || '';
        const telefono  = _sesionPacienteAgendar.Telefono   || '';
        const tipoDocEl = document.getElementById('tipo-doc');
        const tipoDocTexto = tipoDocEl ? (tipoDocEl.options[tipoDocEl.selectedIndex]?.text || tipoDocEl.value) : '';

        resumen.innerHTML = `
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Paciente</span>
                <p style="font-size:14px;color:#1e293b;font-weight:600;margin:0;text-transform:uppercase;">
                    ${nombres} ${apellidos}
                </p>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Documento</span>
                    <p style="font-size:13px;color:#1e293b;margin:0;">${tipoDocTexto}: ${numDoc}</p>
                </div>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;display:block;margin-bottom:4px;">Teléfono</span>
                    <p style="font-size:13px;color:#1e293b;margin:0;">${telefono}</p>
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

    // Validación doble de fecha y hora antes de confirmar
    const fechaFinal = leerFechaISO();
    if (!fechaFinal || !_validarFechaNoAnterior(fechaFinal)) {
        cerrarModal();
        alert('La fecha seleccionada no es válida. No se puede agendar con fecha anterior a la actual.');
        return;
    }

    if (!_horaEsValida(slotSeleccionado.Hora_Inicio, fechaFinal)) {
        cerrarModal();
        alert('La hora seleccionada ya no es válida (debe ser al menos 3 horas posterior a la hora actual para citas de hoy).');
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

    // POST /api/citas — el backend valida Paciente_ID, Agenda_ID, fecha/hora
    // y la restricción de cita única consultando directamente la base de datos.
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

        // ── Manejo específico del rechazo por cita activa existente ───────────
        // El backend responde 409 (Conflict) cuando la consulta a la BD confirma
        // que el paciente ya tiene una cita Activa/Pendiente. En este caso NO se
        // limpia el formulario ni se cambia de pantalla: solo se cierra el modal
        // de verificación y se notifica al usuario para que pueda corregir/ver
        // su cita existente.
        if (res.status === 409) {
            cerrarModal();
            alert(data.error || 'No puedes agendar. Ya tienes una cita activa en el sistema.');
            return;
        }

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
    autocompletarDatosPaciente();
    cargarEspecialistas();
    document.getElementById('servicio')?.addEventListener('change', cargarAgenda);
    document.getElementById('hora')?.addEventListener('change', seleccionarSlot);
});