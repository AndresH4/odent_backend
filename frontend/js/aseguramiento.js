        function mostrarError(el, p, msg) {
            el.classList.add('input-error');
            p.innerText = msg;
            p.style.display = 'block';
        }

        function ocultarError(el, p) {
            el.classList.remove('input-error');
            p.style.display = 'none';
        }

        function validarYProcesar(accion) {
            const inputs = {
                nombre: [document.getElementById('nombre'), document.getElementById('err-nombre')],
                doc: [document.getElementById('num-doc'), document.getElementById('err-documento')],
                tel: [document.getElementById('telefono'), document.getElementById('err-telefono')],
                email: [document.getElementById('correo'), document.getElementById('err-correo')],
                dir: [document.getElementById('direccion'), document.getElementById('err-direccion')],
                tipo: [document.getElementById('tipo-doc'), document.getElementById('err-tipo-doc')]
            };

            let todoValido = true;
            const regexSoloNumeros = /^[0-9]+$/;
            const regexEmail = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

            // Nombre
            if (inputs.nombre[0].value.trim() === "") { mostrarError(inputs.nombre[0], inputs.nombre[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else if (/\d/.test(inputs.nombre[0].value)) { mostrarError(inputs.nombre[0], inputs.nombre[1], "❌ Información incorrecta: Sin números."); todoValido = false; }
            else { ocultarError(inputs.nombre[0], inputs.nombre[1]); }

            // Documento (MAX 10)
            if (inputs.doc[0].value.trim() === "") { mostrarError(inputs.doc[0], inputs.doc[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else if (!regexSoloNumeros.test(inputs.doc[0].value) || inputs.doc[0].value.length > 10) { mostrarError(inputs.doc[0], inputs.doc[1], "❌ Información incorrecta: Solo números (Máximo 10)."); todoValido = false; }
            else { ocultarError(inputs.doc[0], inputs.doc[1]); }

            // Teléfono (EXACTO 10)
            if (inputs.tel[0].value.trim() === "") { mostrarError(inputs.tel[0], inputs.tel[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else if (!regexSoloNumeros.test(inputs.tel[0].value) || inputs.tel[0].value.length !== 10) { mostrarError(inputs.tel[0], inputs.tel[1], "❌ Información incorrecta: Debe tener exactamente 10 números."); todoValido = false; }
            else { ocultarError(inputs.tel[0], inputs.tel[1]); }

            // Correo
            if (inputs.email[0].value.trim() === "") { mostrarError(inputs.email[0], inputs.email[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else if (!regexEmail.test(inputs.email[0].value)) { mostrarError(inputs.email[0], inputs.email[1], "❌ Información incorrecta: Formato de correo inválido."); todoValido = false; }
            else { ocultarError(inputs.email[0], inputs.email[1]); }

            // Dirección
            if (inputs.dir[0].value.trim() === "") { mostrarError(inputs.dir[0], inputs.dir[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else { ocultarError(inputs.dir[0], inputs.dir[1]); }

            // Tipo Doc
            if (inputs.tipo[0].value === "") { mostrarError(inputs.tipo[0], inputs.tipo[1], "⚠️ Este campo es obligatorio."); todoValido = false; }
            else { ocultarError(inputs.tipo[0], inputs.tipo[1]); }

            if (!document.getElementById('terminos').checked) { alert('⚠️ Debe aceptar el tratamiento de datos.'); todoValido = false; }

            if (todoValido) alert(accion === 'asegurar' ? '✅ Datos asegurados correctamente.' : '🔄 Información actualizada.');
        }