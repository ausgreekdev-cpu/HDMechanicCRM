"""Core authentication and session views (same `core` blueprint)."""
import os
from flask import redirect, session, render_template, request, flash, g
from app.auth import hash_password, verify_password, login_required
from app import limiter
from app.routes.core import bp


@bp.route("/")
def root():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        from app.models import User
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = g.db
        user = db.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash) and user.is_active:
            user_data = {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
            }
            session.clear()
            session.update(user_data)
            flash(f"Welcome back, {user.display_name or user.username}!", "success")
            return redirect("/dashboard")
        flash("Invalid username or password", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect("/login")


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    from app.models import User
    db = g.db
    user = db.query(User).filter(User.id == session["user_id"]).first()
    if request.method == "POST":
        if request.form.get("display_name"):
            user.display_name = request.form["display_name"]
        if request.form.get("new_password"):
            current = request.form.get("current_password", "")
            if verify_password(current, user.password_hash):
                user.password_hash = hash_password(request.form["new_password"])
                flash("Password updated", "success")
            else:
                flash("Current password is incorrect", "danger")
        db.commit()
    return render_template("settings.html", user=user, env=os.environ)
