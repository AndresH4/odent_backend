        /** * LÓGICA INTEGRADA - STYLO DENTAL 2026 */        let adminData = { nombre: "Admin Root", email: "admin@stylodental.com", tel: "+57 322 456 7890", pass: "Admin123*" };

        function toggleProfileDropdown() {
            document.getElementById('profileDropdown').classList.toggle('active');
        }

        window.addEventListener('click', (e) => {
            if (!e.target.closest('#profileDropdown') && !e.target.closest('header .cursor-pointer')) {
                document.getElementById('profileDropdown').classList.remove('active');
            }
        });

        function actualizarReloj() {
            const ahora = new Date();
            document.getElementById('reloj').innerText = ahora.toLocaleTimeString('es-CO');
            document.getElementById('fecha-actual').innerText = ahora.toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        }
        setInterval(actualizarReloj, 1000); actualizarReloj();

        function cambiarSeccion(sec) {
            document.getElementById('sec-dashboard').classList.toggle('hidden', sec !== 'dashboard');
            document.getElementById('sec-tablas').classList.toggle('hidden', sec === 'dashboard');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-dashboard').classList.toggle('active', sec==='dashboard');
            if(sec === 'citas') { renderCitas(); document.getElementById('btn-citas').classList.add('active'); }
        }

        function renderUsuarios(rol) {
            const u = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            const body = document.getElementById('body-lista-dinamica');
            document.getElementById('container-lista-rapida').classList.remove('hidden');
            document.getElementById('titulo-lista-dinamica').innerText = `GESTIÓN: ${rol}S`;
            body.innerHTML = Object.keys(u).filter(e => u[e].rol === rol).map(email => `
                <tr class="p-4 flex justify-between items-center px-8 hover:bg-sky-50/50 transition-all">
                    <td><p class="font-black text-slate-800 text-[11px] uppercase">${u[email].nombre}</p><p class="text-[9px] text-slate-400 font-bold">${email}</p></td>
                    <td><button onclick="preguntarEliminar('${email}')" class="text-red-300 hover:text-red-600 transition-all text-sm"><i class="fas fa-user-minus"></i></button></td>
                </tr>`).join('');
        }

        function renderCitas() {
            document.getElementById('main-title').innerText = "Historial General de Citas";
            const h = JSON.parse(localStorage.getItem('historialCompleto')) || [];
            const body = document.getElementById('tabla-body');
            document.getElementById('tabla-head').innerHTML = `<tr><th class="p-6">Paciente</th><th class="p-6">Especialista</th><th class="p-6">Procedimiento</th></tr>`;
            body.innerHTML = h.map(c => `
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="p-6 font-bold text-slate-800 text-[11px] uppercase">${c.nombre}</td>
                    <td class="p-6 text-[10px] font-black text-slate-600 uppercase"><i class="fas fa-user-md mr-2 text-sky-500"></i> ${c.especialista || 'No Asignado'}</td>
                    <td class="p-6 text-sky-600 font-black text-[10px] uppercase">${c.especialidad}</td>
                </tr>`).join('');
        }

        function abrirConfiguracion() {
            document.getElementById('edit-nombre').value = adminData.nombre;
            document.getElementById('edit-email').value = adminData.email;
            document.getElementById('edit-tel').value = adminData.tel;
            document.getElementById('modalConfig').style.display = 'flex';
        }

        function guardarPerfil() {
            adminData.nombre = document.getElementById('edit-nombre').value;
            adminData.email = document.getElementById('edit-email').value;
            adminData.tel = document.getElementById('edit-tel').value;
            mostrarToast("PERFIL ACTUALIZADO");
            cerrarConfiguracion();
            actualizarInterfazHeader();
        }

        function actualizarInterfazHeader() {
            document.getElementById('header-name').innerText = adminData.nombre;
            document.getElementById('drop-name').innerText = adminData.nombre;
            document.getElementById('drop-email').innerText = adminData.email;
            document.getElementById('drop-tel').innerText = adminData.tel;
            document.getElementById('header-pic').src = `https://ui-avatars.com/api/?name=${adminData.nombre.replace(" ","+")}&background=0284c7&color=fff&size=128`;
        }

        function verificarOldPass() {
            if(document.getElementById('old-pass').value === adminData.pass) {
                document.getElementById('step-1').classList.add('hidden');
                document.getElementById('step-2').classList.remove('hidden');
            } else { alert("CONTRASEÑA INCORRECTA"); }
        }

        function mostrarToast(msg) {
            // Lógica de toast si existe el elemento en el HTML, si no alert
            alert(msg);
        }

        function togglePass(id) { const i = document.getElementById(id); i.type = i.type === 'password' ? 'text' : 'password'; }
        function cerrarConfiguracion() { document.getElementById('modalConfig').style.display = 'none'; document.getElementById('step-1').classList.remove('hidden'); document.getElementById('step-2').classList.add('hidden'); }
        
        function actualizarStats() {
            const u = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
            document.getElementById('stat-esp').innerText = Object.values(u).filter(x => x.rol === 'Especialista').length;
            document.getElementById('stat-pac').innerText = Object.values(u).filter(x => x.rol === 'Paciente').length;
        }

        window.onload = () => { actualizarStats(); actualizarInterfazHeader(); };