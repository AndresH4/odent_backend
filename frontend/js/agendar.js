        // --- FUNCIONES DE SOPORTE ---
        function mostrarError(el, p) { el.classList.add('input-error'); p.style.display = 'flex'; }
        function ocultarError(el, p) { el.classList.remove('input-error'); p.style.display = 'none'; }
        function validarEmail(email) { return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(String(email).toLowerCase()); }
        function cerrarVentanaYVolver() { window.close(); }

        function resetearFormulario() {
            const ids = ['nombre', 'apellido', 'tipo-doc', 'num-doc', 'telefono', 'correo', 'servicio', 'fecha', 'hora'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if(el) { el.value = ""; ocultarError(el, document.getElementById('err-' + id)); }
            });
        }

        function mostrarModalBloqueo(documento) {
            document.getElementById('mensajeBloqueo').innerHTML = `Ya existe una cita activa para el documento <b>${documento}</b>. <br><br> Por políticas del sistema, no se permite agendar más de una cita simultánea.`;
            document.getElementById('modalBloqueo').style.display = 'flex';
        }

        function cerrarModalBloqueo() { document.getElementById('modalBloqueo').style.display = 'none'; }
        function cerrarModal() { document.getElementById('modalVerificacion').style.display = 'none'; }

        // --- VALIDACIÓN PRINCIPAL ---
        function validarYAgendar() {
            const campos = ['nombre', 'apellido', 'tipo-doc', 'num-doc', 'telefono', 'correo', 'servicio', 'fecha', 'hora'];
            const regexLetras = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$/;
            let valido = true;

            campos.forEach(id => {
                const input = document.getElementById(id);
                const error = document.getElementById('err-' + id);
                let esInvalido = !input.value || input.value.trim() === "";
                
                // Texto de error unificado
                error.innerText = "⚠ Este campo es obligatorio.";

                if ((id === 'nombre' || id === 'apellido') && !esInvalido) {
                    if (!regexLetras.test(input.value)) {
                        error.innerText = "⚠ Caracteres no válidos.";
                        esInvalido = true;
                    }
                }
                
                if (id === 'telefono' && input.value.length !== 10 && !esInvalido) {
                    error.innerText = "⚠ El teléfono debe tener 10 dígitos.";
                    esInvalido = true;
                }
                
                if (id === 'correo' && !validarEmail(input.value) && !esInvalido) {
                    error.innerText = "⚠ Ingrese un correo válido.";
                    esInvalido = true;
                }
                
                if(esInvalido) { mostrarError(input, error); valido = false; } else { ocultarError(input, error); }
            });

            if(valido) {
                const numDocIngresado = document.getElementById('num-doc').value.trim();
                let citasTemporales = JSON.parse(localStorage.getItem('citasPacientes')) || [];
                let historialTotal = JSON.parse(localStorage.getItem('historialCompleto')) || [];
                
                if (citasTemporales.some(c => String(c.numDoc).trim() === numDocIngresado && c.estado === "Agendada") || 
                    historialTotal.some(c => String(c.numDoc).trim() === numDocIngresado && c.estado === "Agendada")) {
                    mostrarModalBloqueo(numDocIngresado);
                    return; 
                }

                const tieneMulta = historialTotal.some(c => String(c.numDoc).trim() === numDocIngresado && c.estado === "Cancelada con multa");
                const alerta = document.getElementById('alertaMulta');
                const header = document.getElementById('headerVerificacion');
                const btnFinal = document.getElementById('btnFinal');

                if (tieneMulta) {
                    alerta.classList.remove('hidden');
                    header.className = "bg-orange-600 p-4 text-center";
                    btnFinal.className = "flex-1 bg-orange-600 text-white py-3 rounded-xl font-bold hover:bg-orange-700 transition-all uppercase text-xs shadow-lg shadow-orange-200";
                } else {
                    alerta.classList.add('hidden');
                    header.className = "bg-blue-600 p-4 text-center";
                    btnFinal.className = "flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition-all uppercase text-xs shadow-lg shadow-blue-200";
                }

                document.getElementById('resumen').innerHTML = `
                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                        <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Paciente Registrado</span>
                        <p class="text-sm text-slate-800 font-semibold uppercase">${document.getElementById('nombre').value} ${document.getElementById('apellido').value}</p>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                            <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Documento</span>
                            <p class="text-sm text-slate-800">${document.getElementById('tipo-doc').value}: ${document.getElementById('num-doc').value}</p>
                        </div>
                        <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
                            <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Teléfono</span>
                            <p class="text-sm text-slate-800">${document.getElementById('telefono').value}</p>
                        </div>
                    </div>
                    <div class="bg-blue-50 p-3 rounded-lg border border-blue-100">
                        <span class="text-[10px] font-bold text-blue-600 uppercase block mb-1">Detalles del Servicio</span>
                        <p class="text-sm text-slate-800 font-bold uppercase">${document.getElementById('servicio').value}</p>
                        <p class="text-xs text-slate-600 mt-1"><i class="far fa-calendar-alt"></i> ${document.getElementById('fecha').value} | <i class="far fa-clock"></i> ${document.getElementById('hora').value}</p>
                    </div>
                `;
                document.getElementById('modalVerificacion').style.display = 'flex';
            }
        }

        function finalizarTodo() { 
            const numDoc = document.getElementById('num-doc').value.trim();
            let historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            const tieneMulta = historial.some(c => String(c.numDoc).trim() === numDoc && c.estado === "Cancelada con multa");

            const nuevaCita = {
                nombre: `${document.getElementById('nombre').value} ${document.getElementById('apellido').value}`,
                tipoDoc: document.getElementById('tipo-doc').value,
                numDoc: numDoc,
                telefono: document.getElementById('telefono').value,
                correo: document.getElementById('correo').value,
                especialidad: document.getElementById('servicio').value,
                fecha: document.getElementById('fecha').value,
                hora: document.getElementById('hora').value,
                tieneMultaPendiente: tieneMulta,
                estado: "Agendada",
                id: Date.now()
            };
            
            let citas = JSON.parse(localStorage.getItem('citasPacientes')) || [];
            citas.push(nuevaCita);
            localStorage.setItem('citasPacientes', JSON.stringify(citas));
            
            if(tieneMulta) {
                document.getElementById('mensajeExito').innerHTML = "Agendado con éxito. <br><b class='text-orange-600 uppercase'>Importante:</b> Debe pagar su multa pendiente en recepción.";
            } else {
                document.getElementById('mensajeExito').innerText = "Su cita ha sido procesada exitosamente. Gracias por confiar en nosotros.";
            }

            cerrarModal();
            document.getElementById('modalExito').style.display = 'flex';
        }

        function cerrarExitoYLimpiar() {
            document.getElementById('modalExito').style.display = 'none';
            resetearFormulario();
        }