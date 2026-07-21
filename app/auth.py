from functools import wraps
from flask import session, flash, redirect
from werkzeug.security import generate_password_hash, check_password_hash

ROLE_HIERARCHY = {"view-only": 0, "tech": 1, "manager": 2, "admin": 3}


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, stored_hash):
    return check_password_hash(stored_hash, password)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def role_required(min_role="manager"):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first", "warning")
                return redirect("/login")
            user_role = session.get("role", "view-only")
            if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY.get(min_role, 2):
                flash(f"{min_role.capitalize()} access required", "danger")
                return redirect("/dashboard")
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first", "warning")
            return redirect("/login")
        if session.get("role") != "admin":
            flash("Admin access required", "danger")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated
