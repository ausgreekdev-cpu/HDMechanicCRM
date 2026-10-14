"""Core charges and part cross-references (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
from app.models import CoreCharge, CoreReturn, PartCrossReference
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Core Charges & Returns ----
@bp.route("/core-charges")
@login_required
def list_core_charges():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(CoreCharge).order_by(CoreCharge.created_at.desc()), page)
    return render_template("advanced_ops/core_charges.html", charges=p["rows"], p=p, active_page="core_charges")


@bp.route("/core-charges/new", methods=["POST"])
@login_required
def create_core_charge():
    db = g.db
    try:
        cc = CoreCharge(part_id=int(request.form["part_id"]),
                        charge_amount=float(request.form.get("charge_amount", 0)),
                        is_refundable=request.form.get("is_refundable") == "on")
        db.add(cc); db.commit()
        log_audit("create", "core_charge", cc.id, f"Core charge for part #{cc.part_id}")
        flash("Core charge created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/core-charges")


@bp.route("/core-charges/<int:ccid>/return", methods=["POST"])
@login_required
def return_core(ccid):
    db = g.db
    cc = db.query(CoreCharge).filter(CoreCharge.id == ccid).first()
    if cc:
        cr = CoreReturn(core_charge_id=ccid, work_order_id=int(request.form.get("work_order_id", 0)) or None,
                        refund_amount=float(request.form.get("refund_amount", cc.charge_amount)),
                        notes=request.form.get("notes", ""))
        db.add(cr); db.commit()
        log_audit("return", "core", ccid, f"Core returned ${cr.refund_amount:.2f}")
        flash("Core return recorded", "success")
    return redirect("/ops/core-charges")
# ---- Part Cross References ----
@bp.route("/cross-references")
@login_required
def list_cross_refs():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(PartCrossReference).order_by(PartCrossReference.cross_brand), page)
    return render_template("advanced_ops/cross_refs.html", refs=p["rows"], p=p, active_page="cross_refs")


@bp.route("/cross-references/new", methods=["POST"])
@login_required
def create_cross_ref():
    db = g.db
    try:
        cr = PartCrossReference(part_id=int(request.form["part_id"]),
                                cross_type=request.form.get("cross_type", "OEM"),
                                cross_part_number=request.form["cross_part_number"],
                                cross_brand=request.form.get("cross_brand", ""),
                                cross_description=request.form.get("cross_description", ""),
                                notes=request.form.get("notes", ""))
        db.add(cr); db.commit()
        flash("Cross reference added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/cross-references")
