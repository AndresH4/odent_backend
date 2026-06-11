let codigoGenerado="";
let esMenor=false;

function soloLetras(input){
    input.value=input.value.replace(/[^a-zA-ZÁÉÍÓÚáéíóúñÑ\s]/g,'');
}

function soloNumeros(input){
    input.value=input.value.replace(/\D/g,'');
}

document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll("#nombres,#apellidos,#nombresAcudiente,#apellidosAcudiente")
    .forEach(el=>el.addEventListener("input",function(){soloLetras(this)}));

    document.querySelectorAll("#telefono,#documento,#telefonoAcudiente")
    .forEach(el=>el.addEventListener("input",function(){soloNumeros(this)}));

    document.getElementById("tipoDocumento").addEventListener("change", checkRequisitosAcudiente);

});

// FUNCIÓN PARA VERIFICAR LA EDAD AUTOMÁTICAMENTE
function verificarEdad() {
    const fecha = document.getElementById("fechaNacimiento").value;
    if (!fecha) return;

    const hoy = new Date();
    const cumple = new Date(fecha);
    let edad = hoy.getFullYear() - cumple.getFullYear();
    const m = hoy.getMonth() - cumple.getMonth();

    if (m < 0 || (m === 0 && hoy.getDate() < cumple.getDate())) {
        edad--;
    }

    esMenor = (edad < 18);
    checkRequisitosAcudiente();
}

function checkRequisitosAcudiente() {
    const tipoDoc = document.getElementById("tipoDocumento").value;
    
    if (tipoDoc === "Tarjeta de identidad" || esMenor) {
        acudienteSection.style.display = "block";
        document.getElementById("correoUsuarioGroup").style.display = "none";
        
        if (esMenor) {
            document.getElementById("tipoDocumento").value = "Tarjeta de identidad";
        }
        replicarCorreoAcudiente();
    } else {
        acudienteSection.style.display = "none";
        document.getElementById("correoUsuarioGroup").style.display = "flex";
    }
}

function checkRolEspecialista() {
    const rol = document.getElementById("rolUsuario").value;
    const extra = document.getElementById("especialistaExtra");
    if(rol === "Especialista") {
        extra.style.display = "block";
    } else {
        extra.style.display = "none";
    }
}

function replicarCorreoAcudiente() {
    if (acudienteSection.style.display === "block") {
        document.getElementById("emailAcudiente").value = document.getElementById("email").value;
    }
}

function validarEmail(email){
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function limpiarErrores(){
    document.querySelectorAll(".error-msg").forEach(e=>e.innerText="");
    document.querySelectorAll("input, select").forEach(i=>i.classList.remove("invalid"));
}

function validarPaso1(){
    limpiarErrores();
    let valido=true;

    if(nombres.value.length<2){
        nombres.classList.add("invalid");
        errorNombres.innerText="Ingrese sus nombres.";
        valido=false;
    }

    if(apellidos.value.length<2){
        apellidos.classList.add("invalid");
        errorApellidos.innerText="Ingrese sus apellidos.";
        valido=false;
    }

    if(!fechaNacimiento.value){
        fechaNacimiento.classList.add("invalid");
        errorFecha.innerText="Seleccione su fecha de nacimiento.";
        valido=false;
    }

    if(!rolUsuario.value){
        rolUsuario.classList.add("invalid");
        errorRol.innerText="Seleccione un rol.";
        valido=false;
    }

    if(documento.value.length<5){
        documento.classList.add("invalid");
        errorDocumento.innerText="Documento no válido.";
        valido=false;
    }

    if(telefono.value.length!==10){
        telefono.classList.add("invalid");
        errorTelefono.innerText="El teléfono debe tener 10 dígitos.";
        valido=false;
    }

    const emailAValidar = (document.getElementById("correoUsuarioGroup").style.display === "none") ? emailAcudiente.value : email.value;

    if(!validarEmail(emailAValidar)){
        if(document.getElementById("correoUsuarioGroup").style.display === "none"){
            emailAcudiente.classList.add("invalid");
            errorEmailAcudiente.innerText="Ingrese un correo electrónico válido.";
        } else {
            email.classList.add("invalid");
            errorEmail.innerText="Ingrese un correo electrónico válido.";
        }
        valido=false;
    }

    if(valido){
        codigoGenerado=Math.floor(100000+Math.random()*900000);
        alert("Código generado: "+codigoGenerado);
        step1.classList.remove("active");
        step2.classList.add("active");
    }
}

function verificarCodigo(){
    if(codigo.value==codigoGenerado){
        step2.classList.remove("active");
        step3.classList.add("active");
    }else{
        errorCodigo.innerText="Código incorrecto.";
    }
}

function validarPassword(pass){
    return /^(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/.test(pass);
}

function crearUsuario(){
    limpiarErrores();

    if(!validarPassword(password.value)){
        password.classList.add("invalid");
        errorPassword.innerText="La contraseña no cumple los requisitos.";
        return;
    }

    if(password.value!==confirmPassword.value){
        confirmPassword.classList.add("invalid");
        errorConfirm.innerText="Las contraseñas no coinciden.";
        return;
    }

    const correoRegistro = (document.getElementById("correoUsuarioGroup").style.display === "none" ? emailAcudiente.value : email.value).toLowerCase();
    const rolSeleccionado = document.getElementById("rolUsuario").value;
    const especialidadSeleccionada = document.getElementById("especialidadMedica").value;
    
    let tabsConfig = ["Inicio"];
    let btnConfig = "Ver perfil";

    if(rolSeleccionado === "Paciente") {
        tabsConfig = ["Panel de citas", "Historial Personal"];
        btnConfig = "Agendar cita";
    } else if(rolSeleccionado === "Especialista") {
        tabsConfig = ["Agenda", "Pacientes", "Ranking"];
        btnConfig = "Ver mi agenda";
    } else if(rolSeleccionado === "Administrador") {
        tabsConfig = ["Usuarios", "Citas", "Sistema"];
        btnConfig = "Gestionar Sistema";
    }

    const nuevoUsuario = {
        nombre: nombres.value + " " + apellidos.value,
        pass: password.value,
        rol: rolSeleccionado,
        especialidad: especialidadSeleccionada,
        email: correoRegistro,
        esMenor: esMenor, 
        foto: "", 
        data: [
            ["Documento", documento.value],
            ["Tipo", document.getElementById("tipoDocumento").value],
            ["Estado", "Activo"]
        ],
        btn: btnConfig,
        tabs: tabsConfig
    };

    let dbLocal = JSON.parse(localStorage.getItem('usuarios_dental')) || {};
    dbLocal[correoRegistro] = nuevoUsuario;
    localStorage.setItem('usuarios_dental', JSON.stringify(dbLocal));

    document.getElementById("groupPassword").style.display = "none";
    document.getElementById("groupConfirm").style.display = "none";
    document.getElementById("btnFinalizar").style.display = "none";
    
    mensajeFinal.innerText="¡Usuario " + rolSeleccionado + " creado correctamente!";
    document.getElementById("btnIrAlLogin").style.display = "block";
}

function abrirLogin() {
    window.location.href = "login.html";
}

function togglePassword(id){
    const input=document.getElementById(id);
    input.type=input.type==="password"?"text":"password";
}