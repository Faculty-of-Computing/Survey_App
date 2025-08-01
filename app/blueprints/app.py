from flask import Flask
from app.blueprints.extensions import db, migrate
from flask_login import LoginManager

def create_app():
  app = Flask(__name__, template_folder='../templates', static_folder='../static')
  app.config['SECRET_KEY'] = 'replace-this-with-a-strong-secret-key'
  app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://flaskuser:Misterambrose1$@localhost/survey_db"
  db.init_app(app)
  migrate.init_app(app, db)
  
  login_manager = LoginManager()
  login_manager.init_app(app)

  @login_manager.user_loader
  def load_user(user_id):
      from app.blueprints.people.models import User
      return User.query.get(int(user_id))
  
  
  from app.blueprints.people.route import auth
  from app.blueprints.core.route import home
  from app.blueprints.survey.route import survey
  app.register_blueprint(auth, url_prefix='/auth')
  app.register_blueprint(home)
  app.register_blueprint(survey, url_prefix='/survey')
  
  return app