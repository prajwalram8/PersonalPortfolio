from pathlib import Path

import click
from flask import (
    Blueprint, Response, abort, flash, redirect, render_template, request, url_for,
)
from flask.cli import with_appcontext
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .models import Category, ContactSubmission, MarkdownFile, User, utc_now
from .projects import available_slug, render_markdown
from .security import rate_limit


admin = Blueprint("admin", __name__)
MARKDOWN_LIMIT = 256 * 1024


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@admin.before_request
def require_owner():
    if request.endpoint != "admin.login" and not current_user.is_authenticated:
        return login_manager.unauthorized()


@admin.route("/login", methods=["GET", "POST"])
@admin.route("/admin/login", methods=["GET", "POST"])
@rate_limit("login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("admin.dashboard"), code=303)
        flash("The username or password is incorrect.", "error")
    return render_template("admin/login.html")


@admin.post("/admin/logout")
def logout():
    logout_user()
    return redirect(url_for("pages.index"), code=303)


@admin.get("/admin/projects-admin")
@admin.get("/admin")
def dashboard():
    posts = db.session.scalars(db.select(MarkdownFile).order_by(MarkdownFile.modification_date.desc())).all()
    return render_template("admin/projects-admin.html", posts=posts)


@admin.get("/admin/inbox")
def inbox():
    submissions = db.session.scalars(db.select(ContactSubmission).order_by(ContactSubmission.id.desc())).all()
    return render_template("admin/admin.html", submissions=submissions)


@admin.post("/admin/inbox/<int:submission_id>/delete")
def delete_submission(submission_id):
    db.session.delete(db.get_or_404(ContactSubmission, submission_id))
    db.session.commit()
    flash("Message deleted.")
    return redirect(url_for("admin.inbox"), code=303)


@admin.route("/admin/posts/new", methods=["GET", "POST"])
@admin.route("/admin/posts/<string:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id=None):
    post = db.get_or_404(MarkdownFile, post_id) if post_id else None
    categories = db.session.scalars(db.select(Category).order_by(Category.category, Category.subcategory)).all()
    values = {
        "name": post.name or "" if post else "",
        "summary": post.summary if post else "",
        "author_name": post.author_name or "" if post else "Prajwal Ram Gowda",
        "category_id": post.category_id or "" if post else "",
        "content": post.content or "" if post else "",
    }
    if request.method == "GET":
        return render_template("admin/editor.html", post=post, values=values, categories=categories)

    values = {field: request.form.get(field, "").strip() for field in values}
    values["content"] = request.form.get("content", "")
    action = request.form.get("action", "save")
    if action not in {"import", "preview", "save", "publish"}:
        abort(400)

    if action == "import":
        upload = request.files.get("markdown")
        if not upload or Path(upload.filename).suffix.lower() != ".md":
            flash("Choose a Markdown file ending in .md.", "error")
        else:
            data = upload.stream.read(MARKDOWN_LIMIT + 1)
            if len(data) > MARKDOWN_LIMIT:
                flash("Choose a Markdown file of 256 KB or smaller.", "error")
            else:
                try:
                    values["content"] = data.decode("utf-8-sig")
                    if not values["name"]:
                        values["name"] = Path(upload.filename).stem.replace("-", " ")[:80]
                    flash("Markdown imported. Save when you’re ready.")
                except UnicodeDecodeError:
                    flash("Save the Markdown file as UTF-8 and try again.", "error")
        return render_template("admin/editor.html", post=post, values=values, categories=categories)

    errors = []
    if len(values["content"].encode("utf-8")) > MARKDOWN_LIMIT:
        errors.append("The Markdown content must be 256 KB or smaller.")
    if action == "preview" and not errors:
        return render_template(
            "admin/editor.html", post=post, values=values, categories=categories,
            preview=render_markdown(values["content"]),
        )

    for field, label, limit in (("name", "Title", 80), ("summary", "Summary", 300), ("author_name", "Author", 80)):
        if len(values[field]) > limit:
            errors.append(f"{label} must be {limit} characters or fewer.")
    if not values["name"]:
        errors.append("Enter a title.")
    category_id = values["category_id"] or None
    if category_id and not any(category.id == category_id for category in categories):
        errors.append("Choose an existing topic or leave it empty.")
    is_publishing = action == "publish" or (post is not None and post.is_published)
    if is_publishing and not values["content"].strip():
        errors.append("Add Markdown content before publishing.")
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("admin/editor.html", post=post, values=values, categories=categories), 422

    now = utc_now()
    if post is None:
        post = MarkdownFile(slug=available_slug(values["name"]), upload_date=now)
        db.session.add(post)
    post.name = values["name"]
    post.summary = values["summary"]
    post.author_name = values["author_name"]
    post.category_id = category_id
    post.content = values["content"]
    post.modification_date = now
    was_published = post.is_published
    if is_publishing and not was_published:
        post.published_at = now

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("This post could not be saved. Please try again.", "error")
        return render_template("admin/editor.html", post=post if post_id else None,
                               values=values, categories=categories), 409
    flash("Post published." if is_publishing and not was_published else "Post saved.")
    return redirect(url_for("admin.edit_post", post_id=post.id), code=303)


@admin.post("/admin/posts/<string:post_id>/unpublish")
def unpublish_post(post_id):
    post = db.get_or_404(MarkdownFile, post_id)
    post.published_at = None
    db.session.commit()
    flash("Post moved to drafts.")
    return redirect(url_for("admin.edit_post", post_id=post.id), code=303)


@admin.get("/admin/posts/<string:post_id>/markdown")
def download_markdown(post_id):
    post = db.get_or_404(MarkdownFile, post_id)
    return Response(
        post.content or "", mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{post.slug}.md"'},
    )


@admin.post("/admin/posts/<string:post_id>/delete")
def delete_post(post_id):
    db.session.delete(db.get_or_404(MarkdownFile, post_id))
    db.session.commit()
    flash("Post deleted.")
    return redirect(url_for("admin.dashboard"), code=303)


@admin.route("/admin/topics", methods=["GET", "POST"])
def topics():
    if request.method == "POST":
        category_id = request.form.get("id")
        category = db.get_or_404(Category, category_id) if category_id else Category()
        action = request.form.get("action", "save")
        if action == "delete" and category_id:
            if category.markdown_files:
                flash("Move posts out of this topic before deleting it.", "error")
            else:
                db.session.delete(category)
                db.session.commit()
                flash("Topic deleted.")
        elif action == "save":
            name = request.form.get("name", "").strip()
            subcategory = request.form.get("subcategory", "").strip()
            if not name or len(name) > 80 or len(subcategory) > 80:
                flash("Enter a topic and optional subtopic of up to 80 characters each.", "error")
            else:
                category.category = name
                category.subcategory = subcategory or None
                db.session.add(category)
                db.session.commit()
                flash("Topic saved.")
        else:
            abort(400)
        return redirect(url_for("admin.topics"), code=303)

    categories = db.session.scalars(db.select(Category).order_by(Category.category, Category.subcategory)).all()
    return render_template("admin/topics.html", categories=categories)


@click.command("create-owner")
@click.argument("username")
@click.password_option(confirmation_prompt=True)
@with_appcontext
def create_owner(username, password):
    """Create an admin login or reset its password."""
    username = username.strip()
    if not 1 <= len(username) <= 80:
        raise click.ClickException("Use a username between 1 and 80 characters.")
    if len(password) < 12:
        raise click.ClickException("Use a password of at least 12 characters.")
    owner = db.session.scalar(db.select(User).where(User.username == username))
    if owner is None:
        owner = User(username=username)
        db.session.add(owner)
    owner.password = generate_password_hash(password, method="scrypt")
    db.session.commit()
    click.echo("Owner account saved.")
