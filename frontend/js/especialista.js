    /* * STYLO DENTAL PRO v2.5 - CORE ENGINE
     * Gestión de estado y persistencia de datos del especialista
     */

    let indexActualGlobal = null;
    let historialTotal = [];
    let seccionActiva = 'agenda';

    /**
     * Gestión de Interfaz de Usuario (UI)
     */
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
        const dia = ahora.getDay();
        const relojElem = document.getElementById('reloj');
        
        if (relojElem) {
            relojElem.innerText = ahora.toLocaleTimeString('es-CO', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit', 
                hour12: false 
            });
        }

        // Definición de horario: Lunes(1)-Viernes(5) 8am-6pm, Sábados(6) 8am-1pm
        const esHorarioLaboral = (dia >= 1 && dia <= 5 && horas >= 8 && horas < 18) || 
                                 (dia === 6 && horas >= 8 && horas < 13);
        
        const dot = document.getElementById('status-dot');
        const txt = document.getElementById('status-text');
        
        if (dot && txt) {
            dot.className = `status-dot ${esHorarioLaboral ? 'dot-active' : 'dot-inactive'}`;
            txt.innerText = esHorarioLaboral ? "Estado: En Jornada" : "Estado: Fuera de Horario";
            txt.style.color = esHorarioLaboral ? "#10b981" : "#ef4444";
        }
    };

    /**
     * Carga de Datos y Autenticación
     */
    const cargarInfoSesion = () => {
        const correoLogueado = localStorage.getItem('usuario_logueado');
        const dbUsuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
        const user = dbUsuarios[correoLogueado];

        if (user && user.rol === "Especialista") {
            const nombreCompleto = `${user.nombre} ${user.apellidos || ''}`.trim();
            const inicial = user.nombre.charAt(0).toUpperCase();

            // Actualización multicanal de UI
            const displays = {
                'doctor-nombre-display': nombreCompleto,
                'doctor-avatar': inicial,
                'avatar-grande': inicial,
                'nombre-menu': `Dr. ${nombreCompleto}`,
                'esp-menu': user.especialidad,
                'email-menu': user.correo,
                'tel-menu': user.celular || 'No asignado',
                'conf-nombre': nombreCompleto,
                'conf-email': user.correo,
                'conf-tel': user.celular || '',
                'esp-1': user.especialidad || 'Odontología General'
            };

            Object.entries(displays).forEach(([id, val]) => {
                const el = document.getElementById(id);
                if (el) el.tagName === 'INPUT' || el.tagName === 'SELECT' ? el.value = val : el.innerText = val;
            });
        } else {
            window.location.replace("login.html");
        }
    };

    const cargarDatosEspecialista = () => {
        historialTotal = JSON.parse(localStorage.getItem('historialCompleto')) || [];
        const tbody = document.getElementById('tabla-especialista');
        if (!tbody) return;

        tbody.innerHTML = '';
        let stats = { atendidos: 0, pendientes: 0, proxima: "--:--" };

        const hoyCitas = historialTotal.filter(c => !c.estado.toLowerCase().includes("cancelada"));

        hoyCitas.forEach((cita) => {
            const esAtendido = (cita.estado === "Atendido");
            esAtendido ? stats.atendidos++ : stats.pendientes++;
            
            if (!esAtendido && stats.proxima === "--:--") stats.proxima = cita.hora;

            if ((seccionActiva === 'agenda') || (seccionActiva === 'pacientes' && esAtendido)) {
                const idxReal = historialTotal.indexOf(cita);
                const row = document.createElement('tr');
                row.className = `transition-all duration-300 ${esAtendido ? 'bg-slate-50/50 opacity-80' : 'hover:bg-sky-50/30'}`;
                
                row.innerHTML = `
                    <td class="p-8"><p class="font-black text-slate-800 text-base">${cita.hora}</p><p class="text-[10px] text-slate-400 font-bold uppercase mt-1">${cita.fecha || 'Hoy'}</p></td>
                    <td class="p-8"><p class="font-black text-slate-700 uppercase text-xs tracking-tight">${cita.nombre}</p><p class="text-[11px] text-slate-400 font-bold mt-1">${cita.tipoDoc}: ${cita.numDoc}</p></td>
                    <td class="p-8 font-black text-sky-600 uppercase text-[11px] tracking-widest">${cita.especialidad}</td>
                    <td class="p-8"><span class="${esAtendido ? 'status-atendido' : 'status-pendiente'} uppercase"><i class="fas ${esAtendido?'fa-check-circle':'fa-clock'} mr-2"></i>${cita.estado}</span></td>
                    <td class="p-8 text-right">
                        ${!esAtendido ? 
                            `<button onclick="abrirModuloConsulta(${idxReal})" class="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black text-[10px] hover:bg-sky-600 transition-all uppercase shadow-lg btn-action">Atender</button>` : 
                            `<button onclick="verReporteProfesional(${idxReal})" class="text-sky-600 bg-sky-50 hover:bg-sky-100 w-14 h-14 rounded-2xl transition-all shadow-sm active:scale-95 flex items-center justify-center mx-auto"><i class="fas fa-file-medical text-2xl"></i></button>`
                        }
                    </td>`;
                tbody.appendChild(row);
            }
        });

        // Actualizar Widgets Numéricos
        document.getElementById('stat-total').innerText = hoyCitas.length;
        document.getElementById('stat-pendientes').innerText = stats.pendientes;
        document.getElementById('stat-atendidos').innerText = stats.atendidos;
        document.getElementById('stat-proxima').innerText = stats.proxima;
        document.getElementById('no-datos').classList.toggle('hidden', tbody.children.length > 0);
    };

    /**
     * Control de Navegación y Vistas
     */
    const cambiarSeccion = (nombreSeccion) => {
        seccionActiva = nombreSeccion;
        const config = {
            'agenda': { title: "Agenda Médica", table: "Pacientes del Día", stats: true },
            'pacientes': { title: "Mis Pacientes", table: "Archivo de Atenciones", stats: false },
            'config': { title: "Mi Perfil", table: "", stats: false }
        };

        const current = config[nombreSeccion];
        
        // Switch de visibilidad con animaciones
        document.getElementById('contenedor-stats').classList.toggle('hidden', !current.stats);
        document.getElementById('sec-tabla').classList.toggle('hidden', nombreSeccion === 'config');
        document.getElementById('sec-config').classList.toggle('hidden', nombreSeccion !== 'config');
        
        document.getElementById('main-title').innerText = current.title;
        const tabTitle = document.getElementById('tabla-titulo');
        if (tabTitle) tabTitle.innerText = current.table;

        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.id === `btn-${nombreSeccion}`);
        });

        cargarDatosEspecialista();
    };

    /**
     * Módulo de Atención Clínica
     */
    const abrirModuloConsulta = (indice) => {
        indexActualGlobal = indice;
        const cita = historialTotal[indice];
        localStorage.setItem('pacienteActivoDoc', cita.numDoc);

        const fields = {
            'paciente-nombre-modal': cita.nombre,
            'paciente-doc-modal': `${cita.tipoDoc} ID: ${cita.numDoc}`,
            'nota-clinica': cita.evolucion || '',
            'receta-clinica': cita.prescripcion || '',
            'diag-clinica': cita.cie10 || ''
        };

        Object.entries(fields).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value = val : el.innerText = val;
        });

        document.getElementById('modalConsulta').style.display = 'flex';
    };

    const finalizarAtencion = () => {
        const notaC = document.getElementById('nota-clinica').value.trim();
        const diagC = document.getElementById('diag-clinica').value.trim();

        if (!notaC || !diagC) {
            alert("⚠️ Registro incompleto: Debe ingresar la evolución y el diagnóstico clínico.");
            return;
        }

        const citaActual = historialTotal[indexActualGlobal];
        Object.assign(citaActual, {
            estado: "Atendido",
            evolucion: notaC,
            cie10: diagC,
            prescripcion: document.getElementById('receta-clinica').value.trim(),
            fechaAtencion: new Date().toLocaleString('es-CO')
        });

        // 🔗 Guardar también en historia clínica
        let historiaClinica = JSON.parse(localStorage.getItem('historia_clinica')) || [];

            historiaClinica.push({
            numDoc: citaActual.numDoc,
            nombre: citaActual.nombre,
            fecha: new Date().toLocaleString('es-CO'),
            diagnostico: citaActual.cie10,
            evolucion: citaActual.evolucion,
            tratamiento: citaActual.prescripcion
        });

localStorage.setItem('historia_clinica', JSON.stringify(historiaClinica));

        localStorage.setItem('historialCompleto', JSON.stringify(historialTotal));
        cerrarConsulta();
        alert("✅ Atención registrada con éxito en el servidor.");
        cargarDatosEspecialista();
    };

    const verReporteProfesional = (indice) => {
        const cita = historialTotal[indice];
        const mapping = {
            'rep-paciente': cita.nombre,
            'rep-fecha-atencion': `Finalizado el ${cita.fechaAtencion || 'N/A'}`,
            'rep-diagnostico': cita.cie10 || 'No codificado',
            'rep-evolucion': cita.evolucion || 'Sin registro',
            'rep-prescripcion': cita.prescripcion || 'Sin prescripción'
        };

        Object.entries(mapping).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        });

        document.getElementById('modalReporte').style.display = 'flex';
    };

    /**
     * Utilidades y Filtros
     */
    const filtrarTabla = () => {
        const query = document.getElementById('busqueda-paciente').value.toLowerCase();
        const filas = document.getElementById('tabla-especialista').getElementsByTagName('tr');
        let visibles = 0;

        Array.from(filas).forEach(fila => {
            const coincide = fila.innerText.toLowerCase().includes(query);
            fila.style.display = coincide ? "" : "none";
            if (coincide) visibles++;
        });

        document.getElementById('no-datos').classList.toggle('hidden', visibles > 0);
    };

    const guardarPerfilCompleto = () => {
        const correoActual = localStorage.getItem('usuario_logueado');
        const database = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
        const nuevoCorreo = document.getElementById('conf-email').value.trim();
        const nuevaPass = document.getElementById('conf-pass').value;

        if (database[correoActual]) {
            const nombreFull = document.getElementById('conf-nombre').value.trim();
            const [nombre, ...apellidos] = nombreFull.split(' ');
            
            const userRef = database[correoActual];
            userRef.nombre = nombre;
            userRef.apellidos = apellidos.join(' ');
            userRef.especialidad = document.getElementById('esp-1').value;
            userRef.celular = document.getElementById('conf-tel').value;
            userRef.correo = nuevoCorreo;

            if (nuevaPass && nuevaPass.length >= 4) userRef.password = nuevaPass;

            if (nuevoCorreo !== correoActual) {
                database[nuevoCorreo] = userRef;
                delete database[correoActual];
                localStorage.setItem('usuario_logueado', nuevoCorreo);
            }

            localStorage.setItem('usuarios_dental', JSON.stringify(database));
            alert("✨ Perfil actualizado correctamente.");
            cargarInfoSesion();
            cambiarSeccion('agenda');
        }
    };

    // Funciones de navegación rápida
    const cerrarConsulta = () => document.getElementById('modalConsulta').style.display = 'none';
    const irAHistoriaClinica = () => window.location.href = 'historia_clinica.html';
    const irAOdontograma = () => window.location.href = 'odontograma.html';
    
    const cerrarSesion = () => {
        if (confirm("¿Finalizar turno de especialista?")) {
            localStorage.removeItem('usuario_logueado');
            window.location.replace("login.html");
        }
    };

    // Inicialización del Sistema
    window.onload = () => {
        cargarInfoSesion();
        setInterval(actualizarRelojYEstado, 1000);
        actualizarRelojYEstado();
        cargarDatosEspecialista();
        
        const fechaStr = new Date().toLocaleDateString('es-CO', { 
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
        });
        document.getElementById('fecha-actual').innerText = fechaStr;
    };
