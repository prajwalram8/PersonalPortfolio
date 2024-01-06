from . import app, db
from .models import ContactSubmission, MarkdownFile, Category
from flask import render_template, request, redirect, url_for, flash, jsonify


@app.route('/projects')
def projects():
    categories = Category.query.all()  # Fetching all categories for the filter
    posts = MarkdownFile.query.all()  # Fetching all posts from the database
    return render_template('projects.html', active_page='projects', posts=posts, categories=categories)

@app.route('/filter-posts/<category_name>')
def filter_posts(category_name):
    if category_name.lower() == 'all':  # If 'all' is selected, return all posts
        filtered_posts = MarkdownFile.query.all()
    else:
        # Find the category with the given name
        category = Category.query.filter_by(category=category_name).first()
        if category:
            # Get all MarkdownFile entries that belong to this category
            filtered_posts = MarkdownFile.query.filter_by(category_id=category.id).all()
        else:
            # If the category doesn't exist or no category selected, return an empty list
            filtered_posts = []
    
    # Convert the posts to a JSON-serializable format
    posts_json = [
        {
            'id': post.id,
            'name': post.name,
            'image_url': url_for('static', filename='img/project_img.jpg'),  # Assuming a default image
            'content': post.content,
            'upload_date': post.upload_date.isoformat() if post.upload_date else None,
            'modification_date': post.modification_date.isoformat() if post.modification_date else None,
            'author_name': post.author_name
        }
        for post in filtered_posts
    ]

    return jsonify(posts=posts_json)


@app.route('/projects-detail/<int:id>', methods=['GET'])
def projects_detail(id):
    posts = MarkdownFile.query.get_or_404(id)
    markdown_content = posts.content
    return render_template('projects-detail.html', md_content = markdown_content)


