# routes.py
import os
import json
from flask import Blueprint, render_template, request, url_for , abort, jsonify
from flask_login import login_required, current_user
from .models import db, Survey, Question, Answer, Response
# from app.blueprints.people.models import User
import re

survey = Blueprint('survey', __name__, template_folder='templates', url_prefix='/survey')
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@survey.route('/dashboard')
@login_required
def dashboard():
    surveys = Survey.query.filter_by(user_id=current_user.uid).all()
    total_responses = db.session.query(Response).join(Survey).filter(
        Survey.user_id == current_user.uid
    ).count()
    responses = Survey.query.filter_by(user_id=current_user.uid, publish=True).all()
    for s in surveys:
        s.questions_length = len(s.questions)
    total_surveys = len(surveys)
    total_published = len(responses)
    return render_template(
        'survey/dashboard.html',
        username=current_user.username,
        surveys=surveys,
        responses=responses,
        total_surveys=total_surveys,
        total_published=total_published,
        total_responses=total_responses
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

        # File Upload: validate extensions and max size
        if qtype == 'File Upload':
            allowed_list = [ft.strip() for ft in q.get('allowed_types', []) if ft.strip()]
            if not all(file_type_pattern.match(ft) for ft in allowed_list):
                abort(400, f'Question {idx}: invalid file types')

            max_mb = q.get('max_size_mb')
            if not isinstance(max_mb, int) or max_mb < 1 or max_mb > 100:
                abort(400, f'Question {idx}: max_size_mb must be 1–100')

            # store JSON string of allowed extensions
            allowed = json.dumps(allowed_list)

        # Multiple Choice (and similar types that carry options)
        elif qtype in ('Multiple Choice', 'Checkboxes', 'Multiple Selection'):
            opts = [str(opt).strip() for opt in q.get('allowed_types', []) if str(opt).strip()]
            if len(opts) == 0:
                abort(400, f'Question {idx}: multiple-choice questions require at least one option')
            # store JSON string of options
            allowed = json.dumps(opts)

        # otherwise allowed remains None

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
    

@survey.route('/fetch-questions', methods=['POST'])
@login_required
def fetch_questions():
    data = request.get_json() or {}
    sid = data.get('survey_id')

    survey_obj = Survey.query.filter_by(id=sid).first()
    if not survey_obj:
        return jsonify({"error": "Survey not found"}), 404

    # Allow owner or allow if survey is published
    if survey_obj.user_id != current_user.uid and not survey_obj.publish:
        return jsonify({"error": "Survey not available"}), 403

    questions_data = []
    for q in survey_obj.questions:
        q_info = {
            "id": q.id,
            "text": q.text,
            "type": q.qtype,
            "required": q.required,
            "options": []
        }

        # If stored allowed_types, try to load JSON first
        if q.allowed_types:
            try:
                opts = json.loads(q.allowed_types)
                if isinstance(opts, list):
                    q_info["options"] = opts
                else:
                    # fallback: string -> single option
                    q_info["options"] = [str(opts)]
            except Exception:
                # backward compatibility: comma-split if it wasn't JSON
                q_info["options"] = [opt.strip() for opt in q.allowed_types.split(",") if opt.strip()]

        questions_data.append(q_info)

    return jsonify({
        "survey": {
            "id": survey_obj.id,
            "title": survey_obj.title,
            "description": survey_obj.description
        },
        "questions": questions_data
    }), 200



@survey.route('/submit/<int:survey_id>', methods=['POST'])
@login_required
def submit_survey(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)

    # Create a new Response entry
    new_response = Response(survey_id=survey_id, user_id=current_user.uid)
    db.session.add(new_response)
    db.session.flush()  # Get ID before adding answers

    for question in survey_obj.questions:
        field_name = f"q{question.id}"
        answer_data = {}

        if question.qtype == "File Upload":
            file = request.files.get(field_name)
            if file and file.filename:
                # Validate file type
                if question.allowed_types:
                    allowed_exts = [ext.lower() for ext in question.allowed_types.split(",")]
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext not in allowed_exts:
                        abort(400, f"Invalid file type for question '{question.text}'")

                # Validate file size
                if question.max_size_mb:
                    file.seek(0, os.SEEK_END)
                    size_mb = file.tell() / (1024 * 1024)
                    file.seek(0)
                    if size_mb > question.max_size_mb:
                        abort(400, f"File too large for question '{question.text}' (max {question.max_size_mb} MB)")

                # Save file
                save_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(save_path)
                answer_data["file_path"] = file.filename

        elif question.qtype == "Text Response":
            answer_data["answer_text"] = request.form.get(field_name, "").strip()

        elif question.qtype == "Multiple Choice":
            selected_option = request.form.get(field_name)
            if question.required and not selected_option:
                abort(400, f"Question '{question.text}' is required")
            answer_data["answer_text"] = selected_option

        elif question.qtype == "Rating (1–5)":
            rating = request.form.get(field_name)
            if rating and rating.isdigit():
                rating_val = int(rating)
                if 1 <= rating_val <= 5:
                    answer_data["answer_number"] = rating_val
                else:
                    abort(400, f"Invalid rating for question '{question.text}'")
            elif question.required:
                abort(400, f"Question '{question.text}' is required")

        elif question.qtype == "Slider/Range":
            slider_value = request.form.get(field_name)
            try:
                if slider_value:
                    answer_data["answer_number"] = float(slider_value)
                elif question.required:
                    abort(400, f"Question '{question.text}' is required")
            except ValueError:
                abort(400, f"Invalid slider value for question '{question.text}'")

        elif question.qtype == "Checkboxes":
            selected_values = request.form.getlist(field_name)
            if question.required and not selected_values:
                abort(400, f"Question '{question.text}' is required")
            answer_data["answer_text"] = ",".join(selected_values)

        elif question.qtype == "Date Picker":
            date_val = request.form.get(field_name)
            if question.required and not date_val:
                abort(400, f"Question '{question.text}' is required")
            answer_data["answer_text"] = date_val

        else:
            # Default to text capture for unsupported types
            answer_data["answer_text"] = request.form.get(field_name, "").strip()

        # Save answer
        answer_entry = Answer(
            response_id=new_response.id,
            question_id=question.id,
            **answer_data
        )
        db.session.add(answer_entry)

    db.session.commit()
    return jsonify({"status": "success", "message": "Responses saved"}), 200
