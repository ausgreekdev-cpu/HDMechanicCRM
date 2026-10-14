"""Shop supplies, SDS, check-in, environmental, sublet, bulk ops, vehicle history, odometer (same `crm_advanced` blueprint)."""
from flask import render_template, request, redirect, flash, g
import logging
from datetime import date
from app.timeutils import utcnow
from app.models import ShopSupply, SDSDocument, WorkOrder, Vehicle, CheckInRecord, EnvironmentalRecord, NonStockItem, Customer, FuelRecord, TireRecord, DieselEmissionRecord, DOTInspection, ServiceReminder
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.crm_advanced import bp


# ---- Shop Supplies ----
@bp.route("/shop-supplies")
@login_required
def list_shop_supplies():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(ShopSupply).order_by(ShopSupply.name), page)
    return render_template("crm_advanced/shop_supplies.html", p=pagination, active_page="shop_supplies")


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
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(SDSDocument).order_by(SDSDocument.uploaded_at.desc()), page)
    return render_template("crm_advanced/sds_documents.html", p=pagination, active_page="sds_documents")
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
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(EnvironmentalRecord).order_by(EnvironmentalRecord.date.desc()), page)
    return render_template("crm_advanced/environmental.html", p=pagination, active_page="environmental")


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
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(NonStockItem).filter(NonStockItem.supplier != "").order_by(NonStockItem.name), page)
    return render_template("crm_advanced/sublet.html", p=pagination, active_page="sublet")
# ---- Bulk Operations ----
@bp.route("/bulk/<entity>", methods=["POST"])
@login_required
def bulk_operation(entity):
    from app.models import Invoice
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
                {"status": "Paid", "paid_at": utcnow()}, synchronize_session=False)
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
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(ServiceReminder).filter(ServiceReminder.is_active == True,
                                                  ServiceReminder.next_due_miles != None).order_by(ServiceReminder.next_due_miles), page)
    return render_template("crm_advanced/odometer_service.html", p=pagination, active_page="odometer_service")
