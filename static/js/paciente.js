
        let accionPendiente = null;
        let indexPendiente = null;

        const cargarInfoSesionPaciente = () => {
            const raw = sessionStorage.getItem('odent_usuario');
            const user = raw ? JSON.parse(raw) : null;
 
            // 2. Fallback a localStorage por compatibilidad con el flujo anterior
            const correoLogueado = localStorage.getItem('usuario_logueado');
            const dbUsuarios     = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            const userLegacy     = dbUsuarios[correoLogueado] || dbUsuarios[raw]; // Soporta ambas llaves
        
            // 3. Seleccionar el usuario definitivo (Prioriza sessionStorage o valida el legacy)
            const u = user || (userLegacy && userLegacy.rol === 'Paciente' ? userLegacy : userLegacy);
        
            // 4. Protección de ruta: Si no hay usuario, redirigir al login controlado por Flask
            if (!u) {
                window.location.replace('/login');
                return;
            }
        
            // 5. Normalizar campos (Traduce si viene con Nombres/Apellidos o nombre/apellidos)
            const nombreCompleto = u.Nombres
                ? `${u.Nombres} ${u.Apellidos || ''}`.trim()
                : `${u.nombre || ''} ${u.apellidos || ''}`.trim();
        
            const inicial       = nombreCompleto.charAt(0).toUpperCase();
            const correo        = u.Correo       || u.correo       || '';
            const telefono      = u.Telefono     || u.telefono     || 'No asignado';
            const nacimiento    = u.Nacimiento   || u.nacimiento   || '---';
            const tipoDoc       = u.TipoDoc      || u.tipoDoc      || '---';
            const numDoc        = u.NumDoc       || u.numDoc       || '---';
        
            // 6. Mapear los IDs específicos que existen en tu paciente.html
            const displays = {
                'nombre-usuario':        nombreCompleto,   // Reemplaza el "Bienvenido de nuevo, Paciente"
                'avatar-letras':         inicial,          // El avatar de la esquina superior
                'perfil-avatar-grande':  inicial,          // El avatar dentro del modal de perfil
                'perfil-nombres':        u.Nombres   || u.nombre || '---',
                'perfil-apellidos':      u.Apellidos || u.apellidos || '---',
                'perfil-tipoDoc':        tipoDoc,
                'perfil-numDoc':         numDoc,
                'perfil-correo':         correo,
                'perfil-nacimiento':     nacimiento,
                // Campos para los inputs del formulario de configuración de cuenta
                'edit-correo':           correo,
                'edit-telefono':         telefono,
                'edit-nacimiento':       nacimiento
            };
        
            // 7. Recorrer y aplicar los cambios automáticamente en el DOM
            Object.entries(displays).forEach(([id, val]) => {
                const el = document.getElementById(id);
                if (el) {
                    (el.tagName === 'INPUT' || el.tagName === 'SELECT')
                        ? el.value     = val
                        : el.innerText = val;
                }
            });
        };

        function cambiarVista(vista) {
            const inicio = document.getElementById('vista-inicio');
            const historial = document.getElementById('vista-historial');
            const btnInicio = document.getElementById('btn-inicio');
            const btnHistorial = document.getElementById('btn-historial');
            const titulo = document.getElementById('titulo-principal');

            if (vista === 'inicio') {
                inicio.classList.remove('hidden');
                historial.classList.add('hidden');
                btnInicio.classList.add('active');
                btnHistorial.classList.remove('active');
                titulo.innerText = "Panel de Control";
                cargarCitas();
            } else {
                inicio.classList.add('hidden');
                historial.classList.remove('hidden');
                btnInicio.classList.remove('active');
                btnHistorial.classList.add('active');
                titulo.innerText = "Historial Completo";
                generarHistorialCompleto();
            }
        }

        function generarHistorialCompleto() {
            const historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            const tbody = document.getElementById('tabla-historial-completo');
            tbody.innerHTML = '';
            [...historial].reverse().forEach((c, i) => {
                const originalIndex = historial.length - 1 - i;
                let badgeClass = "status-agendada";
                if(c.estado === "Cancelada") badgeClass = "status-cancelada";
                if(c.estado === "Cancelada con multa") badgeClass = "status-multa";

                tbody.innerHTML += `
                    <tr class="hover:bg-slate-50">
                        <td class="p-5 font-bold text-slate-700">${c.fecha}<br><span class="text-[10px] text-slate-400 font-black">${c.hora}</span></td>
                        <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">${c.especialidad}</td>
                        <td class="p-5 font-bold uppercase text-xs text-slate-500">Stylo Dental Service</td>
                        <td class="p-5"><span class="${badgeClass}">${c.estado}</span></td>
                        <td class="p-5 text-center">
                            <button onclick="verificarYPreparar(${originalIndex})" class="bg-slate-100 text-slate-600 px-3 py-1 rounded-lg text-[10px] font-black uppercase hover:bg-sky-600 hover:text-white transition-all">Ver Datos</button>
                        </td>
                    </tr>`;
            });
        }

        function abrirModalPerfil() {
        cargarInfoSesionPaciente(); // Se asegura de tener los datos frescos
        document.getElementById('modalPerfil').style.display = 'flex';
        }

        function cerrarModalPerfil() { document.getElementById('modalPerfil').style.display = 'none'; }

        /* LÓGICA CONFIGURACIÓN GENERAL */
        function abrirConfiguracion() {
            cargarInfoSesionPaciente(); // Rellena los inputs de configuración
            cerrarModalPerfil();
        document.getElementById('modalConfig').style.display = 'flex';
        }

        function cerrarConfiguracion() {
            document.getElementById('modalConfig').style.display = 'none';
            document.getElementById('nueva-pass').value = '';
            document.getElementById('confirmar-pass').value = '';
        }

        function guardarConfiguracionGeneral() {
            const sesion = localStorage.getItem('usuario_logueado');
            const usuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            
            const nuevoCorreo = document.getElementById('edit-correo').value.trim();
            const nuevoTel = document.getElementById('edit-telefono').value.trim();
            const nuevaFecha = document.getElementById('edit-nacimiento').value;
            const nuevaPass = document.getElementById('nueva-pass').value;
            const confirmPass = document.getElementById('confirmar-pass').value;

            if(!nuevoCorreo) { alert("El correo es obligatorio."); return; }

            // Lógica de contraseña solo si escribe algo
            if (nuevaPass) {
                if (nuevaPass.length < 6) {
                    alert("La contraseña debe tener al menos 6 caracteres.");
                    return;
                }
                if (nuevaPass !== confirmPass) {
                    alert("Las contraseñas no coinciden.");
                    return;
                }
                usuarios[sesion].password = nuevaPass;
            }

            // Actualizar datos
            usuarios[sesion].correo = nuevoCorreo;
            usuarios[sesion].telefono = nuevoTel;
            usuarios[sesion].nacimiento = nuevaFecha;

            localStorage.setItem('usuarios_dental', JSON.stringify(usuarios));
            alert("¡Perfil actualizado con éxito!");
            cerrarConfiguracion();
            cargarInfoSesionPaciente(); // Actualiza nombres si cambiaron
        }

        function actualizarReloj() {
            const relojElem = document.getElementById('reloj');
            if (relojElem) {
                const ahora = new Date();
                relojElem.innerText = ahora.toLocaleTimeString('es-CO');
            }
        }

        function auditarFechas(historial) {
            const ahora = new Date();
            let huboCambios = false;
            historial.forEach(cita => {
                if (cita.estado === "Agendada") {
                    const [horaStr, meridiano] = cita.hora.split(' ');
                    let [horas, minutos] = horaStr.split(':');
                    horas = parseInt(horas);
                    if (meridiano === "PM" && horas !== 12) horas += 12;
                    if (meridiano === "AM" && horas === 12) horas = 0;
                    const fechaCita = new Date(`${cita.fecha}T${horas.toString().padStart(2, '0')}:${minutos}:00`);
                    if (fechaCita < ahora) {
                        cita.estado = "Cancelada con multa";
                        huboCambios = true;
                    }
                }
            });
            return huboCambios;
        }

        function cargarCitas() {
            cargarInfoSesionPaciente();
            let citasEntrantes = JSON.parse(localStorage.getItem('citasPacientes')) || [];
            let historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            
            if (citasEntrantes.length > 0) {
                citasEntrantes.forEach(cita => {
                    cita.estado = "Agendada"; 
                    cita.ocultoEnPrincipal = false; 
                    historial.push(cita); 
                });
                localStorage.setItem('historialCompleto', JSON.stringify(historial));
                localStorage.removeItem('citasPacientes');
            }

            if (auditarFechas(historial)) {
                localStorage.setItem('historialCompleto', JSON.stringify(historial));
            }

            const tbody = document.getElementById('tabla-citas-body');
            const countCitas = document.getElementById('count-citas');
            tbody.innerHTML = '';
            
            const visibles = historial.filter(c => !c.ocultoEnPrincipal);
            countCitas.innerText = visibles.length;

            if (visibles.length === 0) { 
                document.getElementById('no-citas-msg').classList.remove('hidden'); 
            } else {
                document.getElementById('no-citas-msg').classList.add('hidden');
                historial.forEach((c, originalIndex) => {
                    if (c.ocultoEnPrincipal) return; 

                    let badgeClass = "status-agendada";
                    if(c.estado === "Cancelada") badgeClass = "status-cancelada";
                    if(c.estado === "Cancelada con multa") badgeClass = "status-multa";

                    const row = `
                        <tr class="hover:bg-slate-50 transition-colors">
                            <td class="p-5 font-black text-slate-800 uppercase text-xs">${c.nombre}</td>
                            <td class="p-5 text-[10px] font-bold uppercase tracking-tighter">${c.tipoDoc}<br><span class="text-slate-400 font-medium">${c.numDoc}</span></td>
                            <td class="p-5 font-black text-sky-600 uppercase text-[10px] tracking-widest">${c.especialidad}</td>
                            <td class="p-5 font-bold uppercase text-xs">${c.fecha}<br><span class="text-slate-400 text-[10px] tracking-tighter">${c.hora}</span></td>
                            <td class="p-5"><span class="${badgeClass}">${c.estado}</span></td>
                            <td class="p-5 text-center">
                                ${c.estado === "Agendada" ? 
                                `<button onclick="verificarYPreparar(${originalIndex})" class="text-red-400 hover:text-red-600 p-2 transition-transform hover:scale-125"><i class="fas fa-ban"></i></button>` : 
                                `<button onclick="mostrarConfirmacionSimple('¿Quitar de la vista principal? Seguirá en su historial.', 'eliminar', ${originalIndex})" class="text-slate-300 hover:text-red-500 p-2 transition-transform hover:scale-125"><i class="fas fa-eye-slash"></i></button>`}
                            </td>
                        </tr>`;
                    tbody.insertAdjacentHTML('afterbegin', row);
                });
            }
        }

        window.onfocus = cargarCitas;
        window.onload = () => {
    // Primero inicializamos el reloj para que sea independiente
    actualizarReloj();
    setInterval(actualizarReloj, 1000);
    
    // Luego cargamos las citas (si esto falla, no afectará al reloj)
    try {
        cargarCitas();
    } catch (error) {
        console.error("Error al cargar las citas o validar sesión:", error);
    }
};

        function verificarYPreparar(index) {
            indexPendiente = index;
            const historial = JSON.parse(localStorage.getItem('historialCompleto'));
            const cita = historial[index];
            document.getElementById('detalles-completos').innerHTML = `
                <div><p class="data-label">Nombre</p><p class="data-value uppercase">${cita.nombre}</p></div>
                <div><p class="data-label">Documento</p><p class="data-value uppercase">${cita.tipoDoc} ${cita.numDoc}</p></div>
                <div class="col-span-2 mt-2"><p class="data-label">Especialidad</p><p class="data-value uppercase text-sky-700 font-black tracking-widest">${cita.especialidad}</p></div>
                <div><p class="data-label">Fecha</p><p class="data-value">${cita.fecha}</p></div>
                <div><p class="data-label">Hora</p><p class="data-value">${cita.hora}</p></div>
            `;
            document.getElementById('modalCancelarCita').style.display = 'flex';
        }

        function solicitarConfirmacionFinal() {
            document.getElementById('modalCancelarCita').style.display = 'none';
            document.getElementById('modalConfirmacionFinal').style.display = 'flex';
        }

        function confirmarAccionCancelado() {
            cerrarConfirmacionFinal();
            let historial = JSON.parse(localStorage.getItem('historialCompleto'));
            historial[indexPendiente].estado = "Cancelada";
            localStorage.setItem('historialCompleto', JSON.stringify(historial));
            cargarCitas();
        }

        function cerrarConfirmacionFinal() { document.getElementById('modalConfirmacionFinal').style.display = 'none'; }
        function cerrarModalCancelar() { document.getElementById('modalCancelarCita').style.display = 'none'; }
        
        function mostrarConfirmacionSimple(mensaje, tipo, index = null) {
            accionPendiente = tipo;
            indexPendiente = index;
            document.getElementById('confirm-text-simple').innerText = mensaje;
            document.getElementById('modalConfirmarSimple').style.display = 'flex';
        }
        
        function cerrarModalSimple() { document.getElementById('modalConfirmarSimple').style.display = 'none'; }

        function ejecutarAccionSimple() {
            cerrarModalSimple();
            let historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            
            if (accionPendiente === 'eliminar') {
                historial[indexPendiente].ocultoEnPrincipal = true;
            } else if (accionPendiente === 'limpiar') {
                historial.forEach(cita => {
                    if(cita.estado === "Cancelada" || cita.estado === "Cancelada con multa") {
                        cita.ocultoEnPrincipal = true;
                    }
                });
            } else if (accionPendiente === 'salir') {
                // CORRECCIÓN 1: Limpiar la sesión real de 'odent_usuario'
                sessionStorage.removeItem('odent_usuario');
                
                // Opcional: Si también usabas esta llave en otras partes, la removemos
                localStorage.removeItem('usuario_logueado'); 
                
                // CORRECCIÓN 2: Redirigir a la ruta controlada por Flask
                window.location.href = "/login";
                return;
            }
            
            localStorage.setItem('historialCompleto', JSON.stringify(historial));
            cargarCitas();
        }
    