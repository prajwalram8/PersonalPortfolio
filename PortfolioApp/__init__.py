from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import load_config


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if config_overrides:
        app.config.update(config_overrides)

    from .security import configure_security

    configure_security(app)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"

    from .admin import admin, create_owner
    from . import studio  # Registers the profile and résumé routes on the admin blueprint.
    from .database import backup_db, restore_db
    from .projects import writing
    from .views import pages

    app.register_blueprint(pages)
    app.register_blueprint(writing)
    app.register_blueprint(admin)
    app.cli.add_command(create_owner)

    app.cli.add_command(backup_db)
    app.cli.add_command(restore_db)

    @app.errorhandler(CSRFError)
    def invalid_form(error):
        return render_template(
            "error.html", title="This form has expired",
            message="Return to the page and try submitting it again.",
        ), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "error.html", title="Page not found", message="The link may have moved.",
        ), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template(
            "error.html", title="This submission is too large",
            message=("Choose a PDF of 4 MB or smaller." if request.endpoint == "admin.resume_pdf"
                     else "This form exceeds the request size limit."),
        ), 413

    return app


# Keep the app import used by existing entry points and environment setup.
app = create_app()
