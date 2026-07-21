import os, csv, io, uuid, shutil, logging
from datetime import datetime, timedelta
from flask import Blueprint, redirect, session, render_template, request, flash, jsonify, send_file, g
from app.auth import hash_password, verify_password, login_required, admin_required
from app.export import export_csv

bp = Blueprint("core", __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@bp.route("/")
def root():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        from app.models import User
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = g.db
        user = db.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash) and user.is_active:
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
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


@bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    from app.models import User
    db = g.db
    users = db.query(User).order_by(User.username).all()
    return render_template("admin/users.html", users=users, active_page="admin_users")


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


# ---- CSV Export ----
@bp.route("/export/customers")
@login_required
def export_customers():
    from app.models import Customer
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    return export_csv(
        ["Name", "Company", "Phone", "Email", "Address", "Vehicles", "Notes"],
        [[c.name, c.company or "", c.phone or "", c.email or "", c.address or "", len(c.vehicles), c.notes or ""] for c in customers],
        "customers.csv"
    )


@bp.route("/export/parts")
@login_required
def export_parts():
    from app.models import Part
    db = g.db
    parts = db.query(Part).order_by(Part.name).all()
    return export_csv(
        ["Name", "Part #", "Category", "Supplier", "Qty", "Min", "Cost", "Sell", "Location"],
        [[p.name, p.part_number or "", p.category or "", p.supplier or "", p.quantity_on_hand, p.min_quantity, p.cost_price, p.selling_price, p.location or ""] for p in parts],
        "parts.csv"
    )


@bp.route("/export/work-orders")
@login_required
def export_work_orders():
    from app.models import WorkOrder
    db = g.db
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    return export_csv(
        ["ID", "Title", "Customer", "Vehicle", "Status", "Labor Hrs", "Parts", "Total", "Created"],
        [[wo.id, wo.title, wo.customer.name if wo.customer else "", f"{wo.vehicle.make} {wo.vehicle.model}" if wo.vehicle else "", wo.status, wo.labor_hours, wo.parts_total, wo.total_amount, wo.created_at.strftime("%Y-%m-%d")] for wo in wos],
        "work_orders.csv"
    )


@bp.route("/export/scrap-pickups")
@login_required
def export_scrap_pickups():
    from app.models import ScrapPickup
    db = g.db
    pickups = db.query(ScrapPickup).order_by(ScrapPickup.pickup_date.desc()).all()
    return export_csv(
        ["Date", "Vendor", "Material", "Weight (kg)", "Price/kg", "Total Payout"],
        [[p.pickup_date, p.vendor.name if p.vendor else "", p.material_type, p.weight_kg, p.price_per_kg, p.total_payout] for p in pickups],
        "scrap_pickups.csv"
    )


@bp.route("/export/invoices")
@login_required
def export_invoices():
    from app.models import Invoice
    db = g.db
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return export_csv(
        ["Invoice #", "Work Order", "Customer", "Subtotal", "Tax", "Total", "Status", "Paid Date"],
        [[inv.invoice_number or "", inv.work_order.title if inv.work_order else "", inv.work_order.customer.name if inv.work_order and inv.work_order.customer else "", inv.subtotal, inv.tax_amount, inv.total_amount, inv.status, inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else ""] for inv in invoices],
        "invoices.csv"
    )


