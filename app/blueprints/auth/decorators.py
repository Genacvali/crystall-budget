"""Authentication decorators."""

from functools import wraps
from flask import session, flash, redirect, url_for


def login_required(f):
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Войдите, чтобы продолжить", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function