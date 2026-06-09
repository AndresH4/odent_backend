from flask import Blueprint

eps_bp = Blueprint("eps", __name__)

@eps_bp.route("/eps")
def eps():
    return {"mensaje": "eps"}