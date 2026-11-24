import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import db
from .models import ContactSubmission
from .profile import WORK
from .projects import published_posts


pages = Blueprint("pages", __name__)


@pages.get("/")
def index():
    recent_posts = db.session.scalars(published_posts().limit(3)).all()
    return render_template("index.html", recent_posts=recent_posts, work=WORK)


@pages.get("/about")
def about():
    return render_template("about.html")


@pages.get("/resume")
def resume():
    return render_template("resume.html", work=WORK)


@pages.post("/submit_contact")
@pages.route("/contact", methods=["GET", "POST"])
def contact():
    values = {}
    errors = {}
    if request.method == "POST":
        if request.form.get("website"):
            flash("Thanks for getting in touch.")
            return redirect(url_for("pages.contact"), code=303)

        limits = {"name": 150, "email": 150, "subject": 300, "message": 5000}
        for field, limit in limits.items():
            value = request.form.get(field, "").strip()
            values[field] = value
            if not value or len(value) > limit:
                errors[field] = f"Enter between 1 and {limit} characters."
        if "email" not in errors:
            if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", values["email"]):
                errors["email"] = "Enter a valid email address."

        if not errors:
            db.session.add(ContactSubmission(**values))
            db.session.commit()
            flash("Thanks for getting in touch. Your message has been received.")
            return redirect(url_for("pages.contact"), code=303)

    return render_template(
        "contact.html", values=values, errors=errors,
    ), (422 if errors else 200)
