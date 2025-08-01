from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.blueprints.extensions import db
from app.blueprints.people.models import User
from app.blueprints.survey.route import survey
from flask_login import login_user, login_required, logout_user

auth = Blueprint("auth", __name__, template_folder='templates')

@auth.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        error = ""
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "Email already registered. Please use a different email or log in."
            return render_template("people/register.html", error=error)
        if confirm_password != password:
            error = "Passwords do not match"
            return render_template("people/register.html", error=error)
        else:
            error = ""
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            user = User(email=email, username=username, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful", "success")
            return redirect(url_for('auth.login'))
    
    return render_template("people/register.html")

@auth.route("/login", methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # username = user.username
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for('survey.dashboard'))
        else:
            error = "Invalid email or password"
            return render_template("people/login.html", error=error)
    return render_template("people/login.html")


@auth.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for('auth.login'))