import argparse
import logging
from PortfolioApp import app, db  
from PortfolioApp.models import User
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate, init as init_migrations, migrate as run_migrations, upgrade as apply_migrations

logging.basicConfig(level=logging.INFO)

migrate = Migrate(app, db)

def init_db():
    """Initialize the database."""
    try:
        with app.app_context():
            db.create_all()
        logging.info("Initialized the database.")
    except Exception as e:
        logging.error(f"Error during initialization: {e}")

def migrate_db(directory='migrations'):
    """Run database migrations."""
    try:
        with app.app_context():
            init_migrations(directory=directory)
            run_migrations(directory=directory, message='Migration commit')
            apply_migrations(directory=directory)
        logging.info("Database migrated.")
    except Exception as e:
        logging.error(f"Error during migration: {e}")

def commit_upgrade_db(directory='migrations'):
    """Run only the latest database migrations."""
    try:
        with app.app_context():
            run_migrations(directory=directory, message='Migration commit')
            apply_migrations(directory=directory)
        logging.info("Database migrated.")
    except Exception as e:
        logging.error(f"Error during migration: {e}")

def create_user(username, password):
    """Create a new user."""
    try:
        with app.app_context():
            hashed_password = generate_password_hash(password, method='scrypt')
            new_user = User(username=username, password=hashed_password)  # Do not specify id
            db.session.add(new_user)
            db.session.commit()
        logging.info(f"User {username} created.")
    except Exception as e:
        logging.error(f"Error during user creation: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage your Flask application.')
    parser.add_argument('--init-db', help='Initialize the database', action='store_true')
    parser.add_argument('--migrate-db', help='Migrate the database', action='store_true')
    parser.add_argument('--commit-upgrade-db', help='Commit and upgrade the latest database changes', action='store_true')
    parser.add_argument('--create-user', help='Create a new user', action='store_true')
    parser.add_argument('--username', help='Username for the new user')
    parser.add_argument('--password', help='Password for the new user')
    parser.add_argument('--run', help='Run the app', action='store_true')

    args = parser.parse_args()


    if args.init_db:
        init_db()
    elif args.migrate_db:
        migrate_db()
    elif args.commit_upgrade_db:
        commit_upgrade_db()
    elif args.create_user:
        if args.username and args.password:
            create_user(args.username, args.password)
        else:
            logging.error("Username and password are required to create a new user.")
    elif args.run:
        app.run(host='0.0.0.0')
    else:
        logging.warning("No operation specified. Use --help for available options.")
