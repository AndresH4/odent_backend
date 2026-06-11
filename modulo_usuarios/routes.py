from flask import Flask, request, jsonify
# Importación de todos tus módulos
import usuario, rol, genero, tipo_documento, estado_usuario, \
       administrador, aseguramiento_datos, accion_aseguramiento

app = Flask(__name__)

# =============================================================================
# 1. MÓDULO USUARIOS
# =============================================================================

@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    return jsonify(usuario.read_all_usuarios())

@app.route('/usuarios', methods=['POST'])
def add_usuario():
    data = request.json
    res = usuario.create_usuario(**data)
    return jsonify(res), (201 if res.get('ok') else 400)

@app.route('/usuarios/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def crud_usuario(id):
    if request.method == 'GET':
        data = usuario.read_usuario_by_id(id)
        return jsonify(data) if data else (jsonify({"error": "No encontrado"}), 404)
    if request.method == 'PUT':
        data = request.json
        res = usuario.update_usuario(id, **data)
        return jsonify(res), (200 if res.get('ok') else 400)
    if request.method == 'DELETE':
        res = usuario.delete_usuario(id)
        return jsonify(res), (200 if res.get('ok') else 400)

# =============================================================================
# 2. CATÁLOGOS (Roles, Géneros, Tipos Doc, Estados, Acciones)
# =============================================================================

def handle_catalog(module, id=None):
    """Helper para simplificar las rutas de los catálogos CRUD"""
    if request.method == 'GET':
        return jsonify(module.read_all()) if not id else jsonify(module.read_by_id(id))
    # Aquí podrías extender para POST/PUT/DELETE si lo requieres en todos
    return jsonify({"error": "Método no implementado"}), 405

@app.route('/roles', methods=['GET'])
def get_roles(): return jsonify(rol.read_all_roles())

@app.route('/roles/reporte', methods=['GET'])
def get_reporte_roles(): return jsonify(rol.reporte_usuarios_por_rol())

@app.route('/generos', methods=['GET'])
def get_generos(): return jsonify(genero.read_all_generos())

@app.route('/generos/reporte', methods=['GET'])
def get_reporte_generos(): return jsonify(genero.reporte_usuarios_por_genero())

@app.route('/tipos_documento', methods=['GET'])
def get_tipos_doc(): return jsonify(tipo_documento.read_all_tipos_documento())

@app.route('/estados_usuario', methods=['GET'])
def get_estados(): return jsonify(estado_usuario.read_all_estados())

@app.route('/acciones_aseguramiento', methods=['GET'])
def get_acciones(): return jsonify(accion_aseguramiento.read_all_acciones())

# =============================================================================
# 3. MÓDULO ADMINISTRADORES
# =============================================================================

@app.route('/administradores', methods=['GET', 'POST'])
def crud_administradores():
    if request.method == 'GET':
        return jsonify(administrador.read_all_administradores())
    data = request.json
    res = administrador.create_administrador(data['usuario_id'])
    return jsonify(res), (201 if res.get('ok') else 400)

@app.route('/administradores/activos', methods=['GET'])
def get_admins_activos():
    return jsonify(administrador.reporte_administradores_activos())

# =============================================================================
# 4. MÓDULO ASEGURAMIENTO (Auditoría)
# =============================================================================

@app.route('/auditoria', methods=['GET', 'POST'])
def crud_auditoria():
    if request.method == 'GET':
        return jsonify(aseguramiento_datos.read_all_aseguramientos())
    data = request.json
    res = aseguramiento_datos.create_aseguramiento(
        data['usuario_id'], data['accion_id'], data['descripcion']
    )
    return jsonify(res), (201 if res.get('ok') else 400)

@app.route('/auditoria/usuario/<int:usuario_id>', methods=['GET'])
def get_auditoria_usuario(usuario_id):
    return jsonify(aseguramiento_datos.read_aseguramiento_by_usuario(usuario_id))

@app.route('/auditoria/reporte/acciones', methods=['GET'])
def get_reporte_acciones():
    return jsonify(aseguramiento_datos.reporte_acciones_por_tipo())

@app.route('/auditoria/reporte/fecha', methods=['GET'])
def get_reporte_fecha():
    inicio = request.args.get('desde')
    fin = request.args.get('hasta')
    return jsonify(aseguramiento_datos.reporte_auditoria_por_fecha(inicio, fin))

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    # Ejecutar en puerto 5000
    app.run(debug=True, port=5000)