from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.dialects.sqlite import insert

from . import db
from .admin import admin
from .models import ResumeDocument
from .profile import read_profile, save_profile
from .security import MAX_PDF_SIZE


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    limit: int
    required: bool = False
    rows: int = 0
    choices: tuple = ()
    kind: str = "text"


PROFILE_FIELDS = (
    Field("tagline", "Professional focus", 70, True),
    Field("headline", "Homepage headline", 48, True),
    Field("headline_accent", "Accented second line", 40),
    Field("intro", "Homepage introduction", 420, True, rows=3),
    Field("location", "Location", 100),
    Field("about_lead", "About page introduction", 260, True, rows=2),
    Field("about_text", "About page biography", 4000, True, rows=9),
)
RESUME_FIELDS = (Field("resume_headline", "Résumé headline", 180, True),)
WORK_FIELDS = (
    Field("company", "Company", 100, True),
    Field("role", "Role", 120, True),
    Field("location", "Location", 100),
    Field("period", "Dates", 70),
    Field("story", "Description", 1500, True, rows=4),
    Field("outcome", "Outcome", 500, rows=2),
)
FEATURE_FIELDS = (
    Field("featured", "Show in Selected work", 3, choices=(("no", "No"), ("yes", "Yes"))),
    Field("title", "Card headline", 100),
    Field("intro", "Card summary", 400, rows=3),
    Field("figure", "Card figure", 16),
    Field("figure_label", "Figure label", 65),
    Field("art", "Card artwork", 9, choices=(("teal", "Matrix"), ("logistics", "Timeline"), ("sand", "Research dots"))),
)
RESUME_SECTIONS = (
    ("work", "Experience", "role", WORK_FIELDS + FEATURE_FIELDS),
    ("education", "Education", "title", (
        Field("institution", "Institution", 120, True),
        Field("period", "Year or dates", 70),
        Field("title", "Qualification", 150, True),
    )),
    ("skills", "Tools and skills", "title", (
        Field("title", "Skill group", 120, True),
        Field("description", "Tools or skills", 550, True, rows=3),
    )),
    ("publications", "Publications", "title", (
        Field("title", "Title", 240, True),
        Field("url", "Publication URL", 700, kind="url"),
    )),
)
MAX_SECTION_ENTRIES = 24
SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def clean_text(value):
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def check_field(field, value, errors, context=""):
    if (field.required and not value) or len(value) > field.limit:
        condition = f"is required and must be at most {field.limit} characters" if field.required else (
            f"must be at most {field.limit} characters"
        )
        errors.append(f"{context}{field.label} {condition}.")
    if field.choices and value not in dict(field.choices):
        errors.append(f"{context}{field.label} has an invalid selection.")
    if field.kind == "url" and value:
        try:
            address = urlsplit(value)
            allowed = address.scheme in {"https", "http"} and address.hostname and not address.username
        except ValueError:
            allowed = False
        if not allowed or any(char.isspace() or char == "\\" for char in value):
            errors.append(f"{context}{field.label} must be an http or https URL.")


def read_fields(fields, errors):
    values = {}
    for field in fields:
        value = clean_text(request.form.get(field.name, ""))
        check_field(field, value, errors)
        values[field.name] = value
    return values


def read_section(section, heading, fields, errors):
    names = [field.name for field in fields]
    if section == "work":
        names.append("slug")
    columns = [request.form.getlist(f"{section}-{name}") for name in names]
    if len({len(column) for column in columns}) != 1:
        errors.append(f"{heading} has missing fields. Reload the editor and try again.")
        return []
    if len(columns[0]) > MAX_SECTION_ENTRIES:
        errors.append(f"{heading} is limited to {MAX_SECTION_ENTRIES} entries.")

    rows = []
    for index, items in enumerate(zip(*(column[:MAX_SECTION_ENTRIES] for column in columns)), start=1):
        row = dict(zip(names, map(clean_text, items)))
        context = f"{heading} entry {index}: "
        for field in fields:
            check_field(field, row[field.name], errors, context)
        if section == "work" and row["featured"] == "yes" and not row["title"]:
            errors.append(f"{context}add a card headline to feature this role.")
        rows.append(row)
    return rows


