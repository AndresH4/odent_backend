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
# MOSTRAR PACIENTES (READ)
# =========================================
@app.route('/pacientes')
def pacientes():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Cruzamos con la tabla usuarios para obtener los datos personales del paciente
    sql = '''
        SELECT 
            paciente.id AS paciente_id,
            usuarios.Usuario_ID,
            usuarios.NumeroDocumento,
            CONCAT(usuarios.Nombres, ' ', usuarios.Apellidos) AS nombre_completo,
            usuarios.Correo,
            usuarios.Telefono
        FROM paciente
        INNER JOIN usuarios ON paciente.usuario_id = usuarios.Usuario_ID
    '''
    
    cur.execute(sql)
    lista_pacientes = cur.fetchall()
    
    cur.close()
    con.close()
    
    return render_template(
        'pacientes.html',
        lista_pacientes=lista_pacientes
    )

# =========================================
# CREAR PACIENTE (CREATE)
# =========================================
@app.route('/crear_paciente', methods=['POST'])
def crear_paciente():
    # Se captura el ID del usuario que pasará a ser asignado como paciente
    usuario_id = request.form['usuario_id']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO paciente (usuario_id)
        VALUES (%s)
    '''
    
    cur.execute(sql, (usuario_id,))
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('pacientes'))

# =========================================
# ACTUALIZAR PACIENTE (UPDATE)
# =========================================
@app.route('/actualizar_paciente/<int:id>', methods=['POST'])
def actualizar_paciente(id):
    # Permite reasignar el registro de paciente a otro usuario_id si es necesario
    nuevo_usuario_id = request.form['usuario_id']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE paciente
        SET usuario_id = %s
        WHERE id = %s
    '''
    
    cur.execute(sql, (nuevo_usuario_id, id))
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('pacientes'))

# =========================================
# ELIMINAR PACIENTE (DELETE)
# =========================================
@app.route('/eliminar_paciente/<int:id>', methods=['POST'])
def eliminar_paciente(id):
    con = conectar()
    cur = con.cursor()

    # Remueve la condición de paciente, pero el usuario original sigue existiendo en su tabla
    cur.execute(
        'DELETE FROM paciente WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('pacientes'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)