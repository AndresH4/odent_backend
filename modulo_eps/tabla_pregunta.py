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
        database='odent'  # Tu base de datos de odontología
    )

# =========================================
# MOSTRAR PREGUNTAS (READ)
# =========================================
@app.route('/preguntas')
def preguntas():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Selecciona todas las preguntas registradas para la encuesta
    cur.execute('SELECT * FROM tabla_pregunta')
    lista_preguntas = cur.fetchall()
    
    cur.close()
    con.close()
    
    # Renderiza la plantilla enviando la lista de preguntas
    return render_template(
        'preguntas.html',
        lista_preguntas=lista_preguntas
    )

# =========================================
# CREAR PREGUNTA (CREATE)
# =========================================
@app.route('/crear_pregunta', methods=['POST'])
def crear_pregunta():
    # Captura el texto de la pregunta desde el formulario HTML
    texto = request.form['texto']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO tabla_pregunta (texto)
        VALUES (%s)
    '''
    
    cur.execute(sql, (texto,))
    con.commit()
    
    cur.close()
    con.close()
    
    # Redirige de vuelta al listado de preguntas
    return redirect(url_for('preguntas'))

# =========================================
# ACTUALIZAR PREGUNTA (UPDATE)
# =========================================
@app.route('/actualizar_pregunta/<int:id>', methods=['POST'])
def actualizar_pregunta(id):
    # Captura el nuevo texto para modificar la pregunta existente
    nuevo_texto = request.form['texto']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE tabla_pregunta
        SET texto = %s
        WHERE id = %s
    '''
    
    cur.execute(sql, (nuevo_texto, id))
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('preguntas'))

# =========================================
# ELIMINAR PREGUNTA (DELETE)
# =========================================
@app.route('/eliminar_pregunta/<int:id>', methods=['POST'])
def eliminar_pregunta(id):
    con = conectar()
    cur = con.cursor()

    # Elimina la pregunta seleccionada usando su ID
    cur.execute(
        'DELETE FROM tabla_pregunta WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('preguntas'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)