from flask import Blueprint, render_template
from flask_login import login_required, current_user

survey = Blueprint("survey", __name__, template_folder='templates')

@survey.route('/dashboard')
@login_required
def dashboard():
    return render_template("survey/dashboard.html", username=current_user.username)
  
@survey.route('/create')
@login_required
def create():
  return render_template("survey/create.html")