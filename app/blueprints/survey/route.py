# routes.py
from flask import Blueprint, render_template, request, url_for , abort, jsonify
from flask_login import login_required, current_user
from .models import db, Survey, Question
from app.blueprints.people.models import User
import re

survey = Blueprint('survey', __name__, template_folder='templates', url_prefix='/survey')

@survey.route('/dashboard')
@login_required
def dashboard():
    surveys = Survey.query.filter_by(user_id=current_user.uid).all()
    for s in surveys:
        s.questions_length = len(s.questions)
    return render_template(
        'survey/dashboard.html',
        username=current_user.username,
        surveys=surveys
    )

@survey.route('/create', methods=['GET'])
@login_required
def create():
    return render_template('survey/create.html')

@survey.route('/save', methods=['POST'])
@login_required
def save_survey():
    """
    Receives JSON payload from frontend, validates, and stores Survey + Questions.
    Expected JSON:
    {
      "info": {"title":"...","description":"...","publish":true},
      "questions": [{...}, ...]
    }
    """
    data = request.get_json() or {}
    info = data.get('info', {})
    questions = data.get('questions', [])

    # Validate survey info
    title = info.get('title', '').strip()
    if not title or len(title) > 255:
        abort(400, 'Title is required (≤255 chars)')

    description = info.get('description', '').strip()
    if len(description) > 2000:
        abort(400, 'Description must be ≤2000 chars')

    publish = bool(info.get('publish', False))

    # Validate questions
    if not isinstance(questions, list) or len(questions) == 0:
        abort(400, 'At least one question required')

    file_type_pattern = re.compile(r'^\.[a-zA-Z0-9]+$')
    q_objs = []
    for idx, q in enumerate(questions, start=1):
        text = q.get('text', '').strip()
        if not text:
            abort(400, f'Question {idx}: text required')

        qtype = q.get('type')
        required = bool(q.get('required', False))

        allowed = None
        max_mb = None
        if qtype == 'File Upload':
            allowed_list = q.get('allowed_types', [])
            if not isinstance(allowed_list, list) or any(not file_type_pattern.match(ft) for ft in allowed_list):
                abort(400, f'Question {idx}: invalid file types')
            allowed = ','.join(allowed_list)

            max_mb = q.get('max_size_mb')
            if not isinstance(max_mb, int) or max_mb < 1 or max_mb > 100:
                abort(400, f'Question {idx}: max_size_mb must be 1–100')

        q_objs.append(Question(
            text=text,
            qtype=qtype,
            required=required,
            allowed_types=allowed,
            max_size_mb=max_mb
        ))

    # Save survey
    survey_obj = Survey(title=title, description=description, publish=publish, user_id=current_user.uid)
    db.session.add(survey_obj)
    db.session.flush()  # assign id

    # Save questions
    for qobj in q_objs:
        qobj.survey_id = survey_obj.id
        db.session.add(qobj)

    db.session.commit()
    #jsonify({'status': 'success', 'survey_id': survey_obj.id}), 201
    return jsonify({
        'status': 'success',
        'survey_id': survey_obj.id,
        'redirect': url_for('survey.dashboard')
    }), 201
