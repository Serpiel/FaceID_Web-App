from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import base64
import os
from dotenv import load_dotenv

from connect import connect_to_dynamodb, get_users_table

load_dotenv()
app = Flask(__name__)
app.secret_key = 'APP_SECRET_KEY'

db = connect_to_dynamodb()
users_table = get_users_table(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        photo_b64 = request.form.get('photo_base64')

        if not email or not password or not password_confirm:
            flash("Veuillez remplir tous les champs obligatoires.", "error")
            return redirect(url_for('register'))

        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('register'))

        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('register'))

        photo_filename = None
        if photo_b64:
            try:
                photo_data = photo_b64.split(',')[1]
                photo_filename = f"{uuid.uuid4().hex}.jpg"
                filepath = os.path.join('static', 'faces', photo_filename)
                with open(filepath, "wb") as fh:
                    fh.write(base64.b64decode(photo_data))
            except Exception as e:
                print(f"Erreur image: {e}")

        # Enregistrement dans DynamoDB (avec date_creation)
        hashed_password = generate_password_hash(password)
        date_creation = datetime.now().isoformat()

        users_table.put_item(
            Item={
                'email': email,
                'password': hashed_password,
                'date_creation': date_creation,
                'photo_path': photo_filename
            }
        )
        flash("Inscription réussie ! Vous pouvez vous connecter.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Veuillez remplir tous les champs.", "error")
            return redirect(url_for('login'))

        # 1. Chercher l'utilisateur dans la base de données
        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')

        # 2. Vérifier si l'utilisateur existe ET si le mot de passe correspond au hash
        if user and check_password_hash(user['password'], password):
            # 3. Créer la session utilisateur
            session['user_email'] = user['email']
            flash("Connexion réussie !", "success")
            return redirect(url_for('index'))
        else:
            flash("Email ou mot de passe incorrect.", "error")
            return redirect(url_for('login'))

    # Afficher le formulaire si c'est une requête GET
    return render_template('login.html')

# --- ROUTE : DÉCONNEXION ---
@app.route('/logout')
def logout():
    # Supprimer l'email de la session
    session.pop('user_email', None)
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)