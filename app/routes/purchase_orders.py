from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import date, datetime
from app.models import PurchaseOrder, PurchaseOrderItem, Part, PartTransaction
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("purchase_orders", __name__, url_prefix="/purchase-orders")


@bp.route("", methods=["GET"])
@login_required
def list_pos():
    db = g.db
    status = request.args.get("status", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(PurchaseOrder.order_date.desc()), page, per_page)
    return render_template("purchase_orders/list.html", p=p,
                           status=status, active_page="purchase_orders", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_po_form():
    db = g.db
    suppliers = [r[0] for r in db.query(Part.supplier).filter(Part.supplier != None, Part.supplier != "").distinct().all()]
    parts = db.query(Part).order_by(Part.name).all()
    return render_template("purchase_orders/form.html", po=None, suppliers=suppliers, parts=parts,
                           active_page="purchase_orders")


@bp.route("/new", methods=["POST"])
@login_required
def create_po():
    db = g.db
    try:
        count = db.query(PurchaseOrder).count() + 1
        po = PurchaseOrder(
            po_number=f"PO-{datetime.now().strftime('%Y%m')}-{count:04d}",
            supplier=request.form["supplier"],
            status="Pending",
            order_date=date.fromisoformat(request.form["order_date"]),
            notes=request.form.get("notes", ""),
        )
        db.add(po)
        db.flush()
        part_ids = request.form.getlist("part_id[]")
        qtys = request.form.getlist("qty[]")
        costs = request.form.getlist("cost[]")
        for pid, qty, cost in zip(part_ids, qtys, costs):
            if pid and qty:
                part = db.query(Part).filter(Part.id == int(pid)).first()
                q = int(qty)
                c = float(cost or 0)
                item = PurchaseOrderItem(
                    purchase_order_id=po.id, part_id=int(pid),
                    part_name=part.name if part else "", part_number=part.part_number if part else "",
                    quantity_ordered=q, unit_cost=c, total_cost=q * c
                )
                db.add(item)
        db.commit()
        flash(f"Purchase order {po.po_number} created", "success")
        return redirect("/purchase-orders")
    except Exception:
        db.rollback()
        logging.exception("Error creating PO")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/purchase-orders/new")


@bp.route("/<int:po_id>", methods=["GET"])
@login_required
def view_po(po_id):
    db = g.db
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        flash("Purchase order not found", "warning")
        return redirect("/purchase-orders")
    return render_template("purchase_orders/detail.html", po=po, active_page="purchase_orders")


@bp.route("/<int:po_id>/receive", methods=["POST"])
@login_required
def receive_po(po_id):
    db = g.db
    try:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            flash("Purchase order not found", "warning")
            return redirect("/purchase-orders")
        item_ids = request.form.getlist("item_id[]")
        received = request.form.getlist("received[]")
        all_received = True
        for iid, r in zip(item_ids, received):
            item = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.id == int(iid)).first()
            if item:
                qty = int(r or 0)
                item.quantity_received += qty
                if item.quantity_received > item.quantity_ordered:
                    item.quantity_received = item.quantity_ordered
                if item.part_id:
                    part = db.query(Part).filter(Part.id == item.part_id).first()
                    if part:
                        part.quantity_on_hand += qty
                        db.add(PartTransaction(
                            part_id=item.part_id, quantity_change=qty,
                            transaction_type="Purchase", reference=po.po_number
                        ))
                if item.quantity_received < item.quantity_ordered:
                    all_received = False
        po.status = "Received" if all_received else "Partial"
        po.received_date = date.today()
        db.commit()
        flash("Receiving recorded", "success")
        return redirect(f"/purchase-orders/{po_id}")
    except Exception:
        db.rollback()
        logging.exception("Error receiving PO")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/purchase-orders/{po_id}")