# ---- Reports ----
@bp.route("/reports")
@login_required
def reports():
    from app.models import Customer, WorkOrder, Part, ScrapPickup, Invoice, Lead
    from sqlalchemy import func
    db = g.db
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    revenue = db.query(func.sum(WorkOrder.total_amount)).filter(
        WorkOrder.status.in_(["Completed", "Invoiced"]),
        WorkOrder.updated_at >= month_start
    ).scalar() or 0

    scrap_revenue = db.query(func.sum(ScrapPickup.total_payout)).filter(
        ScrapPickup.created_at >= month_start
    ).scalar() or 0

    wo_by_status = db.query(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status).all()
    parts_low_stock = db.query(Part).filter(Part.quantity_on_hand <= Part.min_quantity).count()
    open_invoices = db.query(Invoice).filter(Invoice.status == "Unpaid").count()
    open_invoices_total = db.query(func.sum(Invoice.total_amount)).filter(Invoice.status == "Unpaid").scalar() or 0
    recent_customers = db.query(Customer).order_by(Customer.created_at.desc()).limit(5).all()

    return render_template("reports.html", revenue=revenue, scrap_revenue=scrap_revenue,
                           wo_by_status=wo_by_status, parts_low_stock=parts_low_stock,
                           open_invoices=open_invoices, open_invoices_total=open_invoices_total,
                           recent_customers=recent_customers, active_page="reports",
                           month=now.strftime("%B %Y"))


# ---- QuickBooks Export ----
@bp.route("/export/quickbooks")
@login_required
def export_quickbooks():
    from app.models import Invoice, WorkOrder
    db = g.db
    invoices = db.query(Invoice).filter(Invoice.status == "Paid").order_by(Invoice.paid_at.desc()).all()
    rows = []
    for inv in invoices:
        cust = inv.work_order.customer if inv.work_order and inv.work_order.customer else None
        rows.append([
            inv.invoice_number or "", inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else "",
            cust.name if cust else "", cust.company or "", cust.address or "",
            cust.email or "", inv.total_amount, inv.subtotal, inv.tax_amount
        ])
    return export_csv(
        ["Invoice #", "Date Paid", "Customer Name", "Company", "Address", "Email",
         "Total Amount", "Subtotal", "Tax"],
        rows, "quickbooks_export.csv"
    )


# ---- Technician Efficiency Report ----
@bp.route("/reports/technician-efficiency")
@login_required
def technician_efficiency():
    from app.models import Technician, WorkOrder, Schedule
    from sqlalchemy import func
    db = g.db
    techs = db.query(Technician).filter(Technician.is_active == True).order_by(Technician.name).all()
    results = []
    for t in techs:
        total_hours = db.query(func.sum(WorkOrder.labor_hours)).join(
            Schedule, Schedule.work_order_id == WorkOrder.id
        ).filter(Schedule.technician_id == t.id, WorkOrder.status == "Completed").scalar() or 0
        wo_count = db.query(WorkOrder).join(
            Schedule, Schedule.work_order_id == WorkOrder.id
        ).filter(Schedule.technician_id == t.id, WorkOrder.status == "Completed").count()
        results.append({"name": t.name, "specialization": t.specialization or "",
                        "hourly_rate": t.hourly_rate, "total_hours": total_hours,
                        "wo_count": wo_count, "earned": total_hours * t.hourly_rate})
    return render_template("reports/tech_efficiency.html", techs=results, active_page="reports")


