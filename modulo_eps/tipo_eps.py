from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# =========================================
# CONEXIÓN MYSQL
# =========================================
def conectar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='odent'  # Tu base de datos
    )

# =========================================
# MOSTRAR TIPOS DE EPS (READ)
# =========================================
@app.route('/tipoeps')
def tipoeps():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Selecciona todos los tipos de EPS registrados
    cur.execute('SELECT * FROM tipoeps')
    lista_tipoeps = cur.fetchall()
    
    cur.close()
    con.close()
    
    # Renderiza la plantilla enviando la lista de datos
    return render_template(
        'tipoeps.html',
        lista_tipoeps=lista_tipoeps
    )

# =========================================
# CREAR TIPO DE EPS (CREATE)
# =========================================
@app.route('/crear_tipoeps', methods=['POST'])
def crear_tipoeps():
    # Captura el nombre del tipo de EPS desde el formulario HTML
    nombre = request.form['nombre']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO tipoeps (nombre)
        VALUES (%s)
    '''
    
    cur.execute(sql, (nombre,))
    con.commit()
    
    cur.close()
    con.close()
    
    # Redirige de vuelta a la lista de tipos de EPS
    return redirect(url_for('tipoeps'))

# =========================================
# ACTUALIZAR TIPO DE EPS (UPDATE)
# =========================================
@app.route('/actualizar_tipoeps/<int:id>', methods=['POST'])
def actualizar_tipoeps(id):
    # Captura el nuevo nombre para modificar el registro existente
    nuevo_nombre = request.form['nombre']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE tipoeps
        SET nombre = %s
        WHERE id = %s
    '''
    
    cur.execute(sql, (nuevo_nombre, id))
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('tipoeps'))

# =========================================
# ELIMINAR TIPO DE EPS (DELETE)
# =========================================
@app.route('/eliminar_tipoeps/<int:id>', methods=['POST'])
def eliminar_tipoeps(id):
    con = conectar()
    cur = con.cursor()

    # Elimina el tipo de EPS usando su ID
    cur.execute(
        'DELETE FROM tipoeps WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('tipoeps'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)