from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime
import uuid
import base64
from face_auth import verifier_visage
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

        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['password'], password):
            session['user_email'] = user['email']
            flash("Connexion réussie !", "success")
            return redirect(url_for('index'))
        else:
            flash("Email ou mot de passe incorrect.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/login/face_step')
def login_face_page():
    email = request.args.get('email', '')
    return render_template('login_face.html', email=email)

# --- ROUTE : TRAITEMENT IA (Toujours la même) ---
# --- ROUTE : CONNEXION FACIALE ---
@app.route('/login/face', methods=['POST'])
def login_face():
    # 1. Récupérer les données envoyées par le JavaScript
    data = request.get_json()
    email = data.get('email')
    photo_live_b64 = data.get('photo_base64')

    if not email or not photo_live_b64:
        return jsonify({"success": False, "message": "Email ou photo manquant."})

    # 2. Chercher l'utilisateur dans DynamoDB
    response = users_table.get_item(Key={'email': email})
    user = response.get('Item')

    if not user:
        return jsonify({"success": False, "message": "Cet utilisateur n'existe pas."})
    
    if not user.get('photo_path'):
        return jsonify({"success": False, "message": "Aucun visage enregistré pour ce compte."})

    # 3. Comparer les visages via notre fichier face_auth.py
    is_match, msg = verifier_visage(email, photo_live_b64, user['photo_path'])

    if is_match:
        # Connecter l'utilisateur
        session['user_email'] = email
        return jsonify({"success": True, "message": msg})
    else:
        return jsonify({"success": False, "message": msg})
# --- ROUTE : DÉCONNEXION ---
@app.route('/logout')
def logout():
    # Supprimer l'email de la session
    session.pop('user_email', None)
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)