# ---- Alerts ----
@bp.route("/alerts")
@login_required
def list_alerts():
    from app.models import Alert
    db = g.db
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(50).all()
    unread = db.query(Alert).filter(Alert.is_read == False).count()
    return render_template("alerts.html", alerts=alerts, unread=unread, active_page="alerts")


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
    reminders = db.query(ServiceReminder).order_by(ServiceReminder.vehicle_id).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("service_reminders.html", reminders=reminders,
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


# ---- Chart API ----
@bp.route("/api/chart/revenue")
@login_required
def chart_revenue():
    from app.models import WorkOrder
    from sqlalchemy import func
    db = g.db
    rows = db.query(
        func.strftime("%Y-%m", WorkOrder.updated_at).label("month"),
        func.sum(WorkOrder.total_amount)
    ).filter(WorkOrder.status.in_(["Completed", "Invoiced"])).group_by("month").order_by("month").all()
    return jsonify(labels=[r.month for r in rows], values=[float(r[1] or 0) for r in rows])


@bp.route("/api/chart/wo-status")
@login_required
def chart_wo_status():
    from app.models import WorkOrder
    from sqlalchemy import func
    db = g.db
    rows = db.query(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status).all()
    colors = {"New": "#0dcaf0", "Diagnosing": "#6f42c1", "Waiting Parts": "#fd7e14",
              "In Progress": "#0d6efd", "Completed": "#198754", "Invoiced": "#20c997", "Cancelled": "#dc3545"}
    return jsonify(labels=[r[0] for r in rows], values=[r[1] for r in rows],
                   colors=[colors.get(r[0], "#adb5bd") for r in rows])


@bp.route("/api/chart/scrap")
@login_required
def chart_scrap():
    from app.models import ScrapPickup
    from sqlalchemy import func
    db = g.db
    rows = db.query(
        func.strftime("%Y-%m", ScrapPickup.pickup_date).label("month"),
        func.sum(ScrapPickup.total_payout)
    ).group_by("month").order_by("month").all()
    return jsonify(labels=[r.month for r in rows], values=[float(r[1] or 0) for r in rows])


# ---- Database Backup ----
@bp.route("/backup")
@login_required
@admin_required
def backup_database():
    from app.database import DB_PATH
    from datetime import date
    db = g.db
    backup_path = DB_PATH + f".backup-{date.today().isoformat()}"
    shutil.copy2(DB_PATH, backup_path)
    flash(f"Database backed up to data/", "success")
    return send_file(backup_path, as_attachment=True, download_name=f"crm-backup-{date.today().isoformat()}.db")


# ---- Global Search ----
@bp.route("/search")
@login_required
def global_search():
    from app.models import Customer, Vehicle, WorkOrder, Part
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("search.html", query=q, results={}, active_page=None)
    db = g.db
    like = f"%{q}%"
    customers = db.query(Customer).filter(Customer.name.ilike(like) | Customer.company.ilike(like) | Customer.phone.ilike(like)).limit(10).all()
    vehicles = db.query(Vehicle).filter(Vehicle.make.ilike(like) | Vehicle.model.ilike(like) | Vehicle.vin.ilike(like) | Vehicle.license_plate.ilike(like)).limit(10).all()
    work_orders = db.query(WorkOrder).filter(WorkOrder.title.ilike(like) | WorkOrder.description.ilike(like)).limit(10).all()
    parts = db.query(Part).filter(Part.name.ilike(like) | Part.part_number.ilike(like) | Part.supplier.ilike(like)).limit(10).all()
    return render_template("search.html", query=q,
                           results={"customers": customers, "vehicles": vehicles,
                                    "work_orders": work_orders, "parts": parts},
                           active_page=None)


# ---- Attachments ----
@bp.route("/attachments/<entity_type>/<int:entity_id>", methods=["GET"])
@login_required
def list_attachments(entity_type, entity_id):
    from app.models import Attachment
    db = g.db
    files = db.query(Attachment).filter(
        Attachment.entity_type == entity_type, Attachment.entity_id == entity_id
    ).order_by(Attachment.created_at.desc()).all()
    return jsonify([{"id": f.id, "name": f.original_name, "size": f.file_size,
                    "type": f.content_type, "created": f.created_at.isoformat()}
                   for f in files])


@bp.route("/attachments/<entity_type>/<int:entity_id>/upload", methods=["POST"])
@login_required
def upload_attachment(entity_type, entity_id):
    from app.models import Attachment
    db = g.db
    try:
        f = request.files.get("file")
        if not f or not f.filename:
            flash("No file selected", "warning")
            return redirect(request.referrer or "/")
        ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
        safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        path = os.path.join(UPLOAD_FOLDER, safe_name)
        f.save(path)
        att = Attachment(
            entity_type=entity_type, entity_id=entity_id,
            filename=safe_name, original_name=f.filename,
            file_size=os.path.getsize(path), content_type=f.content_type or "application/octet-stream",
            uploaded_by=session.get("user_id"),
        )
        db.add(att)
        db.commit()
        from app.audit import log_audit
        log_audit("upload", entity_type, entity_id, f"Uploaded {f.filename}")
        flash("File uploaded", "success")
    except Exception as e:
        logging.exception("Upload failed")
        flash("Upload failed", "danger")
    return redirect(request.referrer or "/")


@bp.route("/attachments/download/<int:att_id>")
@login_required
def download_attachment(att_id):
    from app.models import Attachment
    db = g.db
    att = db.query(Attachment).filter(Attachment.id == att_id).first()
    if not att:
        return "Not found", 404
    path = os.path.join(UPLOAD_FOLDER, att.filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, download_name=att.original_name, as_attachment=True)


@bp.route("/attachments/<int:att_id>/delete", methods=["POST"])
@login_required
def delete_attachment(att_id):
    from app.models import Attachment
    db = g.db
    att = db.query(Attachment).filter(Attachment.id == att_id).first()
    if att:
        path = os.path.join(UPLOAD_FOLDER, att.filename)
        if os.path.exists(path):
            os.remove(path)
        db.delete(att)
        db.commit()
        flash("File deleted", "success")
    return redirect(request.referrer or "/")


# ---- Recurring Work Orders ----
@bp.route("/recurring-work-orders")
@login_required
def list_recurring_work_orders():
    from app.models import RecurringWorkOrder, Customer, Vehicle
    db = g.db
    items = db.query(RecurringWorkOrder).order_by(RecurringWorkOrder.next_due_date).all()
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("recurring_wo/list.html", items=items, customers=customers,
                           vehicles=vehicles, active_page="recurring_wo")


@bp.route("/recurring-work-orders/new", methods=["POST"])
@login_required
def create_recurring_wo():
    from app.models import RecurringWorkOrder
    from datetime import date as dt_date
    db = g.db
    try:
        r = RecurringWorkOrder(
            customer_id=int(request.form["customer_id"]),
            vehicle_id=int(request.form["vehicle_id"]),
            title=request.form["title"],
            description=request.form.get("description", ""),
            interval_days=int(request.form.get("interval_days", 30)),
            interval_miles=int(request.form.get("interval_miles", 0)) or None,
            labor_hours=float(request.form.get("labor_hours", 1)),
            labor_rate=float(request.form.get("labor_rate", 150)),
            next_due_date=dt_date.fromisoformat(request.form["next_due_date"]) if request.form.get("next_due_date") else None,
            notes=request.form.get("notes", ""),
        )
        db.add(r)
        db.commit()
        from app.audit import log_audit
        log_audit("create", "recurring_wo", r.id, f"Created recurring WO: {r.title}")
        flash("Recurring work order created", "success")
        return redirect("/recurring-work-orders")
    except Exception:
        db.rollback()
        logging.exception("Error creating recurring WO")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/recurring-work-orders")


@bp.route("/recurring-work-orders/<int:rid>/toggle", methods=["POST"])
@login_required
def toggle_recurring_wo(rid):
    from app.models import RecurringWorkOrder
    db = g.db
    r = db.query(RecurringWorkOrder).filter(RecurringWorkOrder.id == rid).first()
    if r:
        r.is_active = not r.is_active
        db.commit()
        flash(f"Recurring WO {'activated' if r.is_active else 'deactivated'}", "success")
    return redirect("/recurring-work-orders")


@bp.route("/recurring-work-orders/<int:rid>/generate", methods=["POST"])
@login_required
def generate_from_recurring(rid):
    from app.models import RecurringWorkOrder, WorkOrder
    from datetime import date as dt_date
    db = g.db
    try:
        r = db.query(RecurringWorkOrder).filter(RecurringWorkOrder.id == rid).first()
        if r:
            wo = WorkOrder(
                customer_id=r.customer_id, vehicle_id=r.vehicle_id,
                title=r.title, description=r.description,
                labor_hours=r.labor_hours, labor_rate=r.labor_rate,
                status="New",
            )
            db.add(wo)
            db.flush()
            r.last_generated = datetime.utcnow()
            if r.interval_days:
                r.next_due_date = dt_date.today() + timedelta(days=r.interval_days)
            db.commit()
            from app.audit import log_audit
            log_audit("generate", "work_order", wo.id, f"Generated from recurring WO #{rid}")
            flash(f"Work order '{r.title}' created", "success")
        return redirect("/recurring-work-orders")
    except Exception:
        db.rollback()
        logging.exception("Error generating WO")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/recurring-work-orders")


# ---- Audit Log ----
@bp.route("/audit-log")
@login_required
def list_audit_log():
    from app.models import AuditLog
    from app.helpers import paginate
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(AuditLog).order_by(AuditLog.created_at.desc()), page, 100)
    return render_template("audit_log.html", p=p, active_page="audit_log")


