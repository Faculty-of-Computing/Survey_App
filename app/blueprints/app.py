from flask import Flask, redirect,url_for
from app.blueprints.extensions import db, migrate, mail
from flask_login import LoginManager
from dotenv import load_dotenv
import os


load_dotenv()

def create_app():
  app = Flask(__name__, template_folder='../templates', static_folder='../static')
  @app.route('/')
  def index():
    return redirect(url_for('auth.login'))
    # Config from environment
  app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
  app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')

  # Mail config
  app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
  app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
  app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'true'
  app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
  app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
  app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

  
  
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