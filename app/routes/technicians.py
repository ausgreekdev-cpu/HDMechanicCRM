from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from app.models import Technician
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("technicians", __name__, url_prefix="/technicians")


@bp.route("", methods=["GET"])
@login_required
def list_technicians():
    db = g.db
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(db.query(Technician).order_by(Technician.name), page, per_page)
    return render_template("technicians/list.html", p=p,
                           active_page="technicians", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_technician_form():
    return render_template("technicians/form.html", technician=None, active_page="technicians")


@bp.route("/new", methods=["POST"])
@login_required
def create_technician():
    db = g.db
    try:
        t = Technician(name=request.form["name"], phone=request.form.get("phone", ""),
                       email=request.form.get("email", ""),
                       specialization=request.form.get("specialization", ""),
                       hourly_rate=float(request.form.get("hourly_rate", 0)))
        db.add(t)
        db.commit()
        flash("Technician added", "success")
        return redirect("/technicians")
    except Exception as e:
        db.rollback()
        logging.exception("Error in technicians")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/technicians/new")


@bp.route("/<int:tech_id>/edit", methods=["GET"])
@login_required
def edit_technician_form(tech_id):
    db = g.db
    t = db.query(Technician).filter(Technician.id == tech_id).first()
    if not t:
        return redirect("/technicians")
    return render_template("technicians/form.html", technician=t, active_page="technicians")


@bp.route("/<int:tech_id>/edit", methods=["POST"])
@login_required
def update_technician(tech_id):
    db = g.db
    try:
        t = db.query(Technician).filter(Technician.id == tech_id).first()
        if t:
            t.name = request.form["name"]
            t.phone = request.form.get("phone", "")
            t.email = request.form.get("email", "")
            t.specialization = request.form.get("specialization", "")
            t.hourly_rate = float(request.form.get("hourly_rate", 0))
            t.is_active = request.form.get("is_active") == "on"
            db.commit()
            flash("Technician updated", "success")
        return redirect("/technicians")
    except Exception as e:
        db.rollback()
        logging.exception("Error in technicians")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/technicians/{tech_id}/edit")


@bp.route("/<int:tech_id>/delete", methods=["POST"])
@login_required
def delete_technician(tech_id):
    db = g.db
    try:
        t = db.query(Technician).filter(Technician.id == tech_id).first()
        if t:
            db.delete(t)
            db.commit()
            flash("Technician deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete technician failed")
        flash("Cannot delete: technician is linked to existing records", "danger")
    return redirect("/technicians")
