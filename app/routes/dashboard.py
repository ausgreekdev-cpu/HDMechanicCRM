from flask import Blueprint, render_template, g
from sqlalchemy import func
from datetime import datetime
from app.models import Customer, Vehicle, WorkOrder, Part, ScrapPickup, Lead, Technician, Schedule, ScrapInventory, Alert
from app.auth import login_required

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("", methods=["GET"])
@login_required
def dashboard():
    db = g.db
    total_customers = db.query(Customer).count()
    total_vehicles = db.query(func.count(Vehicle.id)).scalar() or 0
    active_work_orders = db.query(WorkOrder).filter(
        WorkOrder.status.not_in(["Completed", "Invoiced", "Cancelled"])
    ).count()
    completed_this_month = db.query(WorkOrder).filter(
        WorkOrder.status == "Completed",
        func.strftime("%Y-%m", WorkOrder.updated_at) == datetime.utcnow().strftime("%Y-%m")
    ).count()
    low_stock_parts = db.query(Part).filter(Part.quantity_on_hand <= Part.min_quantity).count()
    total_parts = db.query(Part).count()
    scrap_pickups_month = db.query(ScrapPickup).filter(
        func.strftime("%Y-%m", ScrapPickup.pickup_date) == datetime.utcnow().strftime("%Y-%m")
    ).count()
    open_leads = db.query(Lead).filter(Lead.status.not_in(["Closed", "Converted"])).count()
    tech_count = db.query(Technician).filter(Technician.is_active == True).count()
    total_scrap_weight = db.query(func.sum(ScrapInventory.weight_kg)).scalar() or 0
    total_scrap_value = db.query(func.sum(ScrapInventory.estimated_value)).scalar() or 0

    recent_work_orders = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(5).all()
    recent_pickups = db.query(ScrapPickup).order_by(ScrapPickup.created_at.desc()).limit(5).all()
    today_schedule = db.query(Schedule).filter(
        Schedule.scheduled_date == datetime.utcnow().date()
    ).order_by(Schedule.start_time).all()
    dashboard_alerts = db.query(Alert).filter(Alert.is_read == False).order_by(
        Alert.created_at.desc()).limit(5).all()

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
    return render_template("dashboard.html", stats=stats,
                           recent_work_orders=recent_work_orders,
                           recent_pickups=recent_pickups,
                           today_schedule=today_schedule,
                           alerts=dashboard_alerts,
                           active_page="dashboard")
