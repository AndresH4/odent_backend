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
# MOSTRAR ASEGURAMIENTOS
# READ
# =========================================

@app.route('/aseguramientos')
def aseguramientos():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM aseguramiento_datos')

    aseguramientos = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'aseguramientos.html',
        aseguramientos=aseguramientos
    )

# =========================================
# CREAR ASEGURAMIENTO
# CREATE
# =========================================

@app.route('/crear_aseguramiento', methods=['POST'])
def crear_aseguramiento():

    usuario_id = request.form['usuario_id']
    fecha = request.form['fecha']
    accion_id = request.form['accion_id']
    descripcion = request.form['descripcion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO aseguramiento_datos (

            Usuario_ID,
            Fecha,
            Accion_ID,
            Descripcion

        )

        VALUES (%s, %s, %s, %s)

    '''

    valores = (
        usuario_id,
        fecha,
        accion_id,
        descripcion
    )

    cur.execute(sql, valores)

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('aseguramientos'))

# =========================================
# ACTUALIZAR ASEGURAMIENTO
# UPDATE
# =========================================

@app.route('/actualizar_aseguramiento/<int:id>', methods=['POST'])
def actualizar_aseguramiento(id):

    usuario_id = request.form['usuario_id']
    fecha = request.form['fecha']
    accion_id = request.form['accion_id']
    descripcion = request.form['descripcion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE aseguramiento_datos

        SET

        Usuario_ID = %s,
        Fecha = %s,
        Accion_ID = %s,
        Descripcion = %s

        WHERE Aseguramiento_ID = %s

    '''

    valores = (
        usuario_id,
        fecha,
        accion_id,
        descripcion,
        id
    )

    cur.execute(sql, valores)

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('aseguramientos'))

# =========================================
# ELIMINAR ASEGURAMIENTO
# DELETE
# =========================================

@app.route('/eliminar_aseguramiento/<int:id>', methods=['POST'])
def eliminar_aseguramiento(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM aseguramiento_datos

        WHERE Aseguramiento_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('aseguramientos'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)
