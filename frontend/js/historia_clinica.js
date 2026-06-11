        let dienteSeleccionadoActual = null;

        function init() {
            const sup = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28];
            const inf = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38];
            sup.forEach(n => document.getElementById('odo-sup').innerHTML += `<div class="diente shadow-sm" onclick="abrirSelector(this, ${n}, event)">${n}</div>`);
            inf.forEach(n => document.getElementById('odo-inf').innerHTML += `<div class="diente shadow-sm" onclick="abrirSelector(this, ${n}, event)">${n}</div>`);

            // --- CAMBIO SOLICITADO: Cargar datos específicos del paciente activo ---
            const docActivo = localStorage.getItem('pacienteActivoDoc');
            const historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            
            // Buscamos al paciente por el documento guardado en el localStorage
            const activa = historial.find(c => c.numDoc == docActivo);
            
            if(activa) {
                document.getElementById('p-full-name').innerText = `${activa.nombre} ${activa.apellidos || ''}`;
                document.getElementById('p-doc').innerText = activa.numDoc;
                document.getElementById('p-tel').innerText = activa.telefono || '--';
                document.getElementById('p-email').innerText = activa.correo || '--';
                document.getElementById('p-dir').innerText = activa.direccion || '--';
            } else {
                // Si no hay paciente seleccionado, enviamos de vuelta al panel
                alert("Por favor seleccione un paciente desde el panel.");
                window.location.href = 'panel_especialista.html';
            }
        }

        function abrirSelector(el, num, event) {
            event.stopPropagation();
            dienteSeleccionadoActual = el;
            document.getElementById('num-diente-sel').innerText = num;
            const selector = document.getElementById('selector-estado');
            selector.style.display = 'block';
            selector.style.top = `${el.offsetTop + 55}px`;
            selector.style.left = `${el.offsetLeft - 60}px`;
        }

        function asignarEstado(clase) {
            if(dienteSeleccionadoActual) {
                dienteSeleccionadoActual.classList.remove('azul', 'rojo', 'verde');
                if(clase) dienteSeleccionadoActual.classList.add(clase);
                document.getElementById('selector-estado').style.display = 'none';
            }
        }

        function cerrarSelector() { document.getElementById('selector-estado').style.display = 'none'; }

        function agregarFila() {
            const container = document.getElementById('lista-hallazgos');
            const nuevaFila = document.createElement('div');
            nuevaFila.className = "grid grid-cols-1 md:grid-cols-3 gap-4 items-end mt-4 animate-fade-in";
            nuevaFila.innerHTML = `
                <div class="md:col-span-1"><select class="select-odont"><option>Caries Detectada</option><option>Ausente</option><option>Endodoncia</option></select></div>
                <div class="md:col-span-2"><input type="text" class="input-clinical" placeholder="Detalles..."></div>
            `;
            container.appendChild(nuevaFila);
        }

        // --- CAMBIO SOLICITADO: Guardar datos y regresar al panel del especialista ---
        function guardarTodo() { 
            const conf = confirm("¿Desea finalizar la consulta y guardar los cambios?");
            if(conf) {
                const docActivo = localStorage.getItem('pacienteActivoDoc');
                let historial = JSON.parse(localStorage.getItem('historialCompleto')) || [];
                
                // Buscar el índice del paciente para actualizarlo
                const index = historial.findIndex(p => p.numDoc == docActivo);

                if (index !== -1) {
                    // Guardamos la información capturada
                    historial[index].estado = "Atendido";
                    historial[index].motivo = document.getElementById('hc-motivo').value;
                    historial[index].evolucion = document.getElementById('hc-evolucion').value;
                    historial[index].diagnostico = document.getElementById('hc-diag').value;
                    historial[index].plan = document.getElementById('hc-plan').value;
                    historial[index].fechaAtencion = new Date().toLocaleString();

                    // Guardamos en el almacenamiento local
                    localStorage.setItem('historialCompleto', JSON.stringify(historial));
                    
                    // Limpiamos la referencia temporal
                    localStorage.removeItem('pacienteActivoDoc');

                    alert("✅ Consulta Guardada Exitosamente. Regresando al panel...");
                    
                    // Redirigir al panel del especialista
                    window.location.href = 'especialista.html';
                }
            }
        }

        // ADICIÓN DE LÓGICA DE ATENCIÓN DIRECTA (CONEXIÓN CON PANEL ESPECIALISTA)
        // Esta función se encarga de que si llegas aquí mediante una redirección, 
        // sepa exactamente qué paciente estás atendiendo.
        function sincronizarDesdePanel() {
            const urlParams = new URLSearchParams(window.location.search);
            const docParam = urlParams.get('doc');
            if(docParam) {
                localStorage.setItem('pacienteActivoDoc', docParam);
                init(); // Recargar datos con el nuevo documento
            }
        }

        window.onload = function() {
            sincronizarDesdePanel();
            init();
        };