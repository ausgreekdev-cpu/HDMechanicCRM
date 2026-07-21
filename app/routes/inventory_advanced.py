from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import datetime, date
from app.models import Warehouse, BinLocation, Part, SerialNumber, KitAssembly, KitItem, PartSupersession, NonStockItem, ConsignmentItem, CycleCount, User, InventoryTransfer, SupplierScorecard
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate

bp = Blueprint("inventory_advanced", __name__, url_prefix="/inv")


# ---- Warehouses ----
@bp.route("/warehouses")
@login_required
def list_warehouses():
    db = g.db
    warehouses = db.query(Warehouse).order_by(Warehouse.name).all()
    return render_template("inventory_advanced/warehouses.html", warehouses=warehouses, active_page="warehouses")


@bp.route("/warehouses/new", methods=["POST"])
@login_required
def create_warehouse():
    db = g.db
    try:
        w = Warehouse(name=request.form["name"], location=request.form.get("location", ""))
        db.add(w); db.commit()
        flash("Warehouse created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/warehouses")


# ---- Bin Locations ----
@bp.route("/bins")
@login_required
def list_bins():
    db = g.db
    bins = db.query(BinLocation).order_by(BinLocation.bin_code).all()
    warehouses = db.query(Warehouse).order_by(Warehouse.name).all()
    return render_template("inventory_advanced/bins.html", bins=bins, warehouses=warehouses, active_page="bins")


@bp.route("/bins/new", methods=["POST"])
@login_required
def create_bin():
    db = g.db
    try:
        b = BinLocation(warehouse_id=int(request.form["warehouse_id"]),
                        part_id=int(request.form.get("part_id", 0)) or None,
                        bin_code=request.form["bin_code"],
                        max_capacity=int(request.form.get("max_capacity", 0)),
                        notes=request.form.get("notes", ""))
        db.add(b); db.commit()
        flash("Bin location created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/bins")


# ---- Serial Numbers ----
@bp.route("/serial-numbers")
@login_required
def list_serial_numbers():
    db = g.db
    serials = db.query(SerialNumber).order_by(SerialNumber.created_at.desc()).all()
    return render_template("inventory_advanced/serials.html", serials=serials, active_page="serials")


@bp.route("/serial-numbers/new", methods=["POST"])
@login_required
def create_serial_number():
    db = g.db
    try:
        s = SerialNumber(part_id=int(request.form["part_id"]),
                         serial_number=request.form["serial_number"],
                         status=request.form.get("status", "In Stock"),
                         notes=request.form.get("notes", ""))
        db.add(s); db.commit()
        flash("Serial number recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/serial-numbers")


# ---- Kit Assemblies ----
@bp.route("/kits")
@login_required
def list_kits():
    db = g.db
    kits = db.query(KitAssembly).order_by(KitAssembly.name).all()
    return render_template("inventory_advanced/kits.html", kits=kits, active_page="kits")


@bp.route("/kits/new", methods=["POST"])
@login_required
def create_kit():
    db = g.db
    try:
        k = KitAssembly(name=request.form["name"], description=request.form.get("description", ""),
                        selling_price=float(request.form.get("selling_price", 0)))
        db.add(k); db.flush()
        part_ids = request.form.getlist("part_id[]")
        qtys = request.form.getlist("qty[]")
        for pid, q in zip(part_ids, qtys):
            if pid and q: db.add(KitItem(kit_id=k.id, part_id=int(pid), quantity=int(q)))
        db.commit()
        flash("Kit assembly created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/kits")


# ---- Part Supersession ----
@bp.route("/supersessions")
@login_required
def list_supersessions():
    db = g.db
    items = db.query(PartSupersession).order_by(PartSupersession.superseded_at.desc()).all()
    return render_template("inventory_advanced/supersessions.html", items=items, active_page="supersessions")


@bp.route("/supersessions/new", methods=["POST"])
@login_required
def create_supersession():
    db = g.db
    try:
        s = PartSupersession(old_part_id=int(request.form.get("old_part_id", 0)) or None,
                             new_part_id=int(request.form.get("new_part_id", 0)) or None,
                             old_part_number=request.form.get("old_part_number", ""),
                             new_part_number=request.form.get("new_part_number", ""),
                             notes=request.form.get("notes", ""))
        db.add(s); db.commit()
        flash("Supersession recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/supersessions")


# ---- Non-Stock Items ----
@bp.route("/non-stock")
@login_required
def list_non_stock():
    db = g.db
    items = db.query(NonStockItem).order_by(NonStockItem.name).all()
    return render_template("inventory_advanced/non_stock.html", items=items, active_page="non_stock")


