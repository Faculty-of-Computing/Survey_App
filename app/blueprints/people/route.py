from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import random
import time
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from app.blueprints.extensions import db, mail
from app.blueprints.people.models import User
# from app.blueprints.survey.route import survey
from flask_login import login_user, login_required, logout_user

auth = Blueprint("auth", __name__, template_folder='templates')

def generate_otp():
    return str(random.randint(100000, 999999))



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
            otp = generate_otp()

            # Store user info in session temporarily
            session['temp_user'] = {
                'email': email,
                'username': username,
                'password': hashed_password,
                'otp': otp,
                'otp_expiry': time.time() + 300  # 5 minutes from now
            }

            # Send OTP email
            msg = Message("Your OTP Code", recipients=[email])
            msg.body = f"Your OTP is {otp}. It expires in 5 minutes."
            try:
                mail.send(msg)
                print("OTP email sent to:", email)
                flash("OTP sent to your email. Please verify to complete registration.", "info")
                return redirect(url_for('auth.verify_otp_form'))
            except Exception as e:
                print("Failed to send OTP email:", e)
                error = "Failed to send OTP. Please try again later."
                return render_template("people/register.html", error=error)
        
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


@auth.route("/verify_otp", methods=['GET', 'POST'])
def verify_otp_form():
    error = ""
    remaining_time = 0
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        temp_user = session.get('temp_user')
        

        if not temp_user:
            flash("Session expired or invalid access.", "danger")
            return redirect(url_for('auth.register'))

        if time.time() > temp_user['otp_expiry']:
            session.pop('temp_user')
            flash("OTP expired. Please register again.", "danger")
            return redirect(url_for('auth.register'))

        if user_otp == temp_user['otp']:
            error = ""
            new_user = User(
                email=temp_user['email'],
                username=temp_user['username'],
                password=temp_user['password']
            )
            db.session.add(new_user)
            db.session.commit()
            session.pop('temp_user')
            flash("Registration successful.", "success")
            return redirect(url_for('auth.login'))
        else:
            error = "Invalid OTP"
            flash("Invalid OTP.", "danger")
    print("Remaining time for OTP:", remaining_time)
    if 'temp_user' in session and 'otp_expiry' in session['temp_user']:
        expiry = session['temp_user']['otp_expiry']
        print("OTP expiry time:", expiry)
        remaining_time = max(int(expiry - time.time()), 0)
        if remaining_time < 0:
            remaining_time = 0

    return render_template("people/verify_otp.html", error=error, remaining_time=remaining_time)

@auth.route("/resend_otp", methods=['POST'])
def resend_otp():
    temp_user = session.get('temp_user')
    if not temp_user:
        flash("Session expired or invalid access.", "danger")
        return redirect(url_for('auth.register'))

    # Generate a new OTP
    new_otp = generate_otp()
    temp_user['otp'] = new_otp
    temp_user['otp_expiry'] = time.time() + 300
    session['temp_user'] = temp_user
    # Send the new OTP via email
    msg = Message("Your New OTP Code", recipients=[temp_user['email']])
    msg.body = f"Your new OTP is {new_otp}. It expires in 5 minutes."
    try:
        mail.send(msg)
        flash("New OTP sent to your email.", "info")
    except Exception as e:
        print("Failed to send OTP email:", e)
        flash("Failed to send new OTP. Please try again later.", "danger")




