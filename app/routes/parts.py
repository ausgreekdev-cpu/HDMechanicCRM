from flask import Blueprint, render_template, request, redirect, flash, jsonify, g
import logging
from app.models import Part, PartTransaction, PurchaseOrder, PurchaseOrderItem, Alert
from app.auth import login_required
from app.helpers import paginate
from app.audit import log_audit
import urllib.parse

bp = Blueprint("parts", __name__, url_prefix="/parts")


@bp.route("", methods=["GET"])
@login_required
def list_parts():
    db = g.db
    search = request.args.get("search", "")
    low_stock = request.args.get("low_stock", "")
    reorder = request.args.get("reorder", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    query = db.query(Part)
    if low_stock:
        query = query.filter(Part.quantity_on_hand <= Part.min_quantity)
    if reorder:
        query = query.filter(Part.quantity_on_hand <= Part.min_quantity,
                             Part.max_quantity > 0)
    if search:
        query = query.filter(Part.name.ilike(f"%{search}%") | Part.part_number.ilike(f"%{search}%") |
                            Part.supplier.ilike(f"%{search}%") | Part.category.ilike(f"%{search}%") |
                            Part.barcode.ilike(f"%{search}%"))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(query.order_by(Part.name), page, per_page)
    return render_template("parts/list.html", p=p, search=search,
                           low_stock=low_stock, reorder=reorder,
                           active_page="parts", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_part_form():
    return render_template("parts/form.html", part=None, active_page="parts")


@bp.route("/new", methods=["POST"])
@login_required
def create_part():
    db = g.db
    try:
        p = Part(name=request.form["name"], part_number=request.form.get("part_number", ""),
                 barcode=request.form.get("barcode", ""),
                 category=request.form.get("category", ""), supplier=request.form.get("supplier", ""),
                 supplier_part_number=request.form.get("supplier_part_number", ""),
                 cost_price=float(request.form.get("cost_price", 0)),
                 selling_price=float(request.form.get("selling_price", 0)),
                 quantity_on_hand=int(request.form.get("quantity_on_hand", 0)),
                 min_quantity=int(request.form.get("min_quantity", 5)),
                 max_quantity=int(request.form.get("max_quantity", 0)),
                 location=request.form.get("location", ""), notes=request.form.get("notes", ""))
        db.add(p)
        db.commit()
        log_audit("create", "part", p.id, f"Created part {p.name}")
        flash("Part added", "success")
        return redirect("/parts")
    except Exception:
        db.rollback()
        logging.exception("Error in parts")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/parts/new")


@bp.route("/<int:part_id>/edit", methods=["GET"])
@login_required
def edit_part_form(part_id):
    db = g.db
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        return redirect("/parts")
    return render_template("parts/form.html", part=part, active_page="parts")


@bp.route("/<int:part_id>/edit", methods=["POST"])
@login_required
def update_part(part_id):
    db = g.db
    try:
        p = db.query(Part).filter(Part.id == part_id).first()
        if p:
            p.name = request.form["name"]
            p.part_number = request.form.get("part_number", "")
            p.barcode = request.form.get("barcode", "")
            p.category = request.form.get("category", "")
            p.supplier = request.form.get("supplier", "")
            p.supplier_part_number = request.form.get("supplier_part_number", "")
            p.cost_price = float(request.form.get("cost_price", 0))
            p.selling_price = float(request.form.get("selling_price", 0))
            p.quantity_on_hand = int(request.form.get("quantity_on_hand", 0))
            p.min_quantity = int(request.form.get("min_quantity", 5))
            p.max_quantity = int(request.form.get("max_quantity", 0))
            p.location = request.form.get("location", "")
            p.notes = request.form.get("notes", "")
            db.commit()
            log_audit("update", "part", part_id, f"Updated part {p.name}")
            flash("Part updated", "success")
        return redirect("/parts")
    except Exception:
        db.rollback()
        logging.exception("Error in parts")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/parts/{part_id}/edit")


@bp.route("/<int:part_id>/delete", methods=["POST"])
@login_required
def delete_part(part_id):
    db = g.db
    try:
        p = db.query(Part).filter(Part.id == part_id).first()
        if p:
            db.delete(p)
            db.commit()
            log_audit("delete", "part", part_id, f"Deleted part {p.name}")
            flash("Part deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete part failed")
        flash("Cannot delete: part is linked to existing records", "danger")
    return redirect("/parts")


@bp.route("/<int:part_id>/adjust", methods=["POST"])
@login_required
def adjust_stock(part_id):
    db = g.db
    try:
        p = db.query(Part).filter(Part.id == part_id).first()
        if p:
            change = int(request.form["quantity_change"])
            p.quantity_on_hand += change
            txn = PartTransaction(part_id=part_id, quantity_change=change,
                                  transaction_type=request.form.get("transaction_type", "Adjustment"),
                                  reference=request.form.get("reference", ""),
                                  notes=request.form.get("notes", ""))
            db.add(txn)
            db.commit()
            log_audit("stock_adjust", "part", part_id, f"Adjusted stock by {change:+d}")
            flash(f"Stock adjusted by {change:+d} (new: {p.quantity_on_hand})", "success")
        return redirect("/parts")
    except Exception:
        db.rollback()
        logging.exception("Error in parts")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/parts")


@bp.route("/reorder-suggestions")
@login_required
def reorder_suggestions():
    db = g.db
    parts = db.query(Part).filter(
        Part.quantity_on_hand <= Part.min_quantity,
        Part.max_quantity > 0
    ).order_by(Part.name).all()
    suggestions = []
    for p in parts:
        needed = p.max_quantity - p.quantity_on_hand
        if needed > 0:
            suggestions.append({
                "part": p,
                "suggested_qty": needed,
                "estimated_cost": round(needed * p.cost_price, 2)
            })
    return render_template("parts/reorder.html", suggestions=suggestions, active_page="parts")


@bp.route("/barcode/<barcode>")
@login_required
def lookup_barcode(barcode):
    db = g.db
    part = db.query(Part).filter(Part.barcode == barcode).first()
    if part:
        return jsonify({"found": True, "id": part.id, "name": part.name,
                       "part_number": part.part_number, "qty": part.quantity_on_hand,
                       "price": part.selling_price})
    return jsonify({"found": False})
