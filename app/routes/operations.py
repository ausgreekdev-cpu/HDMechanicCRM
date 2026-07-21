from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import date, datetime
from app.models import Lead, Schedule, WorkOrder, Technician, Customer, Communication
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("operations", __name__, url_prefix="/operations")


@bp.route("/leads", methods=["GET"])
@login_required
def list_leads():
    db = g.db
    status = request.args.get("status", "")
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    if search:
        q = q.filter(Lead.name.ilike(f"%{search}%") | Lead.company.ilike(f"%{search}%") |
                     Lead.phone.ilike(f"%{search}%") | Lead.interest.ilike(f"%{search}%"))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(Lead.created_at.desc()), page, per_page)
    return render_template("operations/leads.html", p=p,
                           status=status, search=search, active_page="leads", extra=extra)


@bp.route("/leads/new", methods=["GET"])
@login_required
def new_lead_form():
    return render_template("operations/lead_form.html", lead=None, active_page="leads")


@bp.route("/leads/new", methods=["POST"])
@login_required
def create_lead():
    db = g.db
    try:
        l = Lead(name=request.form["name"], company=request.form.get("company", ""),
                 phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                 source=request.form.get("source", ""), interest=request.form.get("interest", ""),
                 notes=request.form.get("notes", ""))
        db.add(l)
        db.commit()
        flash("Lead created", "success")
        return redirect("/operations/leads")
    except Exception as e:
        db.rollback()
        logging.exception("Error in operations")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/operations/leads/new")


@bp.route("/leads/<int:lead_id>/edit", methods=["GET"])
@login_required
def edit_lead_form(lead_id):
    db = g.db
    l = db.query(Lead).filter(Lead.id == lead_id).first()
    if not l:
        return redirect("/operations/leads")
    return render_template("operations/lead_form.html", lead=l, active_page="leads")


@bp.route("/leads/<int:lead_id>/edit", methods=["POST"])
@login_required
def update_lead(lead_id):
    db = g.db
    try:
        l = db.query(Lead).filter(Lead.id == lead_id).first()
        if l:
            l.name = request.form["name"]
            l.company = request.form.get("company", "")
            l.phone = request.form.get("phone", "")
            l.email = request.form.get("email", "")
            l.source = request.form.get("source", "")
            l.status = request.form.get("status", "New")
            l.interest = request.form.get("interest", "")
            l.notes = request.form.get("notes", "")
            db.commit()
            flash("Lead updated", "success")
        return redirect("/operations/leads")
    except Exception as e:
        db.rollback()
        logging.exception("Error in operations")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/operations/leads/{lead_id}/edit")


@bp.route("/leads/<int:lead_id>/delete", methods=["POST"])
@login_required
def delete_lead(lead_id):
    db = g.db
    try:
        l = db.query(Lead).filter(Lead.id == lead_id).first()
        if l:
            db.delete(l)
            db.commit()
            flash("Lead deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete lead failed")
        flash("Cannot delete: lead is linked to existing records", "danger")
    return redirect("/operations/leads")


@bp.route("/leads/<int:lead_id>/convert", methods=["POST"])
@login_required
def convert_lead(lead_id):
    db = g.db
    try:
        l = db.query(Lead).filter(Lead.id == lead_id).first()
        if l:
            c = Customer(name=l.name, company=l.company or "", phone=l.phone or "",
                         email=l.email or "", notes=f"Converted from lead. {l.notes or ''}")
            db.add(c)
            db.flush()
            db.add(Communication(customer_id=c.id, comm_type="Lead Conversion",
                                 subject="Lead converted to customer",
                                 body=f"Converted from {l.source or 'unknown source'}. Interest: {l.interest or 'N/A'}",
                                 direction="Inbound"))
            l.status = "Converted"
            db.commit()
            flash(f"Lead converted to customer: {c.name}", "success")
            return redirect(f"/customers/{c.id}")
        flash("Lead not found", "warning")
        return redirect("/operations/leads")
    except Exception:
        db.rollback()
        logging.exception("Error converting lead")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/operations/leads")


@bp.route("/schedule", methods=["GET"])
@login_required
def view_schedule():
    db = g.db
    d = request.args.get("date", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    sched_date = date.fromisoformat(d) if d else datetime.now().date()
    q = db.query(Schedule).filter(Schedule.scheduled_date == sched_date).order_by(Schedule.start_time)
    technicians = db.query(Technician).filter(Technician.is_active == True).all()
    work_orders = db.query(WorkOrder).filter(
        WorkOrder.status.not_in(["Completed", "Invoiced", "Cancelled"])).all()
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q, page, per_page)
    return render_template("operations/schedule.html", p=p, date=sched_date,
                           technicians=technicians, work_orders=work_orders, active_page="schedule", extra=extra)


@bp.route("/schedule/add", methods=["POST"])
@login_required
def add_schedule():
    db = g.db
    try:
        s = Schedule(work_order_id=int(request.form["work_order_id"]),
                     technician_id=int(request.form["technician_id"]),
                     scheduled_date=date.fromisoformat(request.form["scheduled_date"]),
                     start_time=request.form.get("start_time", ""),
                     end_time=request.form.get("end_time", ""), notes=request.form.get("notes", ""))
        db.add(s)
        db.commit()
        flash("Job scheduled", "success")
        return redirect("/operations/schedule")
    except Exception as e:
        db.rollback()
        logging.exception("Error in operations")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/operations/schedule")


@bp.route("/schedule/<int:schedule_id>/delete", methods=["POST"])
@login_required
def delete_schedule(schedule_id):
    db = g.db
    try:
        s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if s:
            db.delete(s)
            db.commit()
            flash("Schedule removed", "info")
    except Exception as e:
        db.rollback()
        logging.exception("Error in operations")
        flash("An error occurred. Please try again.", "danger")
    return redirect("/operations/schedule")
