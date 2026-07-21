from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import datetime
from app.models import WorkOrder, WorkOrderItem, Customer, Vehicle, WorkOrderStatus, Part, PartTransaction
from app.auth import login_required
from app.helpers import paginate
from app.audit import log_audit
import urllib.parse

bp = Blueprint("work_orders", __name__, url_prefix="/work-orders")


@bp.route("", methods=["GET"])
@login_required
def list_work_orders():
    db = g.db
    status = request.args.get("status", "")
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if search:
        query = query.join(Customer).filter(
            WorkOrder.title.ilike(f"%{search}%") | Customer.name.ilike(f"%{search}%") |
            WorkOrder.description.ilike(f"%{search}%")
        )
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(query.order_by(WorkOrder.created_at.desc()), page, per_page)
    statuses = [s.value for s in WorkOrderStatus]
    return render_template("work_orders/list.html", p=p,
                           status=status, search=search, active_page="work_orders", statuses=statuses, extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_work_order_form():
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    statuses = [s.value for s in WorkOrderStatus]
    return render_template("work_orders/form.html", work_order=None,
                           customers=customers, vehicles=vehicles, active_page="work_orders", statuses=statuses)


@bp.route("/new", methods=["POST"])
@login_required
def create_work_order():
    db = g.db
    try:
        wo = WorkOrder(
            customer_id=int(request.form["customer_id"]),
            vehicle_id=int(request.form["vehicle_id"]),
            title=request.form["title"],
            description=request.form.get("description", ""),
            diagnosis=request.form.get("diagnosis", ""),
            status=request.form.get("status", "New"),
            labor_hours=float(request.form.get("labor_hours", 0)),
            labor_rate=float(request.form.get("labor_rate", 150)),
            notes=request.form.get("notes", ""),
            odometer=int(request.form.get("odometer", 0)) or None,
        )
        db.add(wo)
        db.commit()
        _update_totals(wo.id, db)
        log_audit("create", "work_order", wo.id, f"Created WO: {wo.title}")
        flash("Work order created", "success")
        return redirect(f"/work-orders/{wo.id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in work_orders")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/work-orders/new")


@bp.route("/<int:wo_id>", methods=["GET"])
@login_required
def view_work_order(wo_id):
    db = g.db
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        flash("Work order not found", "warning")
        return redirect("/work-orders")
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    statuses = [s.value for s in WorkOrderStatus]
    return render_template("work_orders/detail.html", wo=wo, customers=customers,
                           vehicles=vehicles, active_page="work_orders", statuses=statuses)


@bp.route("/<int:wo_id>/edit", methods=["POST"])
@login_required
def update_work_order(wo_id):
    db = g.db
    try:
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if wo:
            wo.customer_id = int(request.form["customer_id"])
            wo.vehicle_id = int(request.form["vehicle_id"])
            wo.title = request.form["title"]
            wo.description = request.form.get("description", "")
            wo.diagnosis = request.form.get("diagnosis", "")
            wo.status = request.form.get("status", "New")
            wo.labor_hours = float(request.form.get("labor_hours", 0))
            wo.labor_rate = float(request.form.get("labor_rate", 150))
            wo.notes = request.form.get("notes", "")
            wo.odometer = int(request.form.get("odometer", 0)) or None
            if wo.status == "Completed" and not wo.completed_at:
                wo.completed_at = datetime.now()
            db.commit()
            _update_totals(wo.id, db)
            log_audit("update", "work_order", wo_id, f"Updated WO: {wo.title} -> {wo.status}")
            flash("Work order updated", "success")
        return redirect(f"/work-orders/{wo_id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in work_orders")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/work-orders/{wo_id}")


@bp.route("/<int:wo_id>/delete", methods=["POST"])
@login_required
def delete_work_order(wo_id):
    db = g.db
    try:
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if wo:
            log_audit("delete", "work_order", wo_id, f"Deleted WO: {wo.title}")
            db.delete(wo)
            db.commit()
            flash("Work order deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete work order failed")
        flash("Cannot delete: work order is linked to existing records", "danger")
    return redirect("/work-orders")


@bp.route("/<int:wo_id>/items/add", methods=["POST"])
@login_required
def add_work_order_item(wo_id):
    db = g.db
    try:
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if wo:
            qty = int(request.form.get("quantity", 1))
            price = float(request.form.get("unit_price", 0))
            part_used = request.form.get("part_used", "")
            part_link = request.form.get("part_id", "")
            item = WorkOrderItem(
                work_order_id=wo_id, description=request.form["description"],
                part_used=part_used, quantity=qty, unit_price=price,
                total_price=qty * price,
                is_labor=request.form.get("is_labor") == "on")
            db.add(item)
            if part_link and not item.is_labor:
                try:
                    pid = int(part_link)
                    part = db.query(Part).filter(Part.id == pid).first()
                    if part and part.quantity_on_hand >= qty:
                        part.quantity_on_hand -= qty
                        db.add(PartTransaction(
                            part_id=part.id, quantity_change=-qty,
                            transaction_type="Work Order",
                            reference=f"WO-{wo_id}",
                            notes=f"{item.description}"))
                except (ValueError, TypeError):
                    pass
            db.commit()
            _update_totals(wo_id, db)
        return redirect(f"/work-orders/{wo_id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in work_orders")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/work-orders/{wo_id}")


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_work_order_item(item_id):
    db = g.db
    try:
        item = db.query(WorkOrderItem).filter(WorkOrderItem.id == item_id).first()
        if item:
            wo_id = item.work_order_id
            db.delete(item)
            db.commit()
            _update_totals(wo_id, db)
            flash("Item removed", "info")
            return redirect(f"/work-orders/{wo_id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in work_orders")
        flash("An error occurred. Please try again.", "danger")
    return redirect("/work-orders")


def _update_totals(wo_id, db):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        return
    items = db.query(WorkOrderItem).filter(WorkOrderItem.work_order_id == wo_id).all()
    parts_total = sum(i.total_price for i in items if not i.is_labor)
    labor_total = sum(i.total_price for i in items if i.is_labor)
    if labor_total == 0:
        labor_total = wo.labor_hours * wo.labor_rate
    wo.parts_total = parts_total
    wo.total_amount = parts_total + labor_total
    db.commit()
