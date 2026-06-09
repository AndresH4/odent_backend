from flask import Flask

from modulo_usuarios.routes import usuarios_bp
from modulo_eps.routes import eps_bp
from modulo_citas.routes import citas_bp
from modulo_historial.routes import historial_bp

app = Flask(__name__)

app.register_blueprint(usuarios_bp)
app.register_blueprint(eps_bp)
app.register_blueprint(citas_bp)
app.register_blueprint(historial_bp)

@app.route("/")
def home():
    return {"mensaje": "API ODENT funcionando"}

if __name__ == "__main__":
    app.run(debug=True)