import os
from pathlib import Path
from secrets import token_hex


def load_config():
    production = os.environ.get("PORTFOLIO_ENV") == "production"
    secret = os.environ.get("PORTFOLIO_SECRET_KEY")
    if production and (not secret or len(secret) < 32):
        raise RuntimeError("Set PORTFOLIO_SECRET_KEY to a random secret of at least 32 characters.")

    hosts = [host.strip() for host in os.environ.get("PORTFOLIO_TRUSTED_HOSTS", "").split(",") if host.strip()]
    if production and not hosts:
        raise RuntimeError("Set PORTFOLIO_TRUSTED_HOSTS to the public hostnames for this site.")

    database = Path(os.environ.get("PORTFOLIO_DATABASE", Path(__file__).with_name("sqlite3.db")))
    return {
        "SECRET_KEY": secret or token_hex(32),
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.resolve()}",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": production,
        "TRUSTED_HOSTS": hosts or None,
        "TRUST_PROXY": os.environ.get("PORTFOLIO_TRUST_PROXY") == "1",
        "RATE_LIMITS": {"login": (10, 15 * 60), "contact": (5, 60 * 60)},
        "MAX_CONTENT_LENGTH": 768 * 1024,
        "MAX_FORM_MEMORY_SIZE": 768 * 1024,
        "PREVIEW_MODE": False,
    }
