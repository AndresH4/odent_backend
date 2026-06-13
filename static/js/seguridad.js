document.addEventListener('DOMContentLoaded', () => {
    const usuarioGuardado = sessionStorage.getItem('odent_usuario');
    
    if (!usuarioGuardado) {
        window.location.replace('/login.html');
    }
});

function cerrarSesion() {
    sessionStorage.removeItem('odent_usuario');
    window.location.replace('/login.html');
}