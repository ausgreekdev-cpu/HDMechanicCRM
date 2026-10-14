"""Surveys, loyalty, appointments (same `crm_advanced` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import datetime
from app.models import CustomerSurvey, CustomerLoyaltyTier, Appointment
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from sqlalchemy import func
from app.routes.crm_advanced import bp


# ---- Customer Surveys (NPS) ----
@bp.route("/surveys")
@login_required
def list_surveys():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(CustomerSurvey).order_by(CustomerSurvey.created_at.desc()), page)
    avg_nps = db.query(func.avg(CustomerSurvey.nps_score)).scalar() or 0
    avg_rating = db.query(func.avg(CustomerSurvey.rating)).scalar() or 0
    return render_template("crm_advanced/surveys.html", p=pagination,
                           avg_nps=round(avg_nps, 1), avg_rating=round(avg_rating, 1),
                           active_page="surveys")


@bp.route("/surveys/new", methods=["POST"])
@login_required
def create_survey():
    db = g.db
    try:
        s = CustomerSurvey(work_order_id=int(request.form.get("work_order_id", 0)) or None,
                           customer_id=int(request.form["customer_id"]),
                           rating=int(request.form.get("rating", 5)),
                           nps_score=int(request.form.get("nps_score", 0)) or None,
                           feedback=request.form.get("feedback", ""),
                           category=request.form.get("category", ""))
        db.add(s); db.commit()
        flash("Survey recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/surveys")
# ---- Customer Loyalty ----
@bp.route("/loyalty")
@login_required
def list_loyalty():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(CustomerLoyaltyTier).order_by(CustomerLoyaltyTier.customer_id), page)
    return render_template("crm_advanced/loyalty.html", p=pagination, active_page="loyalty")


@bp.route("/loyalty/new", methods=["POST"])
@login_required
def create_loyalty():
    db = g.db
    try:
        t = CustomerLoyaltyTier(customer_id=int(request.form["customer_id"]),
                                tier=request.form.get("tier", "Standard"),
                                points=int(request.form.get("points", 0)),
                                discount_pct=float(request.form.get("discount_pct", 0)),
                                notes=request.form.get("notes", ""))
        db.add(t); db.commit()
        flash("Loyalty tier assigned", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/loyalty")
# ---- Appointments (Self-Scheduling Portal) ----
@bp.route("/appointments")
@login_required
def list_appointments():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(Appointment).order_by(Appointment.appointment_date.desc()), page)
    return render_template("crm_advanced/appointments.html", p=pagination, active_page="appointments")


@bp.route("/appointments/new", methods=["POST"])
@login_required
def create_appointment():
    db = g.db
    try:
        a = Appointment(customer_id=int(request.form["customer_id"]),
                        vehicle_id=int(request.form.get("vehicle_id", 0)) or None,
                        title=request.form["title"], description=request.form.get("description", ""),
                        appointment_date=datetime.fromisoformat(request.form["appointment_date"]),
                        duration_minutes=int(request.form.get("duration_minutes", 60)),
                        notes=request.form.get("notes", ""))
        db.add(a); db.commit()
        log_audit("create", "appointment", a.id, f"Appointment: {a.title}")
        flash("Appointment scheduled", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/appointments")


@bp.route("/appointments/<int:aid>/status", methods=["POST"])
@login_required
def update_appointment_status(aid):
    db = g.db
    a = db.query(Appointment).filter(Appointment.id == aid).first()
    if a: a.status = request.form.get("status", "Scheduled"); db.commit()
    return redirect("/crm/appointments")
