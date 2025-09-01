from flask import Flask, redirect,url_for
from app.blueprints.extensions import db, migrate, mail
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

csrf = CSRFProtect()

load_dotenv()

def create_app():
  app = Flask(__name__, template_folder='../templates', static_folder='../static')
  @app.route('/')
  def index():
    return redirect(url_for('auth.login'))
    # Configurations
  app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
  app.config['WTF_CSRF_ENABLED'] = True
  csrf.init_app(app)
  app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
  
  @app.context_processor
  def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

  # Mail config
  app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
  app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
  app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'true'
  app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
  app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
  app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
  
  cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
  )

  
  
  db.init_app(app)
  migrate.init_app(app, db)
  mail.init_app(app)
  
  login_manager = LoginManager()
  login_manager.init_app(app)
  # rate_limit_tracker = {}

  @login_manager.user_loader
  def load_user(user_id):
      from app.blueprints.people.models import User
      return User.query.get(int(user_id))
  
  
  from app.blueprints.people.route import auth
  from app.blueprints.survey.route import survey
  app.register_blueprint(auth, url_prefix='/auth')
  app.register_blueprint(survey, url_prefix='/survey')
  
  return app