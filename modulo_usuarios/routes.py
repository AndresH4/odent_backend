from flask import Blueprint

usuarios_bp = Blueprint("usuarios", __name__)

@usuarios_bp.route("/usuarios")
def usuarios():
    return {"mensaje": "usuarios"}