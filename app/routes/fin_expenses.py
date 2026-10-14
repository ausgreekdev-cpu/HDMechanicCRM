"""Expenses, job costing and budgets (same `finance` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date
from app.timeutils import utcnow, strftime_sql
from app.models import Expense, WorkOrder, Budget
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from sqlalchemy import func
from app.routes.finance import bp


# ---- Expenses ----
@bp.route("/expenses")
@login_required
def list_expenses():
    db = g.db
    page = int(request.args.get("page", 1))
    q = db.query(Expense).order_by(Expense.expense_date.desc())
    p = paginate(q, page, 50)
    total = db.query(func.sum(Expense.amount)).scalar() or 0
    return render_template("finance/expenses.html", p=p, total=total, active_page="expenses")


@bp.route("/expenses/new", methods=["POST"])
@login_required
def create_expense():
    db = g.db
    try:
        e = Expense(work_order_id=int(request.form.get("work_order_id", 0)) or None,
                    category=request.form["category"], amount=float(request.form["amount"]),
                    expense_date=date.fromisoformat(request.form["expense_date"]),
                    vendor=request.form.get("vendor", ""), description=request.form.get("description", ""),
                    notes=request.form.get("notes", ""))
        db.add(e); db.commit()
        log_audit("create", "expense", e.id, f"Expense ${e.amount:.2f} - {e.category}")
        flash("Expense recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/expenses")
# ---- Job Costing ----
@bp.route("/job-costing")
@login_required
def job_costing():
    db = g.db
    from sqlalchemy import func
    page = int(request.args.get("page", 1))
    query = db.query(WorkOrder).filter(WorkOrder.status.in_(["Completed", "Invoiced"])).order_by(WorkOrder.updated_at.desc())
    p = paginate(query, page)
    results = []
    for wo in p["rows"]:
        parts_cost = wo.parts_total
        labor_cost = wo.labor_hours * wo.labor_rate
        expenses = db.query(func.sum(Expense.amount)).filter(Expense.work_order_id == wo.id).scalar() or 0
        total_cost = parts_cost + labor_cost + expenses
        revenue = wo.total_amount
        results.append({"wo": wo, "parts_cost": parts_cost, "labor_cost": labor_cost,
                       "expenses": expenses, "total_cost": total_cost, "revenue": revenue,
                       "profit": revenue - total_cost, "margin_pct": ((revenue - total_cost) / revenue * 100) if revenue else 0})
    return render_template("finance/job_costing.html", results=results, p=p, active_page="job_costing")
# ---- Budget vs Actual ----
@bp.route("/budgets")
@login_required
def list_budgets():
    db = g.db
    year = int(request.args.get("year", utcnow().year))
    page = int(request.args.get("page", 1))
    query = db.query(Budget).filter(Budget.year == year).order_by(Budget.category)
    p = paginate(query, page)
    revenue = db.query(func.sum(WorkOrder.total_amount)).filter(
        strftime_sql("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).scalar() or 0
    expenses = db.query(func.sum(Expense.amount)).filter(
        strftime_sql("%Y", Expense.expense_date) == str(year)).scalar() or 0
    return render_template("finance/budgets.html", budgets=p["rows"], p=p, year=year,
                           revenue=revenue, expenses=expenses, active_page="budgets")


@bp.route("/budgets/new", methods=["POST"])
@login_required
def create_budget():
    db = g.db
    try:
        b = Budget(year=int(request.form["year"]), month=int(request.form.get("month", 0)) or None,
                   category=request.form.get("category", ""),
                   budgeted_amount=float(request.form.get("budgeted_amount", 0)),
                   notes=request.form.get("notes", ""))
        db.add(b); db.commit()
        flash("Budget entry created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/budgets")
