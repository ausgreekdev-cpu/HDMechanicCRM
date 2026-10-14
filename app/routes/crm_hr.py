"""Time clock, labor standards, certifications (same `crm_advanced` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date
from app.timeutils import utcnow
from app.models import TimeEntry, LaborStandard, TechnicianCertification
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.crm_advanced import bp


# ---- Time Clock ----
@bp.route("/time-entries")
@login_required
def list_time_entries():
    db = g.db
    active = db.query(TimeEntry).filter(TimeEntry.clock_out == None).order_by(TimeEntry.clock_in.desc()).all()
    page = int(request.args.get("page", 1))
    p = paginate(db.query(TimeEntry).filter(TimeEntry.clock_out != None).order_by(TimeEntry.clock_in.desc()), page, 50)
    return render_template("crm_advanced/time_entries.html", active=active, p=p, active_page="time_entries")


@bp.route("/time-entries/clock-in", methods=["POST"])
@login_required
def clock_in():
    db = g.db
    try:
        te = TimeEntry(work_order_id=int(request.form.get("work_order_id", 0)) or None,
                       technician_id=int(request.form["technician_id"]),
                       clock_in=utcnow(), notes=request.form.get("notes", ""))
        db.add(te); db.commit()
        log_audit("clock_in", "time_entry", te.id, f"Tech #{te.technician_id} clocked in")
        flash("Clocked in", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/time-entries")


@bp.route("/time-entries/<int:tid>/clock-out", methods=["POST"])
@login_required
def clock_out(tid):
    db = g.db
    te = db.query(TimeEntry).filter(TimeEntry.id == tid).first()
    if te:
        te.clock_out = utcnow()
        delta = te.clock_out - te.clock_in
        te.total_hours = round(delta.total_seconds() / 3600, 2)
        db.commit()
        log_audit("clock_out", "time_entry", tid, f"Clocked out after {te.total_hours}h")
        flash(f"Clocked out ({te.total_hours}h)", "success")
    return redirect("/crm/time-entries")
# ---- Labor Standards ----
@bp.route("/labor-standards")
@login_required
def list_labor_standards():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(LaborStandard).order_by(LaborStandard.category, LaborStandard.name), page)
    return render_template("crm_advanced/labor_standards.html", p=pagination, active_page="labor_standards")


@bp.route("/labor-standards/new", methods=["POST"])
@login_required
def create_labor_standard():
    db = g.db
    try:
        ls = LaborStandard(name=request.form["name"], category=request.form.get("category", ""),
                           description=request.form.get("description", ""),
                           standard_hours=float(request.form["standard_hours"]),
                           notes=request.form.get("notes", ""))
        db.add(ls); db.commit()
        flash("Labor standard created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/labor-standards")
# ---- Technician Certifications ----
@bp.route("/certifications")
@login_required
def list_certifications():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(TechnicianCertification).order_by(TechnicianCertification.technician_id), page)
    return render_template("crm_advanced/certifications.html", p=pagination, active_page="certifications")


@bp.route("/certifications/new", methods=["POST"])
@login_required
def create_certification():
    db = g.db
    try:
        c = TechnicianCertification(technician_id=int(request.form["technician_id"]),
                                    name=request.form["name"], issuer=request.form.get("issuer", ""),
                                    cert_number=request.form.get("cert_number", ""),
                                    issued_date=date.fromisoformat(request.form["issued_date"]) if request.form.get("issued_date") else None,
                                    expiry_date=date.fromisoformat(request.form["expiry_date"]) if request.form.get("expiry_date") else None,
                                    notes=request.form.get("notes", ""))
        db.add(c); db.commit()
        flash("Certification recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/certifications")
