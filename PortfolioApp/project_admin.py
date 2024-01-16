from flask import render_template, request, redirect, url_for, flash, jsonify
from . import app,db
from .models import MarkdownFile, Category
from .admin import login_required
from datetime import datetime, timezone
import html

@app.route('/admin/projects-admin')
@login_required
def projects_admin():
    return render_template('admin/projects-admin.html')

@app.route('/get_form_categories')
def get_form_categories():
    categories = Category.query.all()
    result = [{"id": c.id, "category": c.category, "subcategory": c.subcategory} for c in categories]
    return jsonify({"categories": result})

# -------------------------------------------------
# Handling Posts
# -------------------------------------------------
@app.route('/get_posts', methods=['GET'])
def get_posts():
    posts = MarkdownFile.query.all()
    data = [{'id': post.id, 'name': post.name, 'category_id': post.category_id, 'content': post.content, 'upload_date': post.upload_date, 'modification_date': post.modification_date, 'author_name': post.author_name} for post in posts]
    return jsonify({'total': len(data), 'rows': data})

@app.route('/create_markdown_file', methods=['POST'])
def create_markdown_file():
    try:
        # Extract data from the request
        name = request.form['name']
        category_id = request.form['category_id']
        content = request.form['content']
        author_name = request.form['author_name']

        # Preprocess content if necessary (for this example, I'm assuming no preprocessing is done)
        # processed_content = preprocess_content(content)  # Define this function if you need preprocessing

        # Create a new MarkdownFile object
        markdown_file = MarkdownFile(
            name=name,
            category_id=category_id,
            content=content,
            upload_date=datetime.now(timezone.utc),  # Setting the current date and time
            modification_date=datetime.now(timezone.utc),  # Setting the current date and time
            author_name=author_name
        )

        # Add to the database and commit
        db.session.add(markdown_file)
        db.session.commit()

        return jsonify(status='success', message='Markdown file added successfully'), 200

    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

@app.route('/update_markdown_file/<string:id>', methods=['POST'])
def update_markdown_file(id):
    markdownFile = MarkdownFile.query.get_or_404(id)
    try:
        # Extract data from the request
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        content = request.form.get('content')
        author_name = request.form.get('author_name')

        # Update a new MarkdownFile object
        markdownFile.name = name
        markdownFile.category_id = category_id
        markdownFile.content = content
        markdownFile.author_name = author_name
        markdownFile.modification_date = datetime.now(timezone.utc)  # Setting the current date and time

        # Add to the database and commit
        db.session.commit()

        return jsonify(status='success', message='Markdown file updated successfully'), 200

    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


@app.route('/delete_markdown_file/<string:id>', methods=['POST'])
def delete_markdown_file(id):
    markdownFile = MarkdownFile.query.get_or_404(id)
    db.session.delete(markdownFile)
    db.session.commit()
    return jsonify({'status': 'success'}), 200