@bp.route("/non-stock/new", methods=["POST"])
@login_required
def create_non_stock():
    db = g.db
    try:
        n = NonStockItem(name=request.form["name"], description=request.form.get("description", ""),
                         supplier=request.form.get("supplier", ""),
                         estimated_cost=float(request.form.get("estimated_cost", 0)),
                         selling_price=float(request.form.get("selling_price", 0)),
                         lead_days=int(request.form.get("lead_days", 7)),
                         notes=request.form.get("notes", ""))
        db.add(n); db.commit()
        flash("Non-stock item created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/non-stock")


# ---- Consignment ----
@bp.route("/consignment")
@login_required
def list_consignment():
    db = g.db
    items = db.query(ConsignmentItem).order_by(ConsignmentItem.supplier).all()
    return render_template("inventory_advanced/consignment.html", items=items, active_page="consignment")


@bp.route("/consignment/new", methods=["POST"])
@login_required
def create_consignment():
    db = g.db
    try:
        c = ConsignmentItem(part_id=int(request.form["part_id"]), supplier=request.form["supplier"],
                            quantity=int(request.form.get("quantity", 0)),
                            unit_cost=float(request.form.get("unit_cost", 0)))
        db.add(c); db.commit()
        flash("Consignment item added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/consignment")


# ---- Cycle Counts ----
@bp.route("/cycle-counts")
@login_required
def list_cycle_counts():
    db = g.db
    counts = db.query(CycleCount).order_by(CycleCount.count_date.desc()).all()
    return render_template("inventory_advanced/cycle_counts.html", counts=counts, active_page="cycle_counts")


@bp.route("/cycle-counts/new", methods=["POST"])
@login_required
def create_cycle_count():
    db = g.db
    try:
        part = db.query(Part).filter(Part.id == int(request.form["part_id"])).first()
        actual = int(request.form["actual_qty"])
        expected = part.quantity_on_hand if part else 0
        cc = CycleCount(part_id=int(request.form["part_id"]),
                        expected_qty=expected, actual_qty=actual,
                        variance=actual - expected,
                        count_date=date.fromisoformat(request.form["count_date"]) if request.form.get("count_date") else date.today(),
                        notes=request.form.get("notes", ""))
        db.add(cc)
        if part and request.form.get("adjust_stock") == "on":
            part.quantity_on_hand = actual
        db.commit()
        log_audit("cycle_count", "part", cc.part_id, f"Count: expected {expected}, actual {actual}")
        flash("Cycle count recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/cycle-counts")


# ---- Inventory Transfers ----
@bp.route("/transfers")
@login_required
def list_transfers():
    db = g.db
    transfers = db.query(InventoryTransfer).order_by(InventoryTransfer.created_at.desc()).all()
    return render_template("inventory_advanced/transfers.html", transfers=transfers, active_page="transfers")


@bp.route("/transfers/new", methods=["POST"])
@login_required
def create_transfer():
    db = g.db
    try:
        qty = int(request.form["quantity"])
        t = InventoryTransfer(part_id=int(request.form["part_id"]),
                              from_warehouse=request.form["from_warehouse"],
                              to_warehouse=request.form["to_warehouse"],
                              quantity=qty, notes=request.form.get("notes", ""))
        db.add(t); db.commit()
        log_audit("transfer", "part", t.part_id, f"Transferred {qty} units")
        flash("Inventory transfer recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/transfers")


# ---- Supplier Scorecards ----
@bp.route("/scorecards")
@login_required
def list_scorecards():
    db = g.db
    cards = db.query(SupplierScorecard).order_by(SupplierScorecard.rating_date.desc()).all()
    return render_template("inventory_advanced/scorecards.html", cards=cards, active_page="scorecards")


@bp.route("/scorecards/new", methods=["POST"])
@login_required
def create_scorecard():
    db = g.db
    try:
        ot = float(request.form.get("on_time_delivery_pct", 100))
        qa = float(request.form.get("quality_rating", 100))
        pr = float(request.form.get("pricing_rating", 100))
        s = SupplierScorecard(supplier_name=request.form["supplier_name"],
                              rating_date=date.fromisoformat(request.form["rating_date"]) if request.form.get("rating_date") else date.today(),
                              on_time_delivery_pct=ot, quality_rating=qa, pricing_rating=pr,
                              overall_score=(ot + qa + pr) / 3, notes=request.form.get("notes", ""))
        db.add(s); db.commit()
        flash("Scorecard created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/inv/scorecards")
