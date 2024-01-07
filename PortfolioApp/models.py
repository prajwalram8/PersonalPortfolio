from . import db  # Import the db instance from the __init__.py
from flask_login import UserMixin
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class ContactSubmission(db.Model):
    __tablename__ = 'contact_submissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    subject = db.Column(db.String(300))
    message = db.Column(db.Text)

# User class
class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid) # autoincrement=True is usually implicit
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

# Model for Categories
class Category(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    category = db.Column(db.String(80))
    subcategory = db.Column(db.String(80))

# Model for Markdown files
class MarkdownFile(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(80))
    category_id = db.Column(db.String(36), db.ForeignKey('category.id'))
    content = db.Column(db.Text)
    upload_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    author_name = db.Column(db.String(80))