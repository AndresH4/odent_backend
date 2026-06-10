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
# MOSTRAR ROLES
# READ
# =========================================

@app.route('/roles')
def roles():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM rol')

    roles = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'roles.html',
        roles=roles
    )

# =========================================
# CREAR ROL
# CREATE
# =========================================

@app.route('/crear_rol', methods=['POST'])
def crear_rol():

    descripcion = request.form['descripcion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO rol
        (Descripcion)

        VALUES (%s)

    '''

    cur.execute(sql, (descripcion,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('roles'))

# =========================================
# ACTUALIZAR ROL
# UPDATE
# =========================================

@app.route('/actualizar_rol/<int:id>', methods=['POST'])
def actualizar_rol(id):

    descripcion = request.form['descripcion']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE rol

        SET Descripcion = %s

        WHERE Rol_ID = %s

    '''

    cur.execute(sql, (descripcion, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('roles'))

# =========================================
# ELIMINAR ROL
# DELETE
# =========================================

@app.route('/eliminar_rol/<int:id>', methods=['POST'])
def eliminar_rol(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM rol

        WHERE Rol_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('roles'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)