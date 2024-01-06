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
