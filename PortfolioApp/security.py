from functools import wraps
import hmac
from time import time

from flask import current_app, render_template, request
from sqlalchemy import case
from sqlalchemy.dialects.sqlite import insert
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db


CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self'; img-src 'self' https: data:; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)

MAX_PDF_SIZE = 4 * 1024 * 1024


def configure_security(app):
    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def set_upload_limit():
        if request.endpoint == "admin.resume_pdf" and request.method == "POST":
            request.max_content_length = MAX_PDF_SIZE + 64 * 1024

    @app.after_request
    def set_security_headers(response):
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if app.config["SESSION_COOKIE_SECURE"] and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.blueprint == "admin":
            response.headers["Cache-Control"] = "no-store"
        return response


def rate_limit(scope):
    def decorate(view):
        @wraps(view)
        def limited_view(*args, **kwargs):
            if request.method == "POST":
                retry_after = reserve_request(scope)
                if retry_after:
                    return render_template(
                        "error.html", title="Too many requests",
                        message="Please wait a little before trying again.",
                    ), 429, {"Retry-After": str(retry_after), "Cache-Control": "no-store"}
            return view(*args, **kwargs)
        return limited_view
    return decorate


def reserve_request(scope):
    from .models import RequestLimit

    maximum, window = current_app.config["RATE_LIMITS"][scope]
    address = request.remote_addr or "unknown"
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode()
    client_key = hmac.digest(secret, address.encode(), "sha256").hex()
    now = int(time())
    entry = RequestLimit.__table__
    expired = entry.c.expires_at <= now

    # A single SQLite write reserves a slot across all processes.
    statement = insert(entry).values(scope=scope, client_key=client_key, count=1, expires_at=now + window)
    statement = statement.on_conflict_do_update(
        index_elements=[entry.c.scope, entry.c.client_key],
        set_={
            "count": case((expired, 1), else_=entry.c.count + 1),
            "expires_at": case((expired, now + window), else_=entry.c.expires_at),
        },
        where=expired | (entry.c.count < maximum),
    )
    key = (entry.c.scope == scope, entry.c.client_key == client_key)
    # A separate short transaction releases the lock before auth or contact handling.
    with db.engine.begin() as connection:
        if connection.execute(statement).rowcount:
            connection.execute(entry.delete().where(expired))
            return 0
        expires_at = connection.scalar(db.select(entry.c.expires_at).where(*key))
        return max(1, expires_at - now)
