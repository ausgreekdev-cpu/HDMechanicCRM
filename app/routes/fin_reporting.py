"""Revenue by category (same `finance` blueprint)."""
from flask import render_template, request, g
from app.timeutils import utcnow, strftime_sql
from app.models import WorkOrder, ScrapPickup
from app.auth import login_required
from app.routes.finance import bp


# ---- Revenue by Category ----
@bp.route("/revenue-by-category")
@login_required
def revenue_by_category():
    db = g.db
    from sqlalchemy import func
    year = int(request.args.get("year", utcnow().year))
    revenue = db.query(func.sum(WorkOrder.total_amount)).filter(
        strftime_sql("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).scalar() or 0
    scrap = db.query(func.sum(ScrapPickup.total_payout)).filter(
        strftime_sql("%Y", ScrapPickup.pickup_date) == str(year)).scalar() or 0
    wo_count = db.query(WorkOrder).filter(
        strftime_sql("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).count() or 0
    return render_template("finance/revenue_categories.html", year=year,
                           revenue=revenue, scrap=scrap, wo_count=wo_count, active_page="revenue_categories")
