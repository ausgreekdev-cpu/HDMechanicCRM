"""Late fees, 1099 contractors and tax exemptions (same `finance` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date, timedelta
from app.timeutils import utcnow
from app.models import Invoice, LateFeeRule, Contractor1099, TaxExemption
from app.auth import login_required
from app.helpers import paginate
from app.routes.finance import bp


# ---- Late Fees ----
@bp.route("/late-fee-rules")
@login_required
def list_late_fee_rules():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(LateFeeRule).order_by(LateFeeRule.name)
    p = paginate(query, page)
    return render_template("finance/late_fee_rules.html", rules=p["rows"], p=p, active_page="late_fee_rules")


@bp.route("/late-fee-rules/new", methods=["POST"])
@login_required
def create_late_fee_rule():
    db = g.db
    try:
        r = LateFeeRule(name=request.form["name"], days_overdue=int(request.form.get("days_overdue", 30)),
                        fee_type=request.form.get("fee_type", "Percentage"),
                        fee_value=float(request.form.get("fee_value", 5)),
                        max_fee=float(request.form.get("max_fee", 0)))
        db.add(r); db.commit()
        flash("Late fee rule created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/late-fee-rules")
# ---- Apply Late Fees ----
@bp.route("/apply-late-fees", methods=["POST"])
@login_required
def apply_late_fees():
    db = g.db
    try:
        rules = db.query(LateFeeRule).filter(LateFeeRule.is_active == True).all()
        now = utcnow()
        applied = 0
        for rule in rules:
            overdue = db.query(Invoice).filter(
                Invoice.status.in_(["Unpaid", "Partial"]),
                Invoice.created_at <= now - timedelta(days=rule.days_overdue)
            ).all()
            for inv in overdue:
                if rule.fee_type == "Percentage":
                    fee = inv.total_amount * (rule.fee_value / 100)
                    if rule.max_fee > 0: fee = min(fee, rule.max_fee)
                else:
                    fee = rule.fee_value
                inv.total_amount += fee
                applied += 1
        db.commit()
        flash(f"Late fees applied to {applied} invoices", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/late-fee-rules")
# ---- 1099 Contractors ----
@bp.route("/contractors")
@login_required
def list_contractors():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(Contractor1099).order_by(Contractor1099.name)
    p = paginate(query, page)
    return render_template("finance/contractors.html", contractors=p["rows"], p=p, active_page="contractors")


@bp.route("/contractors/new", methods=["POST"])
@login_required
def create_contractor():
    db = g.db
    try:
        c = Contractor1099(name=request.form["name"], tax_id=request.form.get("tax_id", ""),
                           address=request.form.get("address", ""), phone=request.form.get("phone", ""),
                           email=request.form.get("email", ""), notes=request.form.get("notes", ""))
        db.add(c); db.commit()
        flash("Contractor created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/contractors")
# ---- Tax Exemptions ----
@bp.route("/tax-exemptions")
@login_required
def list_tax_exemptions():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(TaxExemption).order_by(TaxExemption.customer_id)
    p = paginate(query, page)
    return render_template("finance/tax_exemptions.html", items=p["rows"], p=p, active_page="tax_exemptions")


@bp.route("/tax-exemptions/new", methods=["POST"])
@login_required
def create_tax_exemption():
    db = g.db
    try:
        te = TaxExemption(customer_id=int(request.form["customer_id"]),
                          exemption_number=request.form.get("exemption_number", ""),
                          jurisdiction=request.form.get("jurisdiction", ""),
                          expires_at=date.fromisoformat(request.form["expires_at"]) if request.form.get("expires_at") else None,
                          notes=request.form.get("notes", ""))
        db.add(te); db.commit()
        flash("Tax exemption recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/tax-exemptions")
