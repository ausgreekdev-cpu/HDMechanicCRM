"""Admin user management and admin pages (same `core` blueprint)."""
import logging
from flask import redirect, render_template, request, flash, g
from app.auth import hash_password, login_required, admin_required
from app.helpers import paginate
from app.routes.core import bp


@bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    from app.models import User
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(User).order_by(User.username)
    p = paginate(query, page)
    return render_template("admin/users.html", users=p["rows"], p=p, active_page="admin_users")


@bp.route("/admin/users/new", methods=["POST"])
@login_required
@admin_required
def admin_create_user():
    from app.models import User
    db = g.db
    try:
        u = User(
            username=request.form["username"],
            password_hash=hash_password(request.form["password"]),
            display_name=request.form.get("display_name", ""),
            role=request.form.get("role", "user"),
        )
        db.add(u)
        db.commit()
        flash("User created", "success")
    except Exception:
        logging.exception("Failed to create user")
        flash("Failed to create user. Please try again.", "danger")
    return redirect("/admin/users")


@bp.route("/admin/users/<int:uid>/toggle", methods=["POST"])
@login_required
@admin_required
def admin_toggle_user(uid):
    from app.models import User
    db = g.db
    u = db.query(User).filter(User.id == uid).first()
    if u:
        u.is_active = not u.is_active
        db.commit()
        flash(f"User {'activated' if u.is_active else 'deactivated'}", "success")
    return redirect("/admin/users")


@bp.route("/admin/square-setup")
@login_required
@admin_required
def square_setup():
    from app.payments_square import square_enabled
    return render_template("square_setup.html", square_enabled=square_enabled(), active_page="square_setup")


@bp.route("/admin/analytics")
@login_required
@admin_required
def admin_analytics():
    return render_template("admin/analytics.html", active_page="analytics")
