"""Compatibility entry point for the Flask migration and development commands."""
import argparse

from flask_migrate import upgrade

from wsgi import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--init-db", action="store_true", help="Apply database migrations")
    command.add_argument("--run", action="store_true", help="Run the local development server")
    args = parser.parse_args()

    if args.init_db:
        with app.app_context():
            upgrade()
    else:
        app.run()