# ---- CSV Import ----
@bp.route("/import/<entity>", methods=["POST"])
@login_required
def csv_import(entity):
    from app.models import Customer, Vehicle, Part, Lead, Technician, ScrapVendor
    db = g.db
    try:
        f = request.files.get("file")
        if not f:
            flash("No file selected", "warning")
            return redirect(request.referrer or "/")
        reader = csv.DictReader(io.StringIO(f.read().decode("utf-8")))
        count = 0
        if entity == "customers":
            for row in reader:
                if row.get("name"):
                    db.add(Customer(name=row["name"], company=row.get("company", ""),
                                    phone=row.get("phone", ""), email=row.get("email", ""),
                                    address=row.get("address", ""), notes=row.get("notes", "")))
                    count += 1
        elif entity == "parts":
            for row in reader:
                if row.get("name"):
                    db.add(Part(name=row["name"], part_number=row.get("part_number", ""),
                                category=row.get("category", ""), supplier=row.get("supplier", ""),
                                cost_price=float(row.get("cost_price", 0)),
                                selling_price=float(row.get("selling_price", 0)),
                                quantity_on_hand=int(row.get("quantity_on_hand", 0)),
                                min_quantity=int(row.get("min_quantity", 5)),
                                location=row.get("location", "")))
                    count += 1
        elif entity == "leads":
            for row in reader:
                if row.get("name"):
                    db.add(Lead(name=row["name"], company=row.get("company", ""),
                                phone=row.get("phone", ""), email=row.get("email", ""),
                                source=row.get("source", ""), status=row.get("status", "New"),
                                notes=row.get("notes", "")))
                    count += 1
        elif entity == "technicians":
            for row in reader:
                if row.get("name"):
                    db.add(Technician(name=row["name"], phone=row.get("phone", ""),
                                      email=row.get("email", ""),
                                      specialization=row.get("specialization", ""),
                                      hourly_rate=float(row.get("hourly_rate", 0))))
                    count += 1
        db.commit()
        from app.audit import log_audit
        log_audit("import", entity, None, f"Imported {count} records")
        flash(f"Imported {count} {entity}", "success")
    except Exception:
        db.rollback()
        logging.exception("Import failed")
        flash("Import failed. Check file format.", "danger")
    return redirect(request.referrer or "/")


