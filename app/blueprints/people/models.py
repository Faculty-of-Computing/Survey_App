from flask_login import UserMixin
from app.blueprints.extensions import db

class User(UserMixin, db.Model):
  __tablename__ = 'users'

  uid = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String, nullable=False)
  email = db.Column(db.String, nullable=False, unique=True)
  password = db.Column(db.String, nullable=False)
  surveys = db.relationship(
        'Survey',
        back_populates='user',
        cascade='all, delete-orphan'
    )

  def __repr__(self):
    return f"<PERSON {self.username}>"

  def get_id(self):
    return self.uid
