"""System views: backup, search, attachments, recurring work orders, audit log, kanban, REST API, mobile, photos, health (same `core` blueprint)."""
import os
import shutil
import uuid
import logging
from datetime import datetime, timedelta
from flask import redirect, session, render_template, request, flash, jsonify, send_file, g
from app.auth import login_required, admin_required
from app.helpers import paginate
from app.timeutils import utcnow
from app.routes.core import bp

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---- Database Backup ----
@bp.route("/backup")
@login_required
@admin_required
def backup_database():
    from app.database import DB_PATH
    if not DB_PATH:
        flash("Backup is only available when running on SQLite. "
              "Use pg_dump for PostgreSQL databases.", "warning")
        return redirect("/settings")
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S-%f")
    backup_path = DB_PATH + f".backup-{stamp}"
    shutil.copy2(DB_PATH, backup_path)
    filename = os.path.basename(backup_path)
    flash(f"Database backed up to {filename}", "success")
    return send_file(backup_path, as_attachment=True, download_name=f"crm-backup-{stamp}.db")
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
    page = int(request.args.get("page", 1))
    query = db.query(RecurringWorkOrder).order_by(RecurringWorkOrder.next_due_date)
    p = paginate(query, page)
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("recurring_wo/list.html", items=p["rows"], p=p, customers=customers,
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
            r.last_generated = utcnow()
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
                wo.completed_at = utcnow()
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
@bp.route("/data-deletion")
def data_deletion():
    return render_template("data-deletion.html")
