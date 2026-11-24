import re
import unicodedata
from html import escape, unescape
from xml.etree.ElementTree import tostring

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from latex2mathml.converter import convert_to_element
from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins.dollarmath import dollarmath_plugin
from sqlalchemy.orm import joinedload

from . import db
from .models import Category, MarkdownFile


writing = Blueprint("writing", __name__)


def render_equation(source, options):
    if len(source) > 2000:
        return escape(source)
    try:
        math = convert_to_element(source, display="block" if options["display_mode"] else "inline")
        # Keep the XML serializer's escaping and omit interactive or styled TeX links.
        for element in math.iter():
            element.attrib.pop("href", None)
            element.attrib.pop("style", None)
            if element.text:
                element.text = unescape(element.text)
        return tostring(math, encoding="unicode")
    except Exception:  # A malformed equation should leave the rest of the article readable.
        return escape(source)


markdown = (
    MarkdownIt("commonmark", {"html": False})
    .enable(["table", "strikethrough"])
    .use(dollarmath_plugin, renderer=render_equation, allow_labels=False, allow_space=False)
)


def render_table_cell(self, tokens, index, options, env):
    attributes = tokens[index].attrs
    alignment = attributes.pop("style", None)
    if alignment in {"text-align:center", "text-align:right"}:
        attributes["class"] = "align-" + alignment.split(":")[1]
    return self.renderToken(tokens, index, options, env)


for cell in ("th_open", "td_open"):
    markdown.add_render_rule(cell, render_table_cell)


def render_markdown(source):
    return Markup(markdown.render(source or ""))


def published_posts():
    return (
        db.select(MarkdownFile)
        .options(joinedload(MarkdownFile.category))
        .where(MarkdownFile.published_at.is_not(None))
        .order_by(MarkdownFile.published_at.desc(), MarkdownFile.id)
    )


def filter_by_topic(topic):
    statement = published_posts()
    if topic:
        statement = statement.join(MarkdownFile.category).where(Category.category == topic)
    return statement


def available_slug(title):
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "post"
    candidate = base
    number = 2
    while db.session.scalar(db.select(MarkdownFile.id).where(MarkdownFile.slug == candidate)):
        candidate = f"{base}-{number}"
        number += 1
    return candidate


@writing.get("/blog")
@writing.get("/writing")
def blog():
    active_topic = request.args.get("topic", "").strip()
    topics = db.session.scalars(
        db.select(Category.category).join(MarkdownFile, MarkdownFile.category_id == Category.id)
        .where(MarkdownFile.published_at.is_not(None), Category.category.is_not(None), Category.category != "")
        .distinct().order_by(Category.category)
    ).all()
    posts = db.session.scalars(filter_by_topic(active_topic)).all()
    return render_template("projects.html", posts=posts, topics=topics, active_topic=active_topic)


@writing.get("/writing/<string:slug>")
def article(slug):
    post = db.first_or_404(published_posts().where(MarkdownFile.slug == slug))
    return render_template("projects-detail.html", post=post, article_html=render_markdown(post.content))


@writing.get("/blog-post/<string:post_id>")
def legacy_article(post_id):
    post = db.first_or_404(published_posts().where(MarkdownFile.id == post_id))
    return redirect(url_for("writing.article", slug=post.slug), code=301)


@writing.get("/filter-posts/<category_name>")
def filter_posts(category_name):
    # Keep the original public response available for existing links and callers.
    topic = "" if category_name.lower() == "all" else category_name
    posts = db.session.scalars(filter_by_topic(topic))
    return jsonify(posts=[
        {
            "id": post.id,
            "name": post.name,
            "image_url": url_for("static", filename="img/project_img.jpg"),
            "content": post.content,
            "category_name": post.category.label.replace(" / ", " - ") if post.category else "",
            "upload_date": post.upload_date.strftime("%d %B, %Y") if post.upload_date else None,
            "modification_date": post.modification_date.strftime("%d %B, %Y") if post.modification_date else None,
            "author_name": post.author_name,
        }
        for post in posts
    ])
