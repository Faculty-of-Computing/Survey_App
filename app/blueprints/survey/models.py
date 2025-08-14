from app.blueprints.extensions import db
from app.blueprints.people.models import User
from datetime import datetime

class Survey(db.Model):
    __tablename__ = 'surveys'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    publish = db.Column(db.Boolean, default=False)
    response = db.Column(db.Text, nullable=True) 
        # new timestamp columns:
    created_at  = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now()
    )
    updated_at  = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=db.func.now()
    )

    
    user_id = db.Column(db.Integer, db.ForeignKey('users.uid'), nullable=False)
    user = db.relationship(
        'User',
        back_populates='surveys'
    )

   
    questions = db.relationship('Question', backref='survey', cascade='all, delete-orphan')

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    qtype = db.Column(db.String(50), nullable=False)
    required = db.Column(db.Boolean, default=False)
    allowed_types = db.Column(db.String(255), nullable=True)
    max_size_mb = db.Column(db.Integer, nullable=True)
    
class Response(db.Model):
    __tablename__ = "responses"
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.uid"), nullable=True)  # optional for anonymous
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    survey = db.relationship("Survey", backref=db.backref("responses", lazy=True))
    answers = db.relationship("Answer", backref="response", cascade="all, delete-orphan")

class Answer(db.Model):
    __tablename__ = "answers"
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)
    answer_number = db.Column(db.Float, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)

    question = db.relationship("Question")