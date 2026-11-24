from datetime import datetime, timezone
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy.orm import relationship

from . import db


def generate_uuid():
    return str(uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class ContactSubmission(db.Model):
    __tablename__ = "contact_submissions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    subject = db.Column(db.String(300))
    message = db.Column(db.Text)


class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)


class Category(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    category = db.Column(db.String(80))
    subcategory = db.Column(db.String(80))

    @property
    def label(self):
        return " / ".join(part for part in (self.category, self.subcategory) if part)


class MarkdownFile(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(80))
    category_id = db.Column(db.String(36), db.ForeignKey("category.id"))
    category = relationship("Category", backref="markdown_files")
    content = db.Column(db.Text)
    upload_date = db.Column(db.DateTime)
    modification_date = db.Column(db.DateTime)
    author_name = db.Column(db.String(80))
    slug = db.Column(db.String(120), unique=True, nullable=False)
    summary = db.Column(db.String(300), nullable=False, default="")
    published_at = db.Column(db.DateTime)

    @property
    def is_published(self):
        return self.published_at is not None
