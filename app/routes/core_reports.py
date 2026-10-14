"""Reports, charts, and forecasting (same `core` blueprint)."""
from flask import render_template, request, jsonify, g
from app.auth import login_required
from app.helpers import paginate
from app.timeutils import utcnow, strftime_sql
from app.routes.core import bp


# ---- Reports ----
@bp.route("/reports")
@login_required
def reports():
    from app.models import Customer, WorkOrder, Part, ScrapPickup, Invoice, Lead
    from sqlalchemy import func
    db = g.db
    now = utcnow()
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
# ---- Technician Efficiency Report ----
@bp.route("/reports/technician-efficiency")
@login_required
def technician_efficiency():
    from app.models import Technician, WorkOrder, Schedule
    from sqlalchemy import func
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(Technician).filter(Technician.is_active == True).order_by(Technician.name)
    p = paginate(query, page)
    results = []
    for t in p["rows"]:
        total_hours = db.query(func.sum(WorkOrder.labor_hours)).join(
            Schedule, Schedule.work_order_id == WorkOrder.id
        ).filter(Schedule.technician_id == t.id, WorkOrder.status == "Completed").scalar() or 0
        wo_count = db.query(WorkOrder).join(
            Schedule, Schedule.work_order_id == WorkOrder.id
        ).filter(Schedule.technician_id == t.id, WorkOrder.status == "Completed").count()
        results.append({"name": t.name, "specialization": t.specialization or "",
                        "hourly_rate": t.hourly_rate, "total_hours": total_hours,
                        "wo_count": wo_count, "earned": total_hours * t.hourly_rate})
    return render_template("reports/tech_efficiency.html", techs=results, p=p, active_page="reports")
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
# ---- Chart API ----
@bp.route("/api/chart/revenue")
@login_required
def chart_revenue():
    from app.models import WorkOrder
    from sqlalchemy import func
    db = g.db
    rows = db.query(
        strftime_sql("%Y-%m", WorkOrder.updated_at).label("month"),
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
        strftime_sql("%Y-%m", ScrapPickup.pickup_date).label("month"),
        func.sum(ScrapPickup.total_payout)
    ).group_by("month").order_by("month").all()
    return jsonify(labels=[r.month for r in rows], values=[float(r[1] or 0) for r in rows])
