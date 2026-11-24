import os
from pathlib import Path
from secrets import token_hex


def load_config():
    production = os.environ.get("PORTFOLIO_ENV") == "production"
    secret = os.environ.get("PORTFOLIO_SECRET_KEY")
    if production and (not secret or len(secret) < 32):
        raise RuntimeError("Set PORTFOLIO_SECRET_KEY to a random secret of at least 32 characters.")

    database = Path(os.environ.get("PORTFOLIO_DATABASE", Path(__file__).with_name("sqlite3.db")))
    return {
        "SECRET_KEY": secret or token_hex(32),
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.resolve()}",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": production,
        "MAX_CONTENT_LENGTH": 768 * 1024,
        "MAX_FORM_MEMORY_SIZE": 768 * 1024,
        "PREVIEW_MODE": False,
    }
