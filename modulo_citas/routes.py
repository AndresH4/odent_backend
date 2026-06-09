from flask import Blueprint

citas_bp = Blueprint("citas", __name__)

@citas_bp.route("/citas")
def citas():
    return {"mensaje": "citas"}