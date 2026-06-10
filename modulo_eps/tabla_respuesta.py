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
# MOSTRAR RESPUESTAS (READ)
# =========================================
@app.route('/respuestas')
def respuestas():
    con = conectar()
    cur = con.cursor(dictionary=True)
    
    # Cruzamos con 'tabla_pregunta' para saber a qué pregunta pertenece cada respuesta
    sql = '''
        SELECT 
            tabla_respuesta.id AS respuesta_id,
            tabla_respuesta.texto AS respuesta_texto,
            tabla_pregunta.texto AS pregunta_texto
        FROM tabla_respuesta
        INNER JOIN tabla_pregunta ON tabla_respuesta.pregunta_id = tabla_pregunta.id
    '''
    
    cur.execute(sql)
    lista_respuestas = cur.fetchall()
    
    cur.close()
    con.close()
    
    return render_template(
        'respuestas.html',
        lista_respuestas=lista_respuestas
    )

# =========================================
# CREAR RESPUESTA (CREATE)
# =========================================
@app.route('/crear_respuesta', methods=['POST'])
def crear_respuesta():
    # Captura el ID de la pregunta y el texto de la opción de respuesta
    pregunta_id = request.form['pregunta_id']
    texto = request.form['texto']

    con = conectar()
    cur = con.cursor()

    sql = '''
        INSERT INTO tabla_respuesta (pregunta_id, texto)
        VALUES (%s, %s)
    '''
    
    valores = (pregunta_id, texto)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('respuestas'))

# =========================================
# ACTUALIZAR RESPUESTA (UPDATE)
# =========================================
@app.route('/actualizar_respuesta/<int:id>', methods=['POST'])
def actualizar_respuesta(id):
    # Captura los nuevos datos para modificar la respuesta existente
    pregunta_id = request.form['pregunta_id']
    nuevo_texto = request.form['texto']

    con = conectar()
    cur = con.cursor()

    sql = '''
        UPDATE tabla_respuesta
        SET 
            pregunta_id = %s,
            texto = %s
        WHERE id = %s
    '''
    
    valores = (pregunta_id, nuevo_texto, id)
    
    cur.execute(sql, valores)
    con.commit()
    
    cur.close()
    con.close()
    
    return redirect(url_for('respuestas'))

# =========================================
# ELIMINAR RESPUESTA (DELETE)
# =========================================
@app.route('/eliminar_respuesta/<int:id>', methods=['POST'])
def eliminar_respuesta(id):
    con = conectar()
    cur = con.cursor()

    # Elimina la opción de respuesta seleccionada usando su ID
    cur.execute(
        'DELETE FROM tabla_respuesta WHERE id = %s',
        (id,)
    )

    con.commit()
    cur.close()
    con.close()

    return redirect(url_for('respuestas'))

# =========================================
# EJECUTAR APP
# =========================================
if __name__ == '__main__':
    app.run(debug=True)