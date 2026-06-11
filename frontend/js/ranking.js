  const rankingView = document.getElementById("rankingView");
  const configView = document.getElementById("configView");
  const toast = document.getElementById("toast");
  const profileImage = document.getElementById("profileImage");
  const uploadImage = document.getElementById("uploadImage");

  // --- LÓGICA DE LA FOTO DE PERFIL (Mantenemos la que arreglamos antes) ---
  
  // 1. Cargar la imagen guardada al abrir la página
  window.addEventListener("DOMContentLoaded", () => {
    const savedImage = localStorage.getItem("profilePic");
    if (savedImage) {
      profileImage.src = savedImage;
    }
  });

  // 2. Cambiar la imagen y guardarla cuando el usuario sube un archivo
  uploadImage.addEventListener("change", function(event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function(e) {
        const imageResult = e.target.result;
        profileImage.src = imageResult;
        localStorage.setItem("profilePic", imageResult); // Guardar en el navegador
        lanzarToast("Foto de perfil actualizada");
      };
      reader.readAsDataURL(file);
    }
  });

  // --- LÓGICA DE LAS VISTAS ---

  function mostrarConfig(){
    rankingView.style.display = "none";
    configView.style.display = "block";
  }

  function volverRanking(){
    configView.style.display = "none";
    rankingView.style.display = "block";
  }

  function lanzarToast(msj){
    toast.innerHTML = `<i class="fas fa-check-circle"></i> ${msj}`;
    toast.className = "show";
    setTimeout(() => toast.className = "", 2500);
  }

  function guardarCambios(){
    lanzarToast("¡Cambios guardados con éxito!");
    setTimeout(volverRanking, 2000);
  }

  function toggleEstado(){
    const btn = document.getElementById("estadoBtn");
    btn.classList.toggle("off");
    btn.innerText = btn.classList.contains("off") ? "OFF" : "ON";
  }

  function agregarPregunta(){
    const texto = prompt("Nueva pregunta:");
    if(texto){
      const div = document.createElement("div");
      div.className = "pregunta-item";
      div.innerHTML = `<span class="pregunta-texto">"${texto}"</span>
      <div class="pregunta-acciones">
      <i class="fa-solid fa-pencil" onclick="editarPregunta(this)"></i>
      <i class="fa-solid fa-xmark" onclick="this.parentElement.parentElement.remove()"></i>
      </div>`;
      document.getElementById("listaPreguntas").appendChild(div);
    }
  }

  function editarPregunta(el){
    const span = el.parentElement.parentElement.querySelector('.pregunta-texto');
    const nuevo = prompt("Editar pregunta:", span.innerText);
    if(nuevo) span.innerText = nuevo; 
  }