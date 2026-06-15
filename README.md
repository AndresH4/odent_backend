# Stylo Dental — Instrucciones de integración

## Archivos entregados

```
odent_fix/
├── app.py                        ← reemplaza tu app.py actual
├── modulo_citas/
│   └── routes.py                 ← reemplaza modulo_citas/routes.py (estaba vacío)
└── static/js/
    ├── login.js                  ← NUEVO (no existía)
    ├── session.js                ← NUEVO (utilidad compartida)
    ├── seguridad.js              ← reemplaza el actual (simplificado)
    ├── administrador.js          ← reemplaza el actual
    ├── paciente.js               ← reemplaza el actual
    └── agendar.js                ← reemplaza el actual
```

## Pasos de integración

### 1 — Copiar los archivos
Copia cada archivo de `odent_fix/` a la carpeta correspondiente de tu proyecto.
Los nombres son idénticos, simplemente sobreescríbelos.

### 2 — Agregar session.js a los templates HTML
En `administrador.html`, `paciente.html` y `especialista.html` agrega **antes**
del script principal:

```html
<script src="{{ url_for('static', filename='js/session.js') }}"></script>
```

### 3 — Agregar login.js al template de login
En `templates/login.html` ya está el `<script>` apuntando a `login.js`.
Solo verifica que diga:
```html
<script src="{{ url_for('static', filename='js/login.js') }}"></script>
```

### 4 — Registrar citas_bp en app.py (ya incluido)
El `app.py` entregado ya importa y registra `citas_bp`. Si usas tu propio
`app.py`, agrega esto:

```python
from modulo_citas.routes import citas_bp
app.register_blueprint(citas_bp, url_prefix='/api')
```

Y el endpoint auxiliar para obtener `Paciente_ID` por `Usuario_ID`:

```python
@app.route('/api/paciente/por-usuario/<int:usuario_id>', methods=['GET'])
def paciente_por_usuario(usuario_id):
    con = get_db_connection()
    cur = con.cursor()
    cur.execute("SELECT Paciente_ID FROM paciente WHERE Usuario_ID = ?", (usuario_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify({"Paciente_ID": row["Paciente_ID"]}), 200
```

### 5 — Verificar que `modulo_citas/__init__.py` exista
Si no existe, crea un archivo vacío:
```
modulo_citas/__init__.py   (vacío)
```

---

## Qué se corrigió / implementó

| Problema | Solución |
|---|---|
| `login.js` no existía | Creado: autentica contra `/api/auth/login`, guarda en `sessionStorage` |
| Todos los paneles usaban `localStorage` | Migrados a `sessionStorage` + API Flask |
| Saludo "Admin Root" / "Paciente" hardcodeados | Ahora muestra el nombre real del usuario logueado |
| `modulo_citas/routes.py` vacío | CRUD completo: citas, agenda, especialistas, multas |
| `agendar.js` no tocaba la DB | Ahora carga agenda real y guarda en SQLite vía `/api/citas` |
| `administrador.js` leía `localStorage` | Lee usuarios y citas desde la API |
| `paciente.js` leía `localStorage` | Lee citas reales del paciente y cancela vía API |
| `seguridad.js` tenía lógica de admin | Simplificado: solo protege rutas |
| Sin validación de rol al entrar a panel | Cada panel verifica `Rol_ID` de la sesión y redirige si no corresponde |

## Flujo completo después del fix

```
login.html  →  /api/auth/login  →  sessionStorage.odent_usuario
                                         ↓
                              Rol_ID = 1 → administrador.html
                              Rol_ID = 2 → especialista.html  
                              Rol_ID = 3 → paciente.html
                                         ↓
                    Cada panel carga su datos desde la API Flask
                    que lee/escribe en odent.db (SQLite)
```