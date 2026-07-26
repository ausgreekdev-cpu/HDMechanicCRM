import logging
from flask import Blueprint, render_template, request, redirect, flash, g
from app.models import Estimate, EstimateItem, WorkOrder, WorkOrderItem
from app.auth import login_required
from app.audit import log_audit

bp = Blueprint("quote_to_wo", __name__, url_prefix="/ops")


@bp.route("/estimates/<int:eid>/convert-to-wo", methods=["POST"])
@login_required
def convert_to_wo(eid):
    db = g.db
    try:
        est = db.query(Estimate).filter(Estimate.id == eid).first()
        if not est:
            flash("Estimate not found", "danger")
            return redirect("/ops/estimates")
        if est.status == "Converted" and est.converted_wo_id:
            flash(f"Already converted to WO #{est.converted_wo_id}", "warning")
            return redirect(f"/work-orders/{est.converted_wo_id}")
        if est.status not in ("Approved", "Sent"):
            flash("Estimate must be approved (or at least sent) before converting", "warning")
            return redirect(f"/ops/estimates/{eid}")
        wo = WorkOrder(
            customer_id=est.customer_id, vehicle_id=est.vehicle_id,
            title=est.title, description=est.description,
            labor_hours=est.labor_hours, labor_rate=est.labor_rate,
            parts_total=est.parts_total, total_amount=est.total_amount,
            status="New", notes=f"Converted from estimate {est.estimate_number}"
        )
        db.add(wo)
        db.flush()
        for item in est.items:
            db.add(WorkOrderItem(
                work_order_id=wo.id, description=item.description,
                part_used=item.part_used, quantity=item.quantity,
                unit_price=item.unit_price, total_price=item.total_price,
                is_labor=item.is_labor
            ))
        est.converted_wo_id = wo.id
        est.status = "Converted"
        db.commit()
        log_audit("convert", "estimate", eid, f"Estimate {est.estimate_number} converted to WO #{wo.id}")
        flash(f"Work order #{wo.id} created from {est.estimate_number}", "success")
        return redirect(f"/work-orders/{wo.id}")
    except Exception:
        db.rollback()
        logging.exception("Error converting estimate to work order")
        flash("Conversion failed. Please try again.", "danger")
        return redirect(f"/ops/estimates/{eid}")


@bp.route("/estimates/<int:eid>/preview-wo")
@login_required
def preview_wo_from_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if not est:
        flash("Estimate not found", "danger")
        return redirect("/ops/estimates")
    return render_template("advanced_ops/wo_preview.html", est=est, active_page="estimates")
