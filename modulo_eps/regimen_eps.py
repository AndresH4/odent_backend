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
# MOSTRAR REGÍMENES (READ)
# =========================================
@app.route('/regimen_eps')
def regimen_eps():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Selecciona todos los regímenes existentes
    cur.execute('SELECT * FROM regimen_eps')
    lista_regimen = cur.fetchall()
    
    cur.close()
    con.close()
    
    # Renderiza la plantilla enviando la lista de datos
    return render_template(
        'regimen_eps.html',
        lista_regimen=lista_regimen
    )

# =========================================
# CREAR RÉGIMEN (CREATE)
# =========================================
@app.route('/crear_regimen', methods=['POST'])
def crear_regimen():
    # Captura el nombre del régimen desde el formulario HTML
    nombre = request.form['nombre']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO regimen_eps (nombre)
        VALUES (%s)
    '''
    
    cur.execute(sql, (nombre,))
    con.commit()
    
    cur.close()
    con.close()
    
    # Redirige de vuelta a la lista de regímenes
    return redirect(url_for('regimen_eps'))

# =========================================
# ACTUALIZAR RÉGIMEN (UPDATE)
# =========================================
@app.route('/actualizar_regimen/<int:id>', methods=['POST'])
def actualizar_regimen(id):
    # Captura el nuevo nombre para modificar el registro existente
    nuevo_nombre = request.form['nombre']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE regimen_eps
        SET nombre = %s
        WHERE id = %s
    '''
    
    cur.execute(sql, (nuevo_nombre, id))
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('regimen_eps'))

# =========================================
# ELIMINAR RÉGIMEN (DELETE)
# =========================================
@app.route('/eliminar_regimen/<int:id>', methods=['POST'])
def eliminar_regimen(id):
    con = conectar()
    cur = con.cursor()

    # Elimina el régimen usando su ID
    cur.execute(
        'DELETE FROM regimen_eps WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('regimen_eps'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)