# ---- QuickBooks Sync (enhanced) ----
@bp.route("/export/quickbooks-import", methods=["POST"])
@login_required
def quickbooks_import():
    from app.models import Invoice, WorkOrder, Customer
    db = g.db
    try:
        f = request.files.get("file")
        if not f:
            flash("No file selected", "warning")
            return redirect(request.referrer or "/")
        reader = csv.DictReader(io.StringIO(f.read().decode("utf-8")))
        count = 0
        for row in reader:
            if row.get("Invoice #") and row.get("Date Paid"):
                inv = db.query(Invoice).filter(Invoice.invoice_number == row["Invoice #"]).first()
                if inv:
                    from datetime import date as dt_date
                    try:
                        paid = dt_date.fromisoformat(row["Date Paid"])
                    except ValueError:
                        paid = None
                    inv.status = "Paid"
                    inv.paid_at = datetime.combine(paid, datetime.min.time()) if paid else datetime.utcnow()
                    count += 1
        db.commit()
        flash(f"Synced {count} invoices from QuickBooks", "success")
    except Exception:
        db.rollback()
        logging.exception("QB import failed")
        flash("QuickBooks import failed", "danger")
    return redirect(request.referrer or "/")


# ---- Parts Usage Forecasting ----
@bp.route("/reports/parts-forecast")
@login_required
def parts_forecast():
    from app.models import WorkOrderItem, Part
    from sqlalchemy import func
    db = g.db
    usage = db.query(
        WorkOrderItem.part_used,
        func.sum(WorkOrderItem.quantity).label("total_qty"),
        func.count(WorkOrderItem.id).label("usage_count")
    ).filter(WorkOrderItem.part_used != None, WorkOrderItem.part_used != ""
            ).group_by(WorkOrderItem.part_used).order_by(func.sum(WorkOrderItem.quantity).desc()).limit(20).all()
    results = []
    for name, qty, cnt in usage:
        part = db.query(Part).filter(Part.name.ilike(f"%{name}%")).first()
        results.append({
            "part_name": name,
            "total_used": qty,
            "times_used": cnt,
            "avg_per_wo": round(qty / cnt, 1) if cnt else 0,
            "current_stock": part.quantity_on_hand if part else 0,
            "min_qty": part.min_quantity if part else 0,
        })
    return render_template("reports/parts_forecast.html", results=results, active_page="reports")


