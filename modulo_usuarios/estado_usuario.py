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
# MOSTRAR ESTADOS DE USUARIO
# READ
# =========================================

@app.route('/estados_usuario')
def estados_usuario():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM estado_usuario')

    estados = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'estados_usuario.html',
        estados=estados
    )

# =========================================
# CREAR ESTADO
# CREATE
# =========================================

@app.route('/crear_estado_usuario', methods=['POST'])
def crear_estado_usuario():

    nombre_estado = request.form['nombre_estado']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO estado_usuario
        (NombreEstado)

        VALUES (%s)

    '''

    cur.execute(sql, (nombre_estado,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('estados_usuario'))

# =========================================
# ACTUALIZAR ESTADO
# UPDATE
# =========================================

@app.route('/actualizar_estado_usuario/<int:id>', methods=['POST'])
def actualizar_estado_usuario(id):

    nombre_estado = request.form['nombre_estado']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE estado_usuario

        SET NombreEstado = %s

        WHERE Estado_ID = %s

    '''

    cur.execute(sql, (nombre_estado, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('estados_usuario'))

# =========================================
# ELIMINAR ESTADO
# DELETE
# =========================================

@app.route('/eliminar_estado_usuario/<int:id>', methods=['POST'])
def eliminar_estado_usuario(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM estado_usuario

        WHERE Estado_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('estados_usuario'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)