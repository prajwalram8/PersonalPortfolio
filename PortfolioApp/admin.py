from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from . import app,db
from .models import User,ContactSubmission,Category,MarkdownFile
from html import escape

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def safe_commit():
    """Commits the current transaction or rolls back if any exception occurs."""
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error: {e}")
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/admin')
@login_required
def admin():
    return render_template('admin/admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user:
            print(f"Debug: Database has username {user.username} with password hash {user.password}")
        
        print(f"Debug: Attempting login with username {username} and password {password}")

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin'))
        
        flash('Invalid username or password')
        return redirect(url_for('login'))

    return render_template('admin/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# -------------------------------------------------
# Handling Users
# -------------------------------------------------
@app.route('/get_users', methods=['GET'])
def get_users():
    users = User.query.all()
    data = [{'id': user.id, 'username': user.username} for user in users]
    return jsonify(data)

@app.route('/delete_user/<string:id>', methods=['POST'])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500


# -------------------------------------------------
# Handling Submissions
# -------------------------------------------------
@app.route('/get_submissions', methods=['GET'])
def get_submissions():
    # Fetch all submissions from the database
    submissions = ContactSubmission.query.all()
    
    # Convert submissions to a format suitable for Bootstrap Table
    data = []
    for submission in submissions:
        data.append({
            'id': submission.id,
            'name': escape(submission.name),
            'email': escape(submission.email),
            'subject': escape(submission.subject),
            'message': escape(submission.message)
        })
    
    # Return data in the expected format
    return jsonify(data)

@app.route('/delete_submission/<int:id>', methods=['POST'])
def delete_submission(id):
    submission = ContactSubmission.query.get_or_404(id)
    db.session.delete(submission)
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500

@app.route('/update_submission/<int:id>', methods=['POST'])
def update_submission(id):
    submission = ContactSubmission.query.get_or_404(id)
    submission.name = request.form.get('name')
    submission.email = request.form.get('email')
    submission.subject = request.form.get('subject')
    submission.message = request.form.get('message')
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500


# -------------------------------------------------
# Handling categories
# -------------------------------------------------
@app.route('/get_categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    data = [{'id': category.id, 'category': category.category, 'subcategory': category.subcategory} for category in categories]
    return jsonify({'total': len(data), 'rows': data})

@app.route('/create_category', methods=['POST'])
def create_category():
    category = request.form.get('category')
    subcategory = request.form.get('subcategory')
    new_category = Category(category=category, subcategory=subcategory)
    db.session.add(new_category)
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500

@app.route('/update_category/<string:id>', methods=['POST'])
def update_category(id):
    category = Category.query.get_or_404(id)
    category.category = request.form.get('category')
    category.subcategory = request.form.get('subcategory')
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500

@app.route('/delete_category/<string:id>', methods=['POST'])
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    if safe_commit():
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 500



if __name__ == '__main__':
    app.run(debug=True)
