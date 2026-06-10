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
# MOSTRAR USUARIOS
# READ
# =========================================

@app.route('/usuarios')
def usuarios():

    con = conectar()

    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM usuarios')

    usuarios = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'usuarios.html',
        usuarios=usuarios
    )

# =========================================
# CREAR USUARIO
# CREATE
# =========================================

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():

    nombres = request.form['nombres']
    apellidos = request.form['apellidos']
    tipo_doc = request.form['tipo_doc']
    numero_documento = request.form['numero_documento']
    password = request.form['password']
    fecha_nacimiento = request.form['fecha_nacimiento']
    genero = request.form['genero']
    correo = request.form['correo']
    telefono = request.form['telefono']
    estado = request.form['estado']
    rol = request.form['rol']

    con = conectar()

    cur = con.cursor()

    sql = '''
        INSERT INTO usuarios (

            Nombres,
            Apellidos,
            TipoDoc_ID,
            NumeroDocumento,
            Contraseña,
            FechaNacimiento,
            Genero_ID,
            Correo,
            Telefono,
            Estado_ID,
            Rol_ID

        )

        VALUES (%s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s)
    '''

    valores = (

        nombres,
        apellidos,
        tipo_doc,
        numero_documento,
        password,
        fecha_nacimiento,
        genero,
        correo,
        telefono,
        estado,
        rol

    )

    cur.execute(sql, valores)

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('usuarios'))

# =========================================
# ACTUALIZAR USUARIO
# UPDATE
# =========================================

@app.route('/actualizar_usuario/<int:id>', methods=['POST'])
def actualizar_usuario(id):

    nombres = request.form['nombres']
    apellidos = request.form['apellidos']
    tipo_doc = request.form['tipo_doc']
    numero_documento = request.form['numero_documento']
    password = request.form['password']
    fecha_nacimiento = request.form['fecha_nacimiento']
    genero = request.form['genero']
    correo = request.form['correo']
    telefono = request.form['telefono']
    estado = request.form['estado']
    rol = request.form['rol']

    con = conectar()

    cur = con.cursor()

    sql = '''
        UPDATE usuarios

        SET

        Nombres = %s,
        Apellidos = %s,
        TipoDoc_ID = %s,
        NumeroDocumento = %s,
        Contraseña = %s,
        FechaNacimiento = %s,
        Genero_ID = %s,
        Correo = %s,
        Telefono = %s,
        Estado_ID = %s,
        Rol_ID = %s

        WHERE Usuario_ID = %s
    '''

    valores = (

        nombres,
        apellidos,
        tipo_doc,
        numero_documento,
        password,
        fecha_nacimiento,
        genero,
        correo,
        telefono,
        estado,
        rol,
        id

    )

    cur.execute(sql, valores)

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('usuarios'))

# =========================================
# ELIMINAR USUARIO
# DELETE
# =========================================

@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
def eliminar_usuario(id):

    con = conectar()

    cur = con.cursor()

    cur.execute(
        'DELETE FROM usuarios WHERE Usuario_ID = %s',
        (id,)
    )

    con.commit()

    cur.close()
    con.close()

    return redirect(url_for('usuarios'))

# =========================================
# EJECUTAR APP
# =========================================

if __name__ == '__main__':
    app.run(debug=True)
