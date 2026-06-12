        let accionPendiente = null;
        let indexPendiente = null;

        function verificarSesion() {
            const sesion = localStorage.getItem('usuario_logueado');
            const usuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            if (!sesion || !usuarios[sesion]) {
                window.location.href = "login.html";
                return;
            }
            const datosUser = usuarios[sesion];
            document.getElementById('nombre-usuario').innerText = datosUser.nombre;
            document.getElementById('avatar-letras').innerText = datosUser.nombre.substring(0,2).toUpperCase();
        }

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
            const sesion = localStorage.getItem('usuario_logueado');
            const usuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            const user = usuarios[sesion];
            if(user) {
                const partesNombre = user.nombre.split(" ");
                document.getElementById('perfil-nombres').innerText = partesNombre[0] || '---';
                document.getElementById('perfil-apellidos').innerText = partesNombre.slice(1).join(" ") || '---';
                document.getElementById('perfil-tipoDoc').innerText = user.tipoDoc || '---';
                document.getElementById('perfil-numDoc').innerText = user.numDoc || '---';
                document.getElementById('perfil-correo').innerText = user.correo || sesion;
                document.getElementById('perfil-nacimiento').innerText = user.nacimiento || '---';
                document.getElementById('perfil-avatar-grande').innerText = user.nombre.substring(0,2).toUpperCase();
                document.getElementById('modalPerfil').style.display = 'flex';
            }
        }

        function cerrarModalPerfil() { document.getElementById('modalPerfil').style.display = 'none'; }

        /* LÓGICA CONFIGURACIÓN GENERAL */
        function abrirConfiguracion() {
            const sesion = localStorage.getItem('usuario_logueado');
            const usuarios = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            const user = usuarios[sesion];

            if(user) {
                document.getElementById('edit-correo').value = user.correo || sesion;
                document.getElementById('edit-telefono').value = user.telefono || '';
                document.getElementById('edit-nacimiento').value = user.nacimiento || '';
            }

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
            verificarSesion(); // Actualiza nombres si cambiaron
        }

        function actualizarReloj() {
            const ahora = new Date();
            const relojElem = document.getElementById('reloj');
            if(relojElem) relojElem.innerText = ahora.toLocaleTimeString('es-CO');
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
            verificarSesion(); 
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
            cargarCitas();
            setInterval(actualizarReloj, 1000);
            actualizarReloj();
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
                localStorage.removeItem('usuario_logueado');
                window.location.href = "login.html";
                return;
            }
            
            localStorage.setItem('historialCompleto', JSON.stringify(historial));
            cargarCitas();
        }