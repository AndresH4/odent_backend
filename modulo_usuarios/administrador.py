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
# MOSTRAR ADMINISTRADORES
# READ
# =========================================

@app.route('/administradores')
def administradores():

    con = conectar()

    cur = con.cursor(dictionary=True)

    sql = '''

        SELECT

            administrador.Administrador_ID,
            usuarios.Nombres,
            usuarios.Apellidos,
            usuarios.Correo

        FROM administrador

        INNER JOIN usuarios
        ON administrador.Usuario_ID = usuarios.Usuario_ID

    '''

    cur.execute(sql)

    administradores = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'administradores.html',
        administradores=administradores
    )

# =========================================
# CREAR ADMINISTRADOR
# CREATE
# =========================================

@app.route('/crear_administrador', methods=['POST'])
def crear_administrador():

    usuario_id = request.form['usuario_id']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO administrador
        (Usuario_ID)

        VALUES (%s)

    '''

    cur.execute(sql, (usuario_id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('administradores'))

# =========================================
# ACTUALIZAR ADMINISTRADOR
# UPDATE
# =========================================

@app.route('/actualizar_administrador/<int:id>', methods=['POST'])
def actualizar_administrador(id):

    usuario_id = request.form['usuario_id']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE administrador

        SET Usuario_ID = %s

        WHERE Administrador_ID = %s

    '''

    cur.execute(sql, (usuario_id, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('administradores'))

# =========================================
# ELIMINAR ADMINISTRADOR
# DELETE
# =========================================

@app.route('/eliminar_administrador/<int:id>', methods=['POST'])
def eliminar_administrador(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM administrador

        WHERE Administrador_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('administradores'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)