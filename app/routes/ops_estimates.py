"""Estimates: list, create, approve, convert, send (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
import logging
from datetime import date, timedelta
from app.timeutils import utcnow
from app.models import Estimate, EstimateItem, Customer, Vehicle, WorkOrder, WorkOrderItem
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Estimates (Estimate → Approve → WO) ----
@bp.route("/estimates")
@login_required
def list_estimates():
    db = g.db
    status = request.args.get("status", "")
    q = db.query(Estimate)
    if status: q = q.filter(Estimate.status == status)
    page = int(request.args.get("page", 1))
    p = paginate(q.order_by(Estimate.created_at.desc()), page, 50)
    return render_template("advanced_ops/estimates.html", p=p, status=status, active_page="estimates")


@bp.route("/estimates/new", methods=["GET"])
@login_required
def new_estimate_form():
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("advanced_ops/estimate_form.html", estimate=None, customers=customers, vehicles=vehicles, active_page="estimates")


@bp.route("/estimates/new", methods=["POST"])
@login_required
def create_estimate():
    db = g.db
    try:
        count = db.query(Estimate).count() + 1
        est = Estimate(estimate_number=f"EST-{utcnow().strftime('%Y%m')}-{count:04d}",
                       customer_id=int(request.form["customer_id"]), vehicle_id=int(request.form["vehicle_id"]),
                       title=request.form["title"], description=request.form.get("description", ""),
                       labor_hours=float(request.form.get("labor_hours", 0)),
                       labor_rate=float(request.form.get("labor_rate", 150)),
                       status="Draft", expires_at=date.today() + timedelta(days=30))
        db.add(est); db.flush()
        descs = request.form.getlist("item_desc[]"); qtys = request.form.getlist("item_qty[]")
        prices = request.form.getlist("item_price[]"); labors = request.form.getlist("item_labor[]")
        for d, q, p, l in zip(descs, qtys, prices, labors):
            if d.strip():
                qty = int(q or 1); price = float(p or 0)
                db.add(EstimateItem(estimate_id=est.id, description=d, quantity=qty, unit_price=price,
                                    total_price=qty * price, is_labor=(l == "on")))
        est.parts_total = sum(i.total_price for i in est.items if not i.is_labor) if est.items else 0
        labor_total = sum(i.total_price for i in est.items if i.is_labor) if est.items else est.labor_hours * est.labor_rate
        est.total_amount = est.parts_total + labor_total
        db.commit()
        log_audit("create", "estimate", est.id, f"Created estimate {est.estimate_number}")
        flash("Estimate created", "success")
        return redirect(f"/ops/estimates/{est.id}")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Error creating estimate", "danger")
        return redirect("/ops/estimates/new")


@bp.route("/estimates/<int:eid>")
@login_required
def view_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if not est: return redirect("/ops/estimates")
    return render_template("advanced_ops/estimate_detail.html", est=est, active_page="estimates")


@bp.route("/estimates/<int:eid>/approve", methods=["POST"])
@login_required
def approve_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if est:
        est.status = "Approved"; est.approved_at = utcnow()
        db.commit()
        log_audit("approve", "estimate", eid, f"Approved estimate {est.estimate_number}")
        flash("Estimate approved", "success")
    return redirect(f"/ops/estimates/{eid}")


@bp.route("/estimates/<int:eid>/convert", methods=["POST"])
@login_required
def convert_estimate_to_wo(eid):
    db = g.db
    try:
        est = db.query(Estimate).filter(Estimate.id == eid).first()
        if est and est.status == "Approved":
            wo = WorkOrder(customer_id=est.customer_id, vehicle_id=est.vehicle_id,
                           title=est.title, description=est.description,
                           labor_hours=est.labor_hours, labor_rate=est.labor_rate,
                           status="New")
            db.add(wo); db.flush()
            for item in est.items:
                db.add(WorkOrderItem(work_order_id=wo.id, description=item.description,
                                     part_used=item.part_used, quantity=item.quantity,
                                     unit_price=item.unit_price, total_price=item.total_price,
                                     is_labor=item.is_labor))
            est.converted_wo_id = wo.id; est.status = "Converted"
            db.commit()
            log_audit("convert", "estimate", eid, f"Converted to WO #{wo.id}")
            flash(f"Work order #{wo.id} created from estimate", "success")
            return redirect(f"/work-orders/{wo.id}")
        flash("Estimate must be approved first", "warning")
        return redirect(f"/ops/estimates/{eid}")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Conversion failed", "danger")
        return redirect(f"/ops/estimates/{eid}")


@bp.route("/estimates/<int:eid>/send", methods=["POST"])
@login_required
def send_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if est:
        est.status = "Sent"; db.commit()
        if est.customer and est.customer.email:
            from app.helpers import send_email
            body = f"<h2>Estimate {est.estimate_number}</h2><p>Your estimate #{est.estimate_number} for ${est.total_amount:.2f} is ready for review.</p>"
            send_email(est.customer.email, f"Estimate {est.estimate_number} from HD Mechanic CRM", body)
        flash("Estimate sent to customer", "success")
    return redirect(f"/ops/estimates/{eid}")
