# routes.py
import json
from flask import Blueprint, render_template, request, url_for, abort, jsonify, flash, redirect
from flask_login import login_required, current_user
from .models import db, Survey, Question, Answer, Response
from app.blueprints.survey.utils import upload_to_cloudinary
import re

survey = Blueprint('survey', __name__, template_folder='templates', url_prefix='/survey')


def parse_platform_from_ua(ua: str, ref: str = "") -> str:
    ua = (ua or "").lower()
    ref = (ref or "").lower()
    if "fbav" in ua or "fban" in ua or "facebook" in ua or "m.facebook" in ref:
        return "Facebook"
    if "whatsapp" in ua or "whatsapp" in ref:
        return "WhatsApp"
    if "instagram" in ua or "instagram" in ref:
        return "Instagram"
    if "linkedin" in ua or "linkedin" in ref:
        return "LinkedIn"
    if "twitter" in ua or "x-ios" in ua or "tweet" in ref:
        return "Twitter"
    if "crios" in ua:
        return "Chrome (iOS)"
    if "edg" in ua or "edge" in ua:
        return "Edge"
    if "firefox" in ua:
        return "Firefox"
    if "chrome" in ua:
        return "Chrome"
    if "safari" in ua:
        return "Safari"
    if "iphone" in ua or "ipad" in ua:
        return "iOS Browser"
    if "android" in ua:
        return "Android Browser"
    return "Unknown"




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


@survey.route('/publish', methods=['POST'])
@login_required
def publish_survey():
    try:
        data = request.get_json() or {}
        survey_id = data.get('survey_id')
        
        if not survey_id:
            return jsonify({'success': False, 'error': 'Survey ID required'}), 400
        
        survey_obj = Survey.query.filter_by(id=survey_id, user_id=current_user.uid).first()
        if not survey_obj:
            return jsonify({'success': False, 'error': 'Survey not found'}), 404
        
        if survey_obj.publish:
            return jsonify({'success': False, 'error': 'Survey already published'}), 400
        
        survey_obj.publish = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Survey published successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    

@survey.route('/create', methods=['GET'])
@login_required
def create():
    return render_template('survey/create.html')


@survey.route('/save', methods=['POST'])
@login_required
def save_survey():
    """
    Receives JSON payload from frontend, validates, and stores Survey + Questions.
    """
    data = request.get_json() or {}
    info = data.get('info', {})
    questions = data.get('questions', [])

    title = info.get('title', '').strip()
    if not title or len(title) > 255:
        abort(400, 'Title is required (≤255 chars)')

    description = info.get('description', '').strip()
    if len(description) > 2000:
        abort(400, 'Description must be ≤2000 chars')

    publish = bool(info.get('publish', False))

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
            allowed_list = [ft.strip() for ft in q.get('allowed_types', []) if ft.strip()]
            if not all(file_type_pattern.match(ft) for ft in allowed_list):
                abort(400, f'Question {idx}: invalid file types')

            max_mb = q.get('max_size_mb')
            if not isinstance(max_mb, int) or max_mb < 1 or max_mb > 100:
                abort(400, f'Question {idx}: max_size_mb must be 1–100')

            allowed = json.dumps(allowed_list)

        elif qtype in ('Multiple Choice', 'Checkboxes', 'Multiple Selection'):
            opts = [str(opt).strip() for opt in q.get('allowed_types', []) if str(opt).strip()]
            if len(opts) == 0:
                abort(400, f'Question {idx}: multiple-choice questions require at least one option')
            allowed = json.dumps(opts)

        q_objs.append(Question(
            text=text,
            qtype=qtype,
            required=required,
            allowed_types=allowed,
            max_size_mb=max_mb
        ))

    survey_obj = Survey(title=title, description=description, publish=publish, user_id=current_user.uid)
    db.session.add(survey_obj)
    db.session.flush()

    for qobj in q_objs:
        qobj.survey_id = survey_obj.id
        db.session.add(qobj)

    db.session.commit()
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

        if q.allowed_types:
            try:
                opts = json.loads(q.allowed_types)
                if isinstance(opts, list):
                    q_info["options"] = opts
                else:
                    q_info["options"] = [str(opts)]
            except Exception:
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
def submit_survey(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)

    new_response = Response(survey_id=survey_id, user_id=current_user.uid if current_user.is_authenticated else None)

    # capture client-sent platform first
    platform_from_form = request.form.get("platform")
    # capture source query param (if user clicked a share link with ?source=)
    platform_from_qs = request.args.get("source")
    if platform_from_form:
        platform = platform_from_form
    elif platform_from_qs:
        platform = platform_from_qs
    else:
        platform = parse_platform_from_ua(request.headers.get("User-Agent", ""), request.referrer)

    new_response.platform = platform

    db.session.add(new_response)
    db.session.flush()
    # ... continue saving answers ...

    
    
    db.session.add(new_response)
    db.session.flush()

    for question in survey_obj.questions:
        field_name = f"q{question.id}"
        answer_data = {}

        if question.qtype == "File Upload":
            file = request.files.get(field_name)
            if file and file.filename:
                # Upload to Cloudinary
                url = upload_to_cloudinary(file, folder="survey_files")
                if not url:
                    abort(500, f"Failed to upload file for '{question.text}'")
                answer_data["file_path"] = url

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
            answer_data["answer_text"] = request.form.get(field_name, "").strip()

        answer_entry = Answer(
            response_id=new_response.id,
            question_id=question.id,
            **answer_data
        )
        db.session.add(answer_entry)

    db.session.commit()
    return render_template("survey/thanks.html", survey=survey_obj)


@survey.route("/share/<int:survey_id>")
@login_required
def share_survey(survey_id):
    s = Survey.query.get_or_404(survey_id)
    if not s.publish:
        abort(403, "Survey not published")
    link = url_for("survey.respond", survey_id=s.id, _external=True)
    return jsonify({"link": link})


@survey.route("/respond/<int:survey_id>", methods=["GET"])
def respond(survey_id):
    survey = Survey.query.get_or_404(survey_id)

    # Build questions list with parsed options (so template can use q.options)
    questions = []
    for q in survey.questions:
        opts = []
        if q.allowed_types:
            try:
                opts = json.loads(q.allowed_types)
            except Exception:
                # fallback if stored as comma-separated string
                opts = [opt.strip() for opt in q.allowed_types.split(",") if opt.strip()]
        # attach parsed options to object for template convenience
        q.options = opts
        questions.append(q)

    return render_template("survey/response.html", survey=survey, questions=questions)


# @survey.route("/thanks/<int:survey_id>")
# def thanks(survey_id):
#     survey = Survey.query.get_or_404(survey_id)
#     return render_template("thanks.html", survey=survey)


@survey.route("/results/<int:survey_id>")
def results(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    responses = Response.query.filter_by(survey_id=survey_id).all()
    grouped = {}

    for r in responses:
        platform = r.platform or "Unknown"
        parsed_answers = []
        for ans in r.answers:
            opts = []
            if ans.question.allowed_types:
                try:
                    opts = json.loads(ans.question.allowed_types)
                except Exception:
                    opts = []
            parsed_answers.append({
                "question": ans.question,
                "answer_text": ans.answer_text,
                "answer_number": ans.answer_number,
                "file_path": ans.file_path,
                "options": opts  
            })
        grouped.setdefault(platform, []).append({
            "submitted_at": r.submitted_at,
            "answers": parsed_answers
        })

    return render_template("survey/result.html", survey=survey, grouped=grouped)
