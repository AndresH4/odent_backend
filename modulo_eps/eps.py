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
        database='odent'  # Usando tu misma base de datos
    )

# =========================================
# MOSTRAR EPS (READ)
# =========================================
@app.route('/eps')
def eps():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Trae todas las EPS registradas
    cur.execute('SELECT * FROM eps')
    lista_eps = cur.fetchall()
    
    cur.close()
    con.close()
    
    return render_template(
        'eps.html',
        lista_eps=lista_eps
    )

# =========================================
# CREAR EPS (CREATE)
# =========================================
@app.route('/crear_eps', methods=['POST'])
def crear_eps():
    # Capturando los datos enviados desde los inputs del formulario
    nombre = request.form['nombre']
    tipoeps_id = request.form['tipoeps_id']
    regimen_eps_id = request.form['regimen_eps_id']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO eps (
            nombre,
            tipoeps_id,
            regimen_eps_id
        )
        VALUES (%s, %s, %s)
    '''
    
    valores = (nombre, tipoeps_id, regimen_eps_id)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('eps'))

# =========================================
# ACTUALIZAR EPS (UPDATE)
# =========================================
@app.route('/actualizar_eps/<int:id>', methods=['POST'])
def actualizar_eps(id):
    # Capturando los nuevos datos para modificar la EPS existente
    nombre = request.form['nombre']
    tipoeps_id = request.form['tipoeps_id']
    regimen_eps_id = request.form['regimen_eps_id']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE eps
        SET
            nombre = %s,
            tipoeps_id = %s,
            regimen_eps_id = %s
        WHERE id = %s
    '''
    
    valores = (nombre, tipoeps_id, regimen_eps_id, id)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('eps'))

# =========================================
# ELIMINAR EPS (DELETE)
# =========================================
@app.route('/eliminar_eps/<int:id>', methods=['POST'])
def eliminar_eps(id):
    con = conectar()
    cur = con.cursor()

    cur.execute(
        'DELETE FROM eps WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('eps'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)