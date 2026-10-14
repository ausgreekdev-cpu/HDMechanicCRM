"""Multi-company management (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
import logging
from app.models import Company
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Multi-Company ----
@bp.route("/companies")
@login_required
def list_companies():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(Company).order_by(Company.name), page)
    return render_template("advanced_ops/companies.html", companies=p["rows"], p=p, active_page="companies")


@bp.route("/companies/new", methods=["POST"])
@login_required
def create_company():
    db = g.db
    try:
        c = Company(name=request.form["name"], legal_name=request.form.get("legal_name", ""),
                    tax_id=request.form.get("tax_id", ""), address=request.form.get("address", ""),
                    phone=request.form.get("phone", ""), email=request.form.get("email", ""))
        db.add(c); db.commit()
        log_audit("create", "company", c.id, f"Created company {c.name}")
        flash("Company created", "success")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Error creating company", "danger")
    return redirect("/ops/companies")


@bp.route("/companies/<int:cid>/toggle", methods=["POST"])
@login_required
def toggle_company(cid):
    db = g.db
    c = db.query(Company).filter(Company.id == cid).first()
    if c: c.is_active = not c.is_active; db.commit()
    return redirect("/ops/companies")
