from flask import Flask, render_template, request, redirect, session
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)
app.secret_key = 'zona-desempleada-clave'
app.config['GMAIL_APP_PASSWORD'] = os.environ.get('GMAIL_APP_PASSWORD')


def conectar_bd():
    return psycopg.connect(
        host='postgres',
        dbname='mi_base_datos',
        user='admin',
        password='admin123'
    )


def enviar_correo(destinatario, nombre_canal):
    mensaje = EmailMessage()
    mensaje['Subject'] = f'Te has suscrito al canal {nombre_canal}'
    mensaje['From'] = 'jugadordefortnite41@gmail.com'
    mensaje['To'] = destinatario

    mensaje.set_content(
        f'Te has suscrito correctamente al canal {nombre_canal}. '
        '¡Gracias por formar parte de Zona Desempleada!'
    )

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as servidor:
        servidor.login(
            'jugadordefortnite41@gmail.com',
            app.config['GMAIL_APP_PASSWORD']
        )
        servidor.send_message(mensaje)


@app.route('/probar-bd/')
def probar_bd():
    with conectar_bd() as conn:
        resultado = conn.execute('SELECT 1').fetchone()

    return f'Conexión correcta con PostgreSQL: {resultado[0]}'


canales = [
    {
        'id': 1,
        'nombre': 'Videojuegos',
        'descripcion': 'Noticias, análisis y actualidad del mundo de los videojuegos.'
    },
    {
        'id': 2,
        'nombre': 'Cine',
        'descripcion': 'Películas, estrenos, críticas y recomendaciones.'
    },
    {
        'id': 3,
        'nombre': 'IT',
        'descripcion': 'Programación, sistemas, redes, Linux, Docker y tecnología.'
    },
    {
        'id': 4,
        'nombre': 'Deportes',
        'descripcion': 'Noticias y actualidad del mundo del deporte.'
    }
]


@app.route('/')
def index():
    return render_template('index.html', canales=canales)


@app.route('/registro/', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html')

    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password = request.form.get('password')

    password_hash = generate_password_hash(password)

    try:
        with conectar_bd() as conn:
            conn.execute(
                '''
                INSERT INTO usuarios (nombre, email, password_hash)
                VALUES (%s, %s, %s)
                ''',
                (nombre, email, password_hash)
            )
    except psycopg.errors.UniqueViolation:
        return 'Este email ya está registrado', 409

    session['usuario'] = email
    return redirect('/')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    with conectar_bd() as conn:
        usuario = conn.execute(
            '''
            SELECT nombre, email, password_hash
            FROM usuarios
            WHERE email = %s
            ''',
            (email,)
        ).fetchone()

    if usuario and check_password_hash(usuario[2], password):
        session['usuario'] = usuario[1]
        return redirect('/')

    return 'Email o contraseña incorrectos', 401


@app.route('/logout/')
def logout():
    session.clear()
    return redirect('/')


@app.route('/canal/<int:id>')
def canal(id):
    for canal in canales:
        if canal['id'] == id:
            return render_template('canal.html', canal=canal)

    return 'Canal no encontrado', 404


@app.route('/suscribirse/<int:id>')
def suscribirse(id):
    if 'usuario' not in session:
        return redirect('/login/')

    canal_encontrado = next(
        (canal for canal in canales if canal['id'] == id),
        None
    )

    if canal_encontrado is None:
        return 'Canal no encontrado', 404

    with conectar_bd() as conn:
        suscripcion = conn.execute(
            '''
            SELECT * FROM suscripciones
            WHERE usuario_email = %s AND canal_id = %s
            ''',
            (session['usuario'], id)
        ).fetchone()

        if suscripcion:
            return 'Ya estás suscrito a este canal.'

        conn.execute(
            '''
            INSERT INTO suscripciones (usuario_email, canal_id)
            VALUES (%s, %s)
            ''',
            (session['usuario'], id)
        )

    enviar_correo(
        session['usuario'],
        canal_encontrado['nombre']
    )

    return 'Te has suscrito correctamente. Revisa tu correo.'


@app.route('/suscripciones/')
def suscripciones():
    if 'usuario' not in session:
        return redirect('/login/')

    with conectar_bd() as conn:
        filas = conn.execute(
            '''
            SELECT canal_id FROM suscripciones
            WHERE usuario_email = %s
            ''',
            (session['usuario'],)
        ).fetchall()

    ids = [fila[0] for fila in filas]

    mis_canales = [
        canal for canal in canales
        if canal['id'] in ids
    ]

    return render_template(
        'suscripciones.html',
        canales=mis_canales
    )


@app.route('/cancelar-suscripcion/<int:id>', methods=['POST'])
def cancelar_suscripcion(id):
    if 'usuario' not in session:
        return redirect('/login/')

    with conectar_bd() as conn:
        conn.execute(
            '''
            DELETE FROM suscripciones
            WHERE usuario_email = %s AND canal_id = %s
            ''',
            (session['usuario'], id)
        )

    return redirect('/suscripciones/')


@app.route('/probar-correo/')
def probar_correo():
    if 'usuario' not in session:
        return redirect('/login/')

    enviar_correo(
        session['usuario'],
        'Videojuegos'
    )

    return 'Correo de prueba enviado correctamente'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)