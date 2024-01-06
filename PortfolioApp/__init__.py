import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_object('config')

# Extensions
db = SQLAlchemy(app)

# Handling Markdown files
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'markdown_uploads')
ALLOWED_EXTENSIONS = {'md'}

# App Configurations
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from PortfolioApp import views
from PortfolioApp import admin
from PortfolioApp import project_admin
from PortfolioApp import projects