"""Alerts and service reminders (same `core` blueprint)."""
import logging
from flask import redirect, render_template, request, flash, g
from app.auth import login_required
from app.helpers import paginate
from app.routes.core import bp


# ---- Alerts ----
@bp.route("/alerts")
@login_required
def list_alerts():
    from app.models import Alert
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(Alert).order_by(Alert.created_at.desc())
    p = paginate(query, page)
    unread = db.query(Alert).filter(Alert.is_read == False).count()
    return render_template("alerts.html", alerts=p["rows"], p=p, unread=unread, active_page="alerts")


@bp.route("/alerts/<int:alert_id>/read", methods=["POST"])
@login_required
def mark_alert_read(alert_id):
    from app.models import Alert
    db = g.db
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if a:
        a.is_read = True
        db.commit()
    return redirect("/alerts")


# ---- Service Reminders ----
@bp.route("/service-reminders")
@login_required
def list_service_reminders():
    from app.models import ServiceReminder, Vehicle
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(ServiceReminder).order_by(ServiceReminder.vehicle_id)
    p = paginate(query, page)
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("service_reminders.html", reminders=p["rows"], p=p,
                           vehicles=vehicles, active_page="service_reminders")


@bp.route("/service-reminders/new", methods=["POST"])
@login_required
def create_service_reminder():
    from app.models import ServiceReminder
    from datetime import date as dt_date
    db = g.db
    try:
        r = ServiceReminder(
            vehicle_id=int(request.form["vehicle_id"]),
            service_type=request.form["service_type"],
            interval_miles=int(request.form.get("interval_miles", 0)) or None,
            interval_days=int(request.form.get("interval_days", 0)) or None,
            last_odometer=int(request.form.get("last_odometer", 0)) or None,
            last_service_date=request.form.get("last_service_date") or None,
            next_due_miles=int(request.form.get("next_due_miles", 0)) or None,
            next_due_date=request.form.get("next_due_date") or None,
            notes=request.form.get("notes", ""),
        )
        if r.last_service_date:
            r.last_service_date = dt_date.fromisoformat(r.last_service_date)
        if r.next_due_date:
            r.next_due_date = dt_date.fromisoformat(r.next_due_date)
        db.add(r)
        db.commit()
        flash("Service reminder created", "success")
        return redirect("/service-reminders")
    except Exception:
        db.rollback()
        logging.exception("Error creating service reminder")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/service-reminders")


@bp.route("/service-reminders/<int:rid>/delete", methods=["POST"])
@login_required
def delete_service_reminder(rid):
    from app.models import ServiceReminder
    db = g.db
    r = db.query(ServiceReminder).filter(ServiceReminder.id == rid).first()
    if r:
        db.delete(r)
        db.commit()
        flash("Reminder deleted", "success")
    return redirect("/service-reminders")
