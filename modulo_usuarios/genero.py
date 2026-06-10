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
# MOSTRAR GÉNEROS
# READ
# =========================================

@app.route('/generos')
def generos():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM genero')

    generos = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'generos.html',
        generos=generos
    )

# =========================================
# CREAR GÉNERO
# CREATE
# =========================================

@app.route('/crear_genero', methods=['POST'])
def crear_genero():

    nombre_genero = request.form['nombre_genero']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO genero
        (NombreGenero)

        VALUES (%s)

    '''

    cur.execute(sql, (nombre_genero,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('generos'))

# =========================================
# ACTUALIZAR GÉNERO
# UPDATE
# =========================================

@app.route('/actualizar_genero/<int:id>', methods=['POST'])
def actualizar_genero(id):

    nombre_genero = request.form['nombre_genero']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE genero

        SET NombreGenero = %s

        WHERE Genero_ID = %s

    '''

    cur.execute(sql, (nombre_genero, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('generos'))

# =========================================
# ELIMINAR GÉNERO
# DELETE
# =========================================

@app.route('/eliminar_genero/<int:id>', methods=['POST'])
def eliminar_genero(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM genero

        WHERE Genero_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('generos'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)