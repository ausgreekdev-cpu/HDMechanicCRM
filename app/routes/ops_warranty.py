"""Warranties and warranty claims (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date, timedelta
from app.models import Warranty, WarrantyClaim
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Warranties ----
@bp.route("/warranties")
@login_required
def list_warranties():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(Warranty).order_by(Warranty.created_at.desc()), page)
    return render_template("advanced_ops/warranties.html", warranties=p["rows"], p=p, active_page="warranties")


@bp.route("/warranties/new", methods=["POST"])
@login_required
def create_warranty():
    db = g.db
    try:
        w = Warranty(entity_type=request.form["entity_type"], entity_id=int(request.form["entity_id"]),
                     warranty_type=request.form.get("warranty_type", "Parts"),
                     duration_days=int(request.form.get("duration_days", 365)),
                     duration_miles=int(request.form.get("duration_miles", 0)) or None,
                     start_date=date.fromisoformat(request.form["start_date"]),
                     notes=request.form.get("notes", ""))
        if w.duration_days: w.end_date = w.start_date + timedelta(days=w.duration_days)
        db.add(w); db.commit()
        log_audit("create", "warranty", w.id, f"Warranty created")
        flash("Warranty created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/warranties")


@bp.route("/warranty-claims")
@login_required
def list_warranty_claims():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(WarrantyClaim).order_by(WarrantyClaim.created_at.desc()), page)
    return render_template("advanced_ops/warranty_claims.html", claims=p["rows"], p=p, active_page="warranty_claims")


@bp.route("/warranty-claims/new", methods=["POST"])
@login_required
def create_warranty_claim():
    db = g.db
    try:
        c = WarrantyClaim(warranty_id=int(request.form["warranty_id"]),
                          work_order_id=int(request.form.get("work_order_id", 0)) or None,
                          description=request.form.get("description", ""),
                          labor_cost=float(request.form.get("labor_cost", 0)),
                          parts_cost=float(request.form.get("parts_cost", 0)),
                          total_claim=float(request.form.get("total_claim", 0)),
                          notes=request.form.get("notes", ""))
        db.add(c); db.commit()
        log_audit("create", "warranty_claim", c.id, f"Warranty claim filed")
        flash("Warranty claim created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/warranty-claims")
