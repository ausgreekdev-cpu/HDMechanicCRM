from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import date
from app.models import ScrapVendor, ScrapPickup, ScrapInventory
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("scrap_metal", __name__, url_prefix="/scrap")


@bp.route("/vendors", methods=["GET"])
@login_required
def list_vendors():
    db = g.db
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(ScrapVendor)
    if search:
        q = q.filter(ScrapVendor.name.ilike(f"%{search}%") | ScrapVendor.material_types.ilike(f"%{search}%"))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(ScrapVendor.name), page, per_page)
    return render_template("scrap/vendors.html", p=p,
                           search=search, active_page="scrap_vendors", extra=extra)


@bp.route("/vendors/new", methods=["GET"])
@login_required
def new_vendor_form():
    return render_template("scrap/vendor_form.html", vendor=None, active_page="scrap_vendors")


@bp.route("/vendors/new", methods=["POST"])
@login_required
def create_vendor():
    db = g.db
    try:
        v = ScrapVendor(name=request.form["name"], contact_person=request.form.get("contact_person", ""),
                        phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                        address=request.form.get("address", ""),
                        material_types=request.form.get("material_types", ""),
                        notes=request.form.get("notes", ""))
        db.add(v)
        db.commit()
        flash("Vendor created", "success")
        return redirect("/scrap/vendors")
    except Exception as e:
        db.rollback()
        logging.exception("Error in scrap_metal")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/scrap/vendors/new")


@bp.route("/vendors/<int:vendor_id>/edit", methods=["GET"])
@login_required
def edit_vendor_form(vendor_id):
    db = g.db
    v = db.query(ScrapVendor).filter(ScrapVendor.id == vendor_id).first()
    if not v:
        return redirect("/scrap/vendors")
    return render_template("scrap/vendor_form.html", vendor=v, active_page="scrap_vendors")


@bp.route("/vendors/<int:vendor_id>/edit", methods=["POST"])
@login_required
def update_vendor(vendor_id):
    db = g.db
    try:
        v = db.query(ScrapVendor).filter(ScrapVendor.id == vendor_id).first()
        if v:
            v.name = request.form["name"]
            v.contact_person = request.form.get("contact_person", "")
            v.phone = request.form.get("phone", "")
            v.email = request.form.get("email", "")
            v.address = request.form.get("address", "")
            v.material_types = request.form.get("material_types", "")
            v.notes = request.form.get("notes", "")
            db.commit()
            flash("Vendor updated", "success")
        return redirect("/scrap/vendors")
    except Exception as e:
        db.rollback()
        logging.exception("Error in scrap_metal")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/scrap/vendors/{vendor_id}/edit")


@bp.route("/vendors/<int:vendor_id>/delete", methods=["POST"])
@login_required
def delete_vendor(vendor_id):
    db = g.db
    try:
        v = db.query(ScrapVendor).filter(ScrapVendor.id == vendor_id).first()
        if v:
            db.delete(v)
            db.commit()
            flash("Vendor deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete scrap record failed")
        flash("Cannot delete: record is linked to existing records", "danger")
    return redirect("/scrap/vendors")


@bp.route("/pickups", methods=["GET"])
@login_required
def list_pickups():
    db = g.db
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(ScrapPickup)
    if search:
        q = q.filter(ScrapPickup.material_type.ilike(f"%{search}%"))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(ScrapPickup.pickup_date.desc()), page, per_page)
    return render_template("scrap/pickups.html", p=p,
                           search=search, active_page="scrap_pickups", extra=extra)


@bp.route("/pickups/new", methods=["GET"])
@login_required
def new_pickup_form():
    db = g.db
    vendors = db.query(ScrapVendor).filter(ScrapVendor.is_active == True).order_by(ScrapVendor.name).all()
    return render_template("scrap/pickup_form.html", pickup=None, vendors=vendors, active_page="scrap_pickups")


