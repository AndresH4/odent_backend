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
# MOSTRAR AFILIACIONES (READ)
# =========================================
@app.route('/afiliacion')
def afiliacion():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Traemos los datos cruzados con las tablas de usuarios y eps
    # Nota: Ajusté 'Usuario_ID' y 'Nombres'/'Apellidos' basándome en tu primer código de usuarios
    sql = '''
        SELECT 
            afiliacion.id,
            afiliacion.fecha,
            CONCAT(usuarios.Nombres, ' ', usuarios.Apellidos) AS nombre_usuario,
            eps.nombre AS nombre_eps
        FROM afiliacion
        INNER JOIN usuarios ON afiliacion.usuario_id = usuarios.Usuario_ID
        INNER JOIN eps ON afiliacion.eps_id = eps.id
    '''
    
    cur.execute(sql)
    lista_afiliaciones = cur.fetchall()
    
    cur.close()
    con.close()
    
    return render_template(
        'afiliacion.html',
        lista_afiliaciones=lista_afiliaciones
    )

# =========================================
# CREAR AFILIACIÓN (CREATE)
# =========================================
@app.route('/crear_afiliacion', methods=['POST'])
def crear_afiliacion():
    # Capturando los IDs y la fecha desde el formulario HTML
    usuario_id = request.form['usuario_id']
    eps_id = request.form['eps_id']
    fecha = request.form['fecha']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO afiliacion (usuario_id, eps_id, fecha)
        VALUES (%s, %s, %s)
    '''
    
    valores = (usuario_id, eps_id, fecha)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('afiliacion'))

# =========================================
# ACTUALIZAR AFILIACIÓN (UPDATE)
# =========================================
@app.route('/actualizar_afiliacion/<int:id>', methods=['POST'])
def actualizar_afiliacion(id):
    # Capturando los nuevos datos para modificar la afiliación existente
    usuario_id = request.form['usuario_id']
    eps_id = request.form['eps_id']
    fecha = request.form['fecha']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE afiliacion
        SET
            usuario_id = %s,
            eps_id = %s,
            fecha = %s
        WHERE id = %s
    '''
    
    valores = (usuario_id, eps_id, fecha, id)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('afiliacion'))

# =========================================
# ELIMINAR AFILIACIÓN (DELETE)
# =========================================
@app.route('/eliminar_afiliacion/<int:id>', methods=['POST'])
def eliminar_afiliacion(id):
    con = conectar()
    cur = con.cursor()

    cur.execute(
        'DELETE FROM afiliacion WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('afiliacion'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)