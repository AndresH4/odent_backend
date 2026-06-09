from flask import Blueprint

historial_bp = Blueprint("historial", __name__)

@historial_bp.route("/historial")
def historial():
    return {"mensaje": "historial"}