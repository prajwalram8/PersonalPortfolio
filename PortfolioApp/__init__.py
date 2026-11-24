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

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"

    from .admin import admin, create_owner
    from .projects import writing
    from .views import pages

    app.register_blueprint(pages)
    app.register_blueprint(writing)
    app.register_blueprint(admin)
    app.cli.add_command(create_owner)

    @app.after_request
    def protect_private_responses(response):
        if request.blueprint == "admin":
            response.headers["Cache-Control"] = "no-store"
        return response

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
            message="Markdown imports must be 256 KB or smaller.",
        ), 413

    return app


# Keep the app import used by existing entry points and environment setup.
app = create_app()