def assign_work_slugs(rows, previous, errors):
    reserved = {row["slug"] for row in previous}
    used = set()
    result = []
    for entry in rows:
        row = entry.copy()
        slug = row["slug"]
        if slug and (slug not in reserved or slug in used):
            errors.append("An experience entry has an invalid link. Reload the editor and try again.")
        elif not slug:
            base = SLUG_CHARS.sub("-", row["company"].lower()).strip("-")[:70] or "experience"
            slug = base
            number = 2
            while slug in reserved or slug in used:
                slug = f"{base}-{number}"
                number += 1
            row["slug"] = slug
        used.add(slug)
        result.append(row)
    return result


def editor(template, fields, public_endpoint, sections=()):
    content, revision = read_profile()
    values = content
    form_revision = revision
    errors = []
    status = 200
    if request.method == "POST":
        submitted_revision = request.form.get("revision", type=int)
        values = {**content, **read_fields(fields, errors)}
        declared_sections = request.form.getlist("resume-section")
        if sections and declared_sections != [section[0] for section in sections]:
            errors.append("Résumé sections are missing. Reload the editor and try again.")
        for name, heading, _, entry_fields in sections:
            values[name] = read_section(name, heading, entry_fields, errors)
        candidate = values.copy()
        if sections:
            candidate["work"] = assign_work_slugs(values["work"], content["work"], errors)

        if submitted_revision != revision:
            errors.insert(0, "The site was updated in another tab. Copy your edits if needed, then reload this editor.")
            status = 409
            form_revision = submitted_revision
        elif errors:
            status = 422
        elif save_profile(candidate, revision):
            flash("Your changes are live.")
            return redirect(url_for(request.endpoint), code=303)
        else:
            errors.append("The site was updated in another tab. Copy your edits if needed, then reload this editor.")
            status = 409

    has_custom_pdf = bool(sections) and db.session.scalar(
        db.select(ResumeDocument.id).where(ResumeDocument.id == 1)
    ) is not None
    return render_template(
        template, fields=fields, values=values, revision=form_revision, sections=sections,
        public_endpoint=public_endpoint, has_custom_pdf=has_custom_pdf, max_entries=MAX_SECTION_ENTRIES,
        errors=errors,
    ), status


@admin.route("/admin/profile", methods=["GET", "POST"])
def profile():
    return editor("admin/profile.html", PROFILE_FIELDS, "pages.about")


@admin.route("/admin/resume", methods=["GET", "POST"])
def resume():
    return editor("admin/resume.html", RESUME_FIELDS, "pages.resume", RESUME_SECTIONS)


@admin.post("/admin/resume/pdf")
def resume_pdf():
    if request.form.get("action") == "reset":
        db.session.execute(db.delete(ResumeDocument).where(ResumeDocument.id == 1))
        db.session.commit()
        flash("The bundled résumé PDF is now available.")
        return redirect(url_for("admin.resume"), code=303)

    upload = request.files.get("pdf")
    data = upload.stream.read(MAX_PDF_SIZE + 1) if upload and upload.filename.lower().endswith(".pdf") else b""
    if len(data) > MAX_PDF_SIZE:
        flash("Choose a résumé PDF of 4 MB or smaller.", "error")
    elif not data.startswith(b"%PDF-") or not data.rstrip().endswith(b"%%EOF"):
        flash("Choose a valid PDF file.", "error")
    else:
        statement = insert(ResumeDocument).values(id=1, payload=data)
        db.session.execute(statement.on_conflict_do_update(
            index_elements=[ResumeDocument.id], set_={"payload": statement.excluded.payload},
        ))
        db.session.commit()
        flash("The new résumé PDF is available for download.")
    return redirect(url_for("admin.resume"), code=303)