# ---- Customer Portal ----
@bp.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    if request.method == "POST":
        from app.models import Customer
        email = request.form.get("email", "").strip().lower()
        ref = request.form.get("reference", "").strip()
        db = g.db
        customer = db.query(Customer).filter(
            Customer.email.ilike(email), Customer.id.isnot(None)
        ).first()
        if customer and customer.phone == ref:
            session["portal_customer_id"] = customer.id
            session["portal_customer_name"] = customer.name
            flash(f"Welcome, {customer.name}!", "success")
            return redirect("/portal/dashboard")
        flash("Invalid credentials", "danger")
    return render_template("portal/login.html")


@bp.route("/portal/dashboard")
def portal_dashboard():
    if "portal_customer_id" not in session:
        return redirect("/portal/login")
    from app.models import WorkOrder, Invoice, Vehicle, ServiceReminder
    cid = session["portal_customer_id"]
    db = g.db
    wos = db.query(WorkOrder).filter(WorkOrder.customer_id == cid).order_by(WorkOrder.created_at.desc()).limit(10).all()
    invoices = db.query(Invoice).join(WorkOrder).filter(WorkOrder.customer_id == cid).order_by(Invoice.created_at.desc()).limit(10).all()
    vehicles = db.query(Vehicle).filter(Vehicle.customer_id == cid).all()
    reminders = db.query(ServiceReminder).join(Vehicle).filter(Vehicle.customer_id == cid).all()
    return render_template("portal/dashboard.html", wos=wos, invoices=invoices,
                           vehicles=vehicles, reminders=reminders)


@bp.route("/portal/logout")
def portal_logout():
    session.pop("portal_customer_id", None)
    session.pop("portal_customer_name", None)
    return redirect("/portal/login")


# ---- Kanban Board View ----
@bp.route("/kanban")
@login_required
def kanban_board():
    from app.models import WorkOrder, WorkOrderStatus
    db = g.db
    statuses = [s.value for s in WorkOrderStatus]
    lanes = {}
    for s in statuses:
        lanes[s] = db.query(WorkOrder).filter(WorkOrder.status == s).order_by(WorkOrder.created_at.desc()).limit(20).all()
    return render_template("kanban.html", lanes=lanes, active_page="kanban")


@bp.route("/kanban/update", methods=["POST"])
@login_required
def kanban_update():
    from app.models import WorkOrder
    db = g.db
    try:
        wo_id = int(request.form.get("work_order_id", 0))
        new_status = request.form.get("status", "")
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if wo and new_status:
            wo.status = new_status
            if new_status == "Completed" and not wo.completed_at:
                wo.completed_at = datetime.utcnow()
            db.commit()
            return jsonify({"ok": True})
        return jsonify({"ok": False}), 400
    except Exception:
        return jsonify({"ok": False}), 500


