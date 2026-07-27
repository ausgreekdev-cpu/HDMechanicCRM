from flask import Blueprint, render_template, g
from sqlalchemy import func, extract
from datetime import datetime
from app.timeutils import utcnow
from app.models import Customer, Vehicle, WorkOrder, Part, ScrapPickup, Lead, Technician, Schedule, ScrapInventory, Alert, Invoice
from app.auth import login_required
from app import cache, USE_REDIS, cached_query

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@cached_query("dashboard:stats", timeout=30)
def _get_dashboard_stats(db):
    now = utcnow()
    total_customers = db.query(Customer).count()
    total_vehicles = db.query(func.count(Vehicle.id)).scalar() or 0
    active_work_orders = db.query(WorkOrder).filter(
        WorkOrder.status.not_in(["Completed", "Invoiced", "Cancelled"])
    ).count()
    completed_this_month = db.query(WorkOrder).filter(
        WorkOrder.status == "Completed",
        func.strftime("%Y-%m", WorkOrder.updated_at) == now.strftime("%Y-%m")
    ).count()
    low_stock_parts = db.query(Part).filter(Part.quantity_on_hand <= Part.min_quantity).count()
    total_parts = db.query(Part).count()
    scrap_pickups_month = db.query(ScrapPickup).filter(
        func.strftime("%Y-%m", ScrapPickup.pickup_date) == now.strftime("%Y-%m")
    ).count()
    open_leads = db.query(Lead).filter(Lead.status.not_in(["Closed", "Converted"])).count()
    tech_count = db.query(Technician).filter(Technician.is_active == True).count()
    total_scrap_weight = db.query(func.sum(ScrapInventory.weight_kg)).scalar() or 0
    total_scrap_value = db.query(func.sum(ScrapInventory.estimated_value)).scalar() or 0

    recent_work_orders = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(5).all()
    recent_pickups = db.query(ScrapPickup).order_by(ScrapPickup.created_at.desc()).limit(5).all()
    today_schedule = db.query(Schedule).filter(
        Schedule.scheduled_date == now.date()
    ).order_by(Schedule.start_time).all()
    dashboard_alerts = db.query(Alert).filter(Alert.is_read == False).order_by(
        Alert.created_at.desc()).limit(5).all()

    months = []
    revenues = []
    for i in range(5, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year - (1 if now.month - i <= 0 else 0)
        months.append(f"{year}-{month:02d}")
        rev = db.query(func.sum(Invoice.total_amount)).filter(
            extract("year", Invoice.created_at) == year,
            extract("month", Invoice.created_at) == month,
            Invoice.status == "Paid"
        ).scalar() or 0
        revenues.append(float(rev))

    wo_statuses = db.query(
        WorkOrder.status, func.count(WorkOrder.id)
    ).group_by(WorkOrder.status).all()
    wo_labels = [s[0] for s in wo_statuses]
    wo_counts = [s[1] for s in wo_statuses]

    stats = {
        "total_customers": total_customers,
        "total_vehicles": total_vehicles,
        "active_work_orders": active_work_orders,
        "completed_this_month": completed_this_month,
        "low_stock_parts": low_stock_parts,
        "total_parts": total_parts,
        "scrap_pickups_month": scrap_pickups_month,
        "open_leads": open_leads,
        "technicians": tech_count,
        "total_scrap_weight": total_scrap_weight,
        "total_scrap_value": total_scrap_value,
    }
    return stats, recent_work_orders, recent_pickups, today_schedule, dashboard_alerts, months, revenues, wo_labels, wo_counts


@bp.route("", methods=["GET"])
@login_required
def dashboard():
    db = g.db
    stats, recent_work_orders, recent_pickups, today_schedule, dashboard_alerts, months, revenues, wo_labels, wo_counts = _get_dashboard_stats(db)
    return render_template("dashboard.html", stats=stats,
                           recent_work_orders=recent_work_orders,
                           recent_pickups=recent_pickups,
                           today_schedule=today_schedule,
                           alerts=dashboard_alerts,
                           active_page="dashboard",
                           chart_months=months,
                           chart_revenues=revenues,
                           chart_wo_labels=wo_labels,
                           chart_wo_counts=wo_counts)