@bp.route("/pickups/new", methods=["POST"])
@login_required
def create_pickup():
    db = g.db
    try:
        w = float(request.form["weight_kg"])
        ppkg = float(request.form.get("price_per_kg", 0))
        payout = w * ppkg
        mat = request.form["material_type"]
        p = ScrapPickup(vendor_id=int(request.form["vendor_id"]),
                        pickup_date=date.fromisoformat(request.form["pickup_date"]),
                        material_type=mat, weight_kg=w, price_per_kg=ppkg,
                        total_payout=payout, location=request.form.get("location", ""),
                        notes=request.form.get("notes", ""))
        db.add(p)
        db.commit()
        _update_inventory(mat, w, payout, db)
        flash("Pickup recorded", "success")
        return redirect("/scrap/pickups")
    except Exception as e:
        db.rollback()
        logging.exception("Error in scrap_metal")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/scrap/pickups/new")


@bp.route("/pickups/<int:pickup_id>/edit", methods=["GET"])
@login_required
def edit_pickup_form(pickup_id):
    db = g.db
    p = db.query(ScrapPickup).filter(ScrapPickup.id == pickup_id).first()
    if not p:
        return redirect("/scrap/pickups")
    vendors = db.query(ScrapVendor).order_by(ScrapVendor.name).all()
    return render_template("scrap/pickup_form.html", pickup=p, vendors=vendors, active_page="scrap_pickups")


@bp.route("/pickups/<int:pickup_id>/edit", methods=["POST"])
@login_required
def update_pickup(pickup_id):
    db = g.db
    try:
        p = db.query(ScrapPickup).filter(ScrapPickup.id == pickup_id).first()
        if p:
            old_w, old_pay = p.weight_kg, p.total_payout
            nw = float(request.form["weight_kg"])
            npk = float(request.form.get("price_per_kg", 0))
            nm = request.form["material_type"]
            p.vendor_id = int(request.form["vendor_id"])
            p.pickup_date = date.fromisoformat(request.form["pickup_date"])
            p.material_type = nm
            p.weight_kg = nw
            p.price_per_kg = npk
            p.total_payout = nw * npk
            p.location = request.form.get("location", "")
            p.notes = request.form.get("notes", "")
            db.commit()
            _update_inventory(nm, nw - old_w, p.total_payout - old_pay, db)
            flash("Pickup updated", "success")
        return redirect("/scrap/pickups")
    except Exception as e:
        db.rollback()
        logging.exception("Error in scrap_metal")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/scrap/pickups/{pickup_id}/edit")


@bp.route("/pickups/<int:pickup_id>/delete", methods=["POST"])
@login_required
def delete_pickup(pickup_id):
    db = g.db
    try:
        p = db.query(ScrapPickup).filter(ScrapPickup.id == pickup_id).first()
        if p:
            _update_inventory(p.material_type, -p.weight_kg, -p.total_payout, db)
            db.delete(p)
            db.commit()
            flash("Pickup deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete scrap record failed")
        flash("Cannot delete: record is linked to existing records", "danger")
    return redirect("/scrap/pickups")


@bp.route("/inventory", methods=["GET"])
@login_required
def view_inventory():
    db = g.db
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    inv_query = db.query(ScrapInventory).order_by(ScrapInventory.material_type)
    all_items = inv_query.all()
    total_weight = sum(i.weight_kg for i in all_items)
    total_value = sum(i.estimated_value for i in all_items)
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(inv_query, page, per_page)
    return render_template("scrap/inventory.html", p=p,
                           total_weight=total_weight, total_value=total_value,
                           active_page="scrap_inventory", extra=extra)


@bp.route("/inventory/<int:inv_id>/edit", methods=["POST"])
@login_required
def update_inventory(inv_id):
    db = g.db
    try:
        inv = db.query(ScrapInventory).filter(ScrapInventory.id == inv_id).first()
        if inv:
            inv.weight_kg = float(request.form.get("weight_kg", 0))
            inv.estimated_value = float(request.form.get("estimated_value", 0))
            inv.notes = request.form.get("notes", "")
            db.commit()
            flash("Inventory updated", "success")
        return redirect("/scrap/inventory")
    except Exception as e:
        db.rollback()
        logging.exception("Error in scrap_metal")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/scrap/inventory")


def _update_inventory(material_type, weight_change, value_change, db):
    inv = db.query(ScrapInventory).filter(ScrapInventory.material_type == material_type).first()
    if not inv:
        if weight_change > 0:
            db.add(ScrapInventory(material_type=material_type, weight_kg=max(0, weight_change),
                                  estimated_value=max(0, value_change)))
    else:
        inv.weight_kg = max(0, inv.weight_kg + weight_change)
        inv.estimated_value = max(0, inv.estimated_value + value_change)
