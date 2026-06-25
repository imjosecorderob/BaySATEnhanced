function confirmarEliminacion() {
    return confirm('¿Estás seguro de que deseas eliminar este proyecto? Esta acción no se puede deshacer.');
}
function mostrarFormulario() {
    let formulario = document.getElementById('formularioProyecto');
    formulario.style.display = 'block';
    setTimeout(function() {
        formulario.classList.add('mostrar');
    }, 10);
}

function cerrarFormulario() {
    let formulario = document.getElementById('formularioProyecto');
    formulario.classList.remove('mostrar');
    setTimeout(function() {
        formulario.style.display = 'none';
    }, 500);
}

function nuevoProyecto() {
    mostrarFormulario();
    // Limpiar los campos
    document.getElementById('txtCodigo').value = '';
    document.getElementById('txtProyecto').value = '';
    document.getElementById('txtIntegrantes').value = '';
    // Habilitar el campo código
    document.getElementById('txtCodigo').disabled = false;
}

function editarProyecto(codigo, proyecto, integrantes) {
    mostrarFormulario();
    // Llenar los campos
    document.getElementById('txtCodigo').value = codigo;
    document.getElementById('txtProyecto').value = proyecto;
    document.getElementById('txtIntegrantes').value = integrantes;
    // Deshabilitar el campo código
    document.getElementById('txtCodigo').disabled = true;
}
