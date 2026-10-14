"""Vendors and vendor quotes (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date
from app.models import Vendor, VendorQuote
from app.auth import login_required
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Vendor Portal (Quotes) ----
@bp.route("/vendors")
@login_required
def list_vendors():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(Vendor).order_by(Vendor.name), page)
    return render_template("advanced_ops/vendors.html", vendors=p["rows"], p=p, active_page="vendors")


@bp.route("/vendors/new", methods=["POST"])
@login_required
def create_vendor():
    db = g.db
    try:
        v = Vendor(name=request.form["name"], contact_person=request.form.get("contact_person", ""),
                   phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                   address=request.form.get("address", ""), vendor_type=request.form.get("vendor_type", ""),
                   payment_terms=request.form.get("payment_terms", ""), tax_id=request.form.get("tax_id", ""))
        db.add(v); db.commit()
        flash("Vendor created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/vendors")


@bp.route("/vendor-quotes")
@login_required
def list_vendor_quotes():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(VendorQuote).order_by(VendorQuote.created_at.desc()), page)
    return render_template("advanced_ops/vendor_quotes.html", quotes=p["rows"], p=p, active_page="vendor_quotes")


@bp.route("/vendor-quotes/new", methods=["POST"])
@login_required
def create_vendor_quote():
    db = g.db
    try:
        q = VendorQuote(vendor_id=int(request.form["vendor_id"]),
                        part_id=int(request.form.get("part_id", 0)) or None,
                        part_name=request.form.get("part_name", ""),
                        part_number=request.form.get("part_number", ""),
                        quantity=int(request.form.get("quantity", 1)),
                        unit_price=float(request.form.get("unit_price", 0)),
                        total_price=float(request.form.get("total_price", 0)),
                        lead_days=int(request.form.get("lead_days", 0)) or None,
                        valid_until=date.fromisoformat(request.form["valid_until"]) if request.form.get("valid_until") else None)
        db.add(q); db.commit()
        flash("Vendor quote added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/vendor-quotes")
