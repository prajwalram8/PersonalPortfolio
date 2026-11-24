from io import BytesIO
from pathlib import Path
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

from . import db
from .models import ContactSubmission, ResumeDocument
from .profile import read_profile
from .projects import published_posts
from .security import rate_limit


pages = Blueprint("pages", __name__)


@pages.get("/")
def index():
    recent_posts = db.session.scalars(published_posts().limit(3)).all()
    profile, _ = read_profile()
    work = [entry for entry in profile["work"] if entry["featured"] == "yes"]
    return render_template("index.html", recent_posts=recent_posts, profile=profile, work=work)


@pages.get("/about")
def about():
    profile, _ = read_profile()
    paragraphs = re.split(r"\n\s*\n", profile["about_text"])
    return render_template("about.html", profile=profile, paragraphs=paragraphs)


@pages.get("/resume")
def resume():
    profile, _ = read_profile()
    return render_template("resume.html", profile=profile)


@pages.get("/resume.pdf")
def resume_pdf():
    bundled = Path(current_app.static_folder) / "pdf" / "Prajwal Ram Gowda.pdf"
    custom = db.session.get(ResumeDocument, 1)
    return send_file(
        BytesIO(custom.payload) if custom else bundled,
        mimetype="application/pdf", as_attachment=True,
        download_name="Prajwal Ram Gowda.pdf", max_age=0,
    )


@pages.post("/submit_contact")
@pages.route("/contact", methods=["GET", "POST"])
@rate_limit("contact")
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
