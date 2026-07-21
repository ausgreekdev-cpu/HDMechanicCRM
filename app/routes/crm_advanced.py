from flask import Blueprint, render_template, request, redirect, flash, jsonify, send_file, g
import logging, json
from datetime import datetime, date, timedelta
from app.models import EmailLog, SMSLog, CustomerSurvey, CustomerLoyaltyTier, Appointment, TimeEntry, Technician, LaborStandard, SavedFilter, User, DashboardWidget, WorkflowRule, TechnicianCertification, ShopSupply, SDSDocument, WorkOrder, Vehicle, CheckInRecord, EnvironmentalRecord, NonStockItem, Customer, FuelRecord, TireRecord, DieselEmissionRecord, DOTInspection, ServiceReminder
from app.auth import login_required, role_required
from app.audit import log_audit
from app.helpers import paginate
from sqlalchemy import func
import io, csv

bp = Blueprint("crm_advanced", __name__, url_prefix="/crm")


# ---- Email Log ----
@bp.route("/email-log")
@login_required
def list_emails():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(EmailLog).order_by(EmailLog.created_at.desc()), page, 50)
    return render_template("crm_advanced/email_log.html", p=p, active_page="email_log")


@bp.route("/email-log/send", methods=["POST"])
@login_required
def send_custom_email():
    from app.notifications import send_email
    db = g.db
    try:
        to = request.form.get("to", "").strip()
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        if to and subject:
            send_email(to, subject, body)
            db.add(EmailLog(recipient=to, subject=subject, body_text=body,
                            customer_id=int(request.form.get("customer_id", 0)) or None,
                            related_type=request.form.get("related_type", ""),
                            related_id=int(request.form.get("related_id", 0)) or None))
            db.commit()
            flash("Email sent", "success")
        return redirect("/crm/email-log")
    except Exception:
        db.rollback(); flash("Error sending email", "danger")
        return redirect("/crm/email-log")


# ---- SMS Log ----
@bp.route("/sms-log")
@login_required
def list_sms():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(SMSLog).order_by(SMSLog.created_at.desc()), page, 50)
    return render_template("crm_advanced/sms_log.html", p=p, active_page="sms_log")


@bp.route("/sms-log/send", methods=["POST"])
@login_required
def send_sms():
    import logging as lg
    db = g.db
    try:
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "")
        if phone and message:
            log_audit("send_sms", "sms", None, f"To {phone}")
            db.add(SMSLog(phone=phone, message=message,
                          customer_id=int(request.form.get("customer_id", 0)) or None,
                          related_type=request.form.get("related_type", ""),
                          related_id=int(request.form.get("related_id", 0)) or None))
            db.commit()
            flash("SMS queued (requires Twilio integration)", "info")
        return redirect("/crm/sms-log")
    except Exception:
        db.rollback(); flash("Error", "danger")
        return redirect("/crm/sms-log")


# ---- Customer Surveys (NPS) ----
@bp.route("/surveys")
@login_required
def list_surveys():
    db = g.db
    surveys = db.query(CustomerSurvey).order_by(CustomerSurvey.created_at.desc()).all()
    avg_nps = db.query(func.avg(CustomerSurvey.nps_score)).scalar() or 0
    avg_rating = db.query(func.avg(CustomerSurvey.rating)).scalar() or 0
    return render_template("crm_advanced/surveys.html", surveys=surveys,
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
    tiers = db.query(CustomerLoyaltyTier).order_by(CustomerLoyaltyTier.customer_id).all()
    return render_template("crm_advanced/loyalty.html", tiers=tiers, active_page="loyalty")


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
    appts = db.query(Appointment).order_by(Appointment.appointment_date.desc()).all()
    return render_template("crm_advanced/appointments.html", appts=appts, active_page="appointments")


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
                       clock_in=datetime.utcnow(), notes=request.form.get("notes", ""))
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
        te.clock_out = datetime.utcnow()
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
    standards = db.query(LaborStandard).order_by(LaborStandard.category, LaborStandard.name).all()
    return render_template("crm_advanced/labor_standards.html", standards=standards, active_page="labor_standards")


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


# ---- Saved Filters ----
@bp.route("/saved-filters")
@login_required
def list_saved_filters():
    db = g.db
    filters = db.query(SavedFilter).filter(SavedFilter.user_id == session.get("user_id")).order_by(SavedFilter.name).all()
    return render_template("crm_advanced/saved_filters.html", filters=filters, active_page="saved_filters")


@bp.route("/saved-filters/new", methods=["POST"])
@login_required
def create_saved_filter():
    db = g.db
    try:
        data = {k: v for k, v in request.form.items() if k not in ("csrf_token", "name", "entity_type")}
        sf = SavedFilter(user_id=session["user_id"], name=request.form["name"],
                         entity_type=request.form["entity_type"],
                         filter_data=json.dumps(data),
                         is_default=request.form.get("is_default") == "on")
        db.add(sf); db.commit()
        flash("Filter saved", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/saved-filters")


# ---- Dashboard Widgets ----
@bp.route("/dashboard-widgets")
@login_required
def list_widgets():
    db = g.db
    widgets = db.query(DashboardWidget).filter(DashboardWidget.user_id == session.get("user_id")).order_by(DashboardWidget.position).all()
    return render_template("crm_advanced/dashboard_widgets.html", widgets=widgets, active_page="dashboard_widgets")


@bp.route("/dashboard-widgets/new", methods=["POST"])
@login_required
def create_widget():
    db = g.db
    try:
        w = DashboardWidget(user_id=session["user_id"], widget_type=request.form["widget_type"],
                            title=request.form.get("title", ""),
                            config=request.form.get("config", "{}"),
                            position=(db.query(func.max(DashboardWidget.position)).filter(
                                DashboardWidget.user_id == session["user_id"]).scalar() or 0) + 1)
        db.add(w); db.commit()
        flash("Widget added to dashboard", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/dashboard-widgets")


@bp.route("/dashboard-widgets/<int:wid>/toggle", methods=["POST"])
@login_required
def toggle_widget(wid):
    db = g.db
    w = db.query(DashboardWidget).filter(DashboardWidget.id == wid).first()
    if w: w.is_visible = not w.is_visible; db.commit()
    return redirect("/crm/dashboard-widgets")


# ---- Workflow Rules ----
@bp.route("/workflow-rules")
@login_required
def list_workflow_rules():
    db = g.db
    rules = db.query(WorkflowRule).order_by(WorkflowRule.name).all()
    return render_template("crm_advanced/workflow_rules.html", rules=rules, active_page="workflow_rules")


@bp.route("/workflow-rules/new", methods=["POST"])
@login_required
def create_workflow_rule():
    db = g.db
    try:
        r = WorkflowRule(name=request.form["name"], trigger_event=request.form["trigger_event"],
                         conditions=request.form.get("conditions", "{}"),
                         actions=request.form.get("actions", "{}"))
        db.add(r); db.commit()
        flash("Workflow rule created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/workflow-rules")


@bp.route("/workflow-rules/<int:rid>/toggle", methods=["POST"])
@login_required
def toggle_workflow_rule(rid):
    db = g.db
    r = db.query(WorkflowRule).filter(WorkflowRule.id == rid).first()
    if r: r.is_active = not r.is_active; db.commit()
    return redirect("/crm/workflow-rules")


# ---- Technician Certifications ----
@bp.route("/certifications")
@login_required
def list_certifications():
    db = g.db
    certs = db.query(TechnicianCertification).order_by(TechnicianCertification.technician_id).all()
    return render_template("crm_advanced/certifications.html", certs=certs, active_page="certifications")


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


# ---- Shop Supplies ----
@bp.route("/shop-supplies")
@login_required
def list_shop_supplies():
    db = g.db
    supplies = db.query(ShopSupply).order_by(ShopSupply.name).all()
    return render_template("crm_advanced/shop_supplies.html", supplies=supplies, active_page="shop_supplies")


@bp.route("/shop-supplies/new", methods=["POST"])
@login_required
def create_shop_supply():
    db = g.db
    try:
        s = ShopSupply(name=request.form["name"], category=request.form.get("category", ""),
                       quantity_on_hand=int(request.form.get("quantity_on_hand", 0)),
                       unit=request.form.get("unit", "Each"),
                       min_quantity=int(request.form.get("min_quantity", 5)),
                       cost_per_unit=float(request.form.get("cost_per_unit", 0)),
                       notes=request.form.get("notes", ""))
        db.add(s); db.commit()
        flash("Shop supply added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/shop-supplies")


# ---- SDS Documents ----
@bp.route("/sds-documents")
@login_required
def list_sds():
    db = g.db
    docs = db.query(SDSDocument).order_by(SDSDocument.uploaded_at.desc()).all()
    return render_template("crm_advanced/sds_documents.html", docs=docs, active_page="sds_documents")


# ---- Check-In Process ----
@bp.route("/check-in/<int:wo_id>")
@login_required
def check_in_form(wo_id):
    db = g.db
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo: return redirect("/work-orders")
    return render_template("crm_advanced/check_in.html", wo=wo, active_page="work_orders")


@bp.route("/check-in/<int:wo_id>/save", methods=["POST"])
@login_required
def save_check_in(wo_id):
    db = g.db
    try:
        ci = CheckInRecord(work_order_id=wo_id,
                           checked_in_by=request.form.get("checked_in_by", ""),
                           customer_name=request.form.get("customer_name", ""),
                           customer_signature=request.form.get("customer_signature", ""),
                           vehicle_condition=request.form.get("vehicle_condition", ""),
                           fuel_level=request.form.get("fuel_level", ""),
                           odometer=int(request.form.get("odometer", 0)) or None,
                           damage_notes=request.form.get("damage_notes", ""),
                           keys_received=request.form.get("keys_received") == "on")
        db.add(ci); db.commit()
        log_audit("check_in", "work_order", wo_id, "Vehicle checked in")
        flash("Vehicle checked in", "success")
        return redirect(f"/work-orders/{wo_id}")
    except Exception:
        db.rollback(); flash("Error", "danger")
        return redirect(f"/work-orders/{wo_id}")


# ---- Environmental Compliance ----
@bp.route("/environmental")
@login_required
def list_environmental():
    db = g.db
    records = db.query(EnvironmentalRecord).order_by(EnvironmentalRecord.date.desc()).all()
    return render_template("crm_advanced/environmental.html", records=records, active_page="environmental")


@bp.route("/environmental/new", methods=["POST"])
@login_required
def create_environmental():
    db = g.db
    try:
        r = EnvironmentalRecord(record_type=request.form["record_type"],
                                date=date.fromisoformat(request.form["date"]),
                                description=request.form.get("description", ""),
                                quantity=float(request.form.get("quantity", 0)),
                                unit=request.form.get("unit", ""),
                                vendor=request.form.get("vendor", ""),
                                disposal_method=request.form.get("disposal_method", ""),
                                cost=float(request.form.get("cost", 0)),
                                notes=request.form.get("notes", ""))
        db.add(r); db.commit()
        flash("Environmental record created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/environmental")


# ---- Sublet Repairs ----
@bp.route("/sublet")
@login_required
def list_sublet():
    db = g.db
    items = db.query(NonStockItem).filter(NonStockItem.supplier != "").order_by(NonStockItem.name).all()
    return render_template("crm_advanced/sublet.html", items=items, active_page="sublet")


# ---- Bulk Operations ----
@bp.route("/bulk/<entity>", methods=["POST"])
@login_required
def bulk_operation(entity):
    from app.models import WorkOrder, Invoice, Customer, Part
    db = g.db
    try:
        ids = request.form.getlist("ids[]")
        action = request.form.get("action", "")
        if not ids: flash("No items selected", "warning"); return redirect(request.referrer or "/")
        count = len(ids)
        if entity == "work_orders" and action == "delete":
            db.query(WorkOrder).filter(WorkOrder.id.in_([int(i) for i in ids])).delete(synchronize_session=False)
        elif entity == "invoices" and action == "delete":
            db.query(Invoice).filter(Invoice.id.in_([int(i) for i in ids])).delete(synchronize_session=False)
        elif entity == "invoices" and action == "mark_paid":
            db.query(Invoice).filter(Invoice.id.in_([int(i) for i in ids])).update(
                {"status": "Paid", "paid_at": datetime.utcnow()}, synchronize_session=False)
        elif entity == "customers" and action == "delete":
            db.query(Customer).filter(Customer.id.in_([int(i) for i in ids])).delete(synchronize_session=False)
        db.commit()
        log_audit("bulk", entity, None, f"Bulk {action}: {count} records")
        flash(f"Bulk {action} completed on {count} {entity}", "success")
    except Exception:
        db.rollback(); logging.exception("Bulk op failed"); flash("Bulk operation failed", "danger")
    return redirect(request.referrer or "/")


# ---- Vehicle History Report (PDF-style HTML) ----
@bp.route("/vehicle-history/<int:vid>")
@login_required
def vehicle_history(vid):
    db = g.db
    vehicle = db.query(Vehicle).filter(Vehicle.id == vid).first()
    if not vehicle: return redirect("/vehicles")
    wos = db.query(WorkOrder).filter(WorkOrder.vehicle_id == vid).order_by(WorkOrder.created_at.desc()).all()
    fuel = db.query(FuelRecord).filter(FuelRecord.vehicle_id == vid).order_by(FuelRecord.fuel_date.desc()).all()
    tires = db.query(TireRecord).filter(TireRecord.vehicle_id == vid).order_by(TireRecord.install_date.desc()).all()
    emissions = db.query(DieselEmissionRecord).filter(DieselEmissionRecord.vehicle_id == vid).order_by(DieselEmissionRecord.service_date.desc()).all()
    dot = db.query(DOTInspection).filter(DOTInspection.vehicle_id == vid).order_by(DOTInspection.inspection_date.desc()).all()
    return render_template("crm_advanced/vehicle_history.html", vehicle=vehicle, wos=wos,
                           fuel=fuel, tires=tires, emissions=emissions, dot=dot, active_page="vehicles")


# ---- Odometer-to-Service Tracking ----
@bp.route("/odometer-service")
@login_required
def odometer_service():
    db = g.db
    reminders = db.query(ServiceReminder).filter(ServiceReminder.is_active == True,
                                                 ServiceReminder.next_due_miles != None).order_by(ServiceReminder.next_due_miles).all()
    return render_template("crm_advanced/odometer_service.html", reminders=reminders, active_page="odometer_service")
