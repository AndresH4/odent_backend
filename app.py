from flask import Flask
from db import get_db_connection

# ─── Importar blueprints de cada módulo ───────────────────────────────────────
from modulo_usuario.routes import usuario_bp
from modulo_eps.routes     import eps_bp
from modulo_citas.routes   import citas_bp
from modulo_historial.routes import historial_bp

app = Flask(__name__)

# ─── Registrar blueprints con prefijo de URL ──────────────────────────────────
app.register_blueprint(usuario_bp,  url_prefix='/api')
app.register_blueprint(eps_bp,      url_prefix='/api')
app.register_blueprint(citas_bp,    url_prefix='/api')
app.register_blueprint(historial_bp, url_prefix='/api')

# ─── Ruta de prueba ───────────────────────────────────────────────────────────
@app.route('/')
def index():
    return {'mensaje': 'Odent API corriendo correctamente'}

if __name__ == '__main__':
    app.run(debug=True)