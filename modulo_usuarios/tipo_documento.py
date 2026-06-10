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
# MOSTRAR TIPOS DE DOCUMENTO
# READ
# =========================================

@app.route('/tipos_documento')
def tipos_documento():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM tipo_documento')

    tipos_documento = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'tipos_documento.html',
        tipos_documento=tipos_documento
    )

# =========================================
# CREAR TIPO DE DOCUMENTO
# CREATE
# =========================================

@app.route('/crear_tipo_documento', methods=['POST'])
def crear_tipo_documento():

    nombre_tipo_documento = request.form['nombre_tipo_documento']

    con = conectar()

    cur = con.cursor()

    sql = '''

        INSERT INTO tipo_documento
        (NombreTipoDeDocumento)

        VALUES (%s)

    '''

    cur.execute(sql, (nombre_tipo_documento,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('tipos_documento'))

# =========================================
# ACTUALIZAR TIPO DE DOCUMENTO
# UPDATE
# =========================================

@app.route('/actualizar_tipo_documento/<int:id>', methods=['POST'])
def actualizar_tipo_documento(id):

    nombre_tipo_documento = request.form['nombre_tipo_documento']

    con = conectar()

    cur = con.cursor()

    sql = '''

        UPDATE tipo_documento

        SET NombreTipoDeDocumento = %s

        WHERE TipoDoc_ID = %s

    '''

    cur.execute(sql, (nombre_tipo_documento, id))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('tipos_documento'))

# =========================================
# ELIMINAR TIPO DE DOCUMENTO
# DELETE
# =========================================

@app.route('/eliminar_tipo_documento/<int:id>', methods=['POST'])
def eliminar_tipo_documento(id):

    con = conectar()

    cur = con.cursor()

    sql = '''

        DELETE FROM tipo_documento

        WHERE TipoDoc_ID = %s

    '''

    cur.execute(sql, (id,))

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('tipos_documento'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)