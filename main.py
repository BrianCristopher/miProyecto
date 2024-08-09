from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
import os
import datetime
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
import hashlib
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'mysecretkey'
bcrypt = Bcrypt(app)

# Conexión a MongoDB
try:
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb+srv://Cristopher:BIL9830BI@cluster0.7kgkid2.mongodb.net/')
    client = MongoClient(mongo_uri)
    db = client.bd3
    usuarios_collection = db.usuarios
    certificados_collection = db.certificados
    print("Conexión a MongoDB establecida correctamente.")
except Exception as e:
    print(f"Error al conectar a MongoDB: {e}")
    usuarios_collection = None
    certificados_collection = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            apellido_paterno = request.form.get('apellido_paterno')
            apellido_materno = request.form.get('apellido_materno')
            fecha_nacimiento = request.form.get('fecha_nacimiento')
            correo_registro = request.form.get('correo_registro')
            contraseña = request.form.get('contraseña_registro')

            if not all([nombre, apellido_paterno, apellido_materno, fecha_nacimiento, correo_registro, contraseña]):
                flash("Todos los campos son requeridos.", "error")
                return render_template('register.html')

            if usuarios_collection is not None:
                hashed_password = bcrypt.generate_password_hash(contraseña).decode('utf-8')
                result = usuarios_collection.insert_one({
                    'nombre': nombre,
                    'apellido_paterno': apellido_paterno,
                    'apellido_materno': apellido_materno,
                    'fecha_nacimiento': fecha_nacimiento,
                    'correo_registro': correo_registro,
                    'contraseña': hashed_password
                })

                if result.acknowledged:
                    flash("Usuario agregado exitosamente.", "success")
                else:
                    flash("No se pudo agregar el usuario.", "error")
            else:
                flash("No se pudo conectar a la base de datos.", "error")
        except Exception as e:
            flash(f"Error al enviar los datos: {e}", "error")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            print(f"Datos recibidos: username={username}, password={password}")  # Para depuración

            if not all([username, password]):
                flash("Todos los campos son requeridos.", "error")
                return render_template('login.html')

            if usuarios_collection is not None:
                user = usuarios_collection.find_one({'correo_registro': username})
                if user:
                    print(f"Usuario encontrado: {user}")  # Para depuración

                if user and bcrypt.check_password_hash(user['contraseña'], password):
                    flash("Inicio de sesión exitoso.", "success")
                    return redirect(url_for('create_certificate'))
                else:
                    flash("Credenciales inválidas.", "error")
                    print("Error: Credenciales inválidas")
            else:
                flash("No se pudo conectar a la base de datos.", "error")
                print("Error: No se pudo conectar a la base de datos")
        except Exception as e:
            flash(f"Error al enviar los datos: {e}", "error")
            print(f"Error al procesar el inicio de sesión: {e}")

    return render_template('login.html')

@app.route('/create_certificate', methods=['GET', 'POST'])
def create_certificate():
    if request.method == 'POST':
        try:
            company = request.form.get('company')
            domain = request.form.get('domain')
            issue_date = request.form.get('issue_date')
            expiry_date = request.form.get('expiry_date')
            issuer = request.form.get('issuer')
            algorithm = request.form.get('algorithm')

            if not all([company, domain, issue_date, expiry_date, issuer, algorithm]):
                flash("Todos los campos son requeridos.", "error")
                return render_template('create_certificate.html')

            # Lógica de encriptación
            concatenated_data = f"{company}{domain}{issue_date}{expiry_date}{issuer}".encode('utf-8')
            if algorithm == 'SHA256':
                encrypted_data = hashlib.sha256(concatenated_data).hexdigest()
            elif algorithm == 'SHA512':
                encrypted_data = hashlib.sha512(concatenated_data).hexdigest()

            # Guardado en la base de datos
            result = certificados_collection.insert_one({
                'company': company,
                'domain': domain,
                'issue_date': datetime.datetime.strptime(issue_date, '%Y-%m-%d'),
                'expiry_date': datetime.datetime.strptime(expiry_date, '%Y-%m-%d'),
                'issuer': issuer,
                'algorithm': algorithm,
                'encrypted_data': encrypted_data
            })

            if result.acknowledged:
                flash("Certificado creado exitosamente.", "success")
                return redirect(url_for('manage_certificates'))
            else:
                flash("No se pudo crear el certificado.", "error")
        except Exception as e:
            flash(f"Error al crear el certificado: {e}", "error")
            print(f"Error: {e}")
    return render_template('create_certificate.html')

@app.route('/manage_certificates')
def manage_certificates():
    try:
        certificates = list(certificados_collection.find())
        now = datetime.datetime.now()
        for certificate in certificates:
            if certificate['expiry_date'] < now:
                certificate['expired'] = True
            else:
                certificate['expired'] = False
        return render_template('manage_certificates.html', certificates=certificates)
    except Exception as e:
        flash(f"Error al gestionar certificados: {e}", "error")
        print(f"Error: {e}")
    return redirect(url_for('index'))

@app.route('/edit_certificate/<id>', methods=['GET', 'POST'])
def edit_certificate(id):
    if request.method == 'POST':
        try:
            company = request.form.get('company')
            domain = request.form.get('domain')
            issue_date = request.form.get('issue_date')
            expiry_date = request.form.get('expiry_date')
            issuer = request.form.get('issuer')
            algorithm = request.form.get('algorithm')

            if not all([company, domain, issue_date, expiry_date, issuer, algorithm]):
                flash("Todos los campos son requeridos.", "error")
                return render_template('edit_certificate.html', id=id)

            result = certificados_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'company': company,
                    'domain': domain,
                    'issue_date': datetime.datetime.strptime(issue_date, '%Y-%m-%d'),
                    'expiry_date': datetime.datetime.strptime(expiry_date, '%Y-%m-%d'),
                    'issuer': issuer,
                    'algorithm': algorithm
                }}
            )

            if result.modified_count > 0:
                flash("Certificado actualizado exitosamente.", "success")
                return redirect(url_for('manage_certificates'))
            else:
                flash("No se pudo actualizar el certificado.", "error")
                return redirect(url_for('manage_certificates'))
        except Exception as e:
            flash(f"Error al actualizar el certificado: {e}", "error")
            print(f"Error: {e}")
            return redirect(url_for('manage_certificates'))
    else:
        certificate = certificados_collection.find_one({'_id': ObjectId(id)})
        if certificate:
            return render_template('edit_certificate.html', certificate=certificate)
        else:
            flash("Certificado no encontrado.", "error")
            return redirect(url_for('manage_certificates'))

@app.route('/delete_certificate/<id>')
def delete_certificate(id):
    try:
        certificados_collection.delete_one({'_id': ObjectId(id)})
        flash("Certificado eliminado exitosamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar el certificado: {e}", "error")
    return redirect(url_for('manage_certificates'))

if __name__ == '__main__':
    app.run(debug=True, port=8090)


