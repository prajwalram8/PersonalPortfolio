from . import app, db
from .models import ContactSubmission, MarkdownFile
from flask import render_template, request, redirect, url_for, flash


# Home page
@app.route('/')
def index():
    return render_template('index.html', active_page='index')

# About Page
@app.route('/about')
def about():
    return render_template('about.html', active_page = 'about')

# Resume Page
@app.route('/resume')
def resume():
    return render_template('resume.html', active_page = 'resume')

@app.route('/projects')
def projects():
    posts = MarkdownFile.query.all()  # Fetching posts from the database
    data = [{'id': post.id, 'name': post.name, 'category_id': post.category_id, 'content': post.content, 
             'upload_date': post.upload_date, 'modification_date': post.modification_date, 
             'author_name': post.author_name} for post in posts]
    return render_template('projects.html', active_page = 'projects', posts=data)

@app.route('/projects-detail/<int:id>', methods=['GET'])
def projects_detail(id):
    posts = MarkdownFile.query.get_or_404(id)
    markdown_content = posts.content
    return render_template('projects-detail.html', md_content = markdown_content)


# ##################################################################################
# Contact
# ##################################################################################

@app.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html', active_page = 'contact')

# Submit Contact
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    submission = ContactSubmission(name=name, email=email, subject=subject, message=message)
    db.session.add(submission)
    db.session.commit()

    flash("Your message has been sent. Thank you!")  # Flash a success message
    return redirect(url_for('contact'))
