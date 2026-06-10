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
        database='odent'
    )

# =========================================
# MOSTRAR ACCIONES
# READ
# =========================================

@app.route('/acciones_aseguramiento')
def acciones_aseguramiento():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM accion_aseguramiento')

    acciones = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'acciones_aseguramiento.html',
        acciones=acciones
    )

# =========================================
# CREAR ACCIÓN
# CREATE
# =========================================

@app.route('/crear_accion_aseguramiento', methods=['POST'])
def crear_accion_aseguramiento():

    nombre_accion = request.form['nombre_accion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO accion_aseguramiento
        (NombreAccion)

        VALUES (%s)

    '''

    cur.execute(sql, (nombre_accion,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('acciones_aseguramiento'))

# =========================================
# ACTUALIZAR ACCIÓN
# UPDATE
# =========================================

@app.route('/actualizar_accion_aseguramiento/<int:id>', methods=['POST'])
def actualizar_accion_aseguramiento(id):

    nombre_accion = request.form['nombre_accion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE accion_aseguramiento

        SET NombreAccion = %s

        WHERE Accion_ID = %s

    '''

    cur.execute(sql, (nombre_accion, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('acciones_aseguramiento'))

# =========================================
# ELIMINAR ACCIÓN
# DELETE
# =========================================

@app.route('/eliminar_accion_aseguramiento/<int:id>', methods=['POST'])
def eliminar_accion_aseguramiento(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM accion_aseguramiento

        WHERE Accion_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('acciones_aseguramiento'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)