# ---- REST API ----
@bp.route("/api/customers", methods=["GET"])
@login_required
def api_customers():
    from app.models import Customer
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    return jsonify([{"id": c.id, "name": c.name, "company": c.company, "phone": c.phone, "email": c.email} for c in customers])


@bp.route("/api/vehicles", methods=["GET"])
@login_required
def api_vehicles():
    from app.models import Vehicle
    db = g.db
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return jsonify([{"id": v.id, "make": v.make, "model": v.model, "year": v.year, "vin": v.vin, "customer_id": v.customer_id} for v in vehicles])


@bp.route("/api/work-orders", methods=["GET"])
@login_required
def api_work_orders():
    from app.models import WorkOrder
    db = g.db
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(50).all()
    return jsonify([{"id": w.id, "title": w.title, "status": w.status, "customer_id": w.customer_id, "vehicle_id": w.vehicle_id} for w in wos])


@bp.route("/api/parts", methods=["GET"])
@login_required
def api_parts():
    from app.models import Part
    db = g.db
    parts = db.query(Part).order_by(Part.name).limit(50).all()
    return jsonify([{"id": p.id, "name": p.name, "part_number": p.part_number, "qty": p.quantity_on_hand, "price": p.selling_price} for p in parts])


@bp.route("/api/work-orders/<int:wo_id>", methods=["GET"])
@login_required
def api_work_order_detail(wo_id):
    from app.models import WorkOrder
    db = g.db
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo: return jsonify({"error": "not found"}), 404
    items = [{"id": i.id, "description": i.description, "qty": i.quantity, "price": i.unit_price} for i in wo.items]
    return jsonify({"id": wo.id, "title": wo.title, "status": wo.status, "customer_id": wo.customer_id, "items": items,
                    "labor_hours": wo.labor_hours, "total": wo.total_amount})


# ---- Mobile Work Order View (Lightweight) ----
@bp.route("/mobile/wo/<int:wo_id>")
@login_required
def mobile_work_order(wo_id):
    from app.models import WorkOrder
    db = g.db
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo: return "Not found", 404
    return render_template("mobile_work_order.html", wo=wo)


# ---- Vehicle Photo Upload ----
@bp.route("/vehicles/<int:vid>/photos", methods=["POST"])
@login_required
def upload_vehicle_photos(vid):
    photos_dir = os.path.join(UPLOAD_FOLDER, "vehicle_photos", str(vid))
    os.makedirs(photos_dir, exist_ok=True)
    files = request.files.getlist("photos")
    count = 0
    for f in files:
        if f and f.filename:
            ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else "jpg"
            safe = f"{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(photos_dir, safe))
            count += 1
    if count:
        flash(f"{count} photo(s) uploaded", "success")
    return redirect(f"/vehicles/{vid}")


# ---- PDF Export (simple HTML-to-PDF print) ----
@bp.route("/export/pdf/<entity>/<int:eid>")
@login_required
def export_pdf(entity, eid):
    from app.models import WorkOrder, Invoice, Customer, Vehicle, Estimate
    db = g.db
    template = None
    ctx = {}
    if entity == "work_order":
        obj = db.query(WorkOrder).filter(WorkOrder.id == eid).first()
        if obj: template, ctx = "pdf/work_order.html", {"wo": obj}
    elif entity == "invoice":
        obj = db.query(Invoice).filter(Invoice.id == eid).first()
        if obj: template, ctx = "pdf/invoice.html", {"inv": obj}
    elif entity == "estimate":
        obj = db.query(Estimate).filter(Estimate.id == eid).first()
        if obj: template, ctx = "pdf/estimate.html", {"est": obj}
    elif entity == "vehicle":
        obj = db.query(Vehicle).filter(Vehicle.id == eid).first()
        if obj: template, ctx = "pdf/vehicle_history.html", {"vehicle": obj}
    if template:
        return render_template(template, **ctx)
    return "Not found", 404


@bp.route("/health")
def health_check():
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
