from functools import wraps
from flask import session, flash, redirect, g
from werkzeug.security import generate_password_hash, check_password_hash

ROLE_HIERARCHY = {"view-only": 0, "tech": 1, "manager": 2, "admin": 3}


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, stored_hash):
    return check_password_hash(stored_hash, password)


def _get_current_user():
    if "user_id" not in session:
        return None
    from app.models import User
    return g.db.query(User).filter(
        User.id == session["user_id"],
        User.is_active == True
    ).first()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user:
            session.clear()
            flash("Please log in first", "warning")
            return redirect("/login")
        session["role"] = user.role
        return f(*args, **kwargs)
    return decorated


def role_required(min_role="manager"):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = _get_current_user()
            if not user:
                session.clear()
                flash("Please log in first", "warning")
                return redirect("/login")
            if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY.get(min_role, 2):
                flash(f"{min_role.capitalize()} access required", "danger")
                return redirect("/dashboard")
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user:
            session.clear()
            flash("Please log in first", "warning")
            return redirect("/login")
        if user.role != "admin":
            flash("Admin access required", "danger")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated
