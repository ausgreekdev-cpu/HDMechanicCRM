from flask import Blueprint, render_template, request, redirect, flash, jsonify, g
import logging
from datetime import datetime
from app.models import Invoice, Payment, WorkOrder, Customer
from app.auth import login_required
from app.helpers import paginate
from app.audit import log_audit
from app.notifications import notify_invoice_created, notify_invoice_paid
import urllib.parse

bp = Blueprint("invoices", __name__, url_prefix="/invoices")


@bp.route("", methods=["GET"])
@login_required
def list_invoices():
    db = g.db
    status = request.args.get("status", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(Invoice)
    if status:
        q = q.filter(Invoice.status == status)
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(Invoice.created_at.desc()), page, per_page)
    return render_template("invoices/list.html", p=p,
                           status=status, active_page="invoices", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_invoice_form():
    db = g.db
    wos = db.query(WorkOrder).filter(WorkOrder.status.in_(["Completed", "Invoiced"])
                                     ).order_by(WorkOrder.created_at.desc()).all()
    return render_template("invoices/form.html", invoice=None, work_orders=wos, active_page="invoices")


@bp.route("/new", methods=["POST"])
@login_required
def create_invoice():
    db = g.db
    try:
        wo = db.query(WorkOrder).filter(WorkOrder.id == int(request.form["work_order_id"])).first()
        if wo:
            subtotal = wo.total_amount
            tax_rate = float(request.form.get("tax_rate", 0))
            tax_amount = subtotal * (tax_rate / 100)
            total = subtotal + tax_amount
            count = db.query(Invoice).count() + 1
            inv = Invoice(work_order_id=wo.id,
                          invoice_number=f"INV-{datetime.now().strftime('%Y%m')}-{count:04d}",
                          subtotal=subtotal, tax_rate=tax_rate, tax_amount=tax_amount,
                          total_amount=total, notes=request.form.get("notes", ""))
            db.add(inv)
            wo.status = "Invoiced"
            db.commit()
            log_audit("create", "invoice", inv.id, f"Created invoice {inv.invoice_number}")
            customer_email = wo.customer.email if wo.customer else None
            notify_invoice_created(inv, customer_email)
            flash("Invoice created", "success")
            return redirect(f"/invoices/{inv.id}")
        flash("Work order not found", "warning")
        return redirect("/invoices/new")
    except Exception as e:
        db.rollback()
        logging.exception("Error in invoices")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/invoices/new")


@bp.route("/<int:inv_id>", methods=["GET"])
@login_required
def view_invoice(inv_id):
    db = g.db
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        flash("Invoice not found", "warning")
        return redirect("/invoices")
    payments = db.query(Payment).filter(Payment.invoice_id == inv_id).order_by(Payment.paid_at.desc()).all()
    balance = inv.total_amount - inv.amount_paid
    return render_template("invoices/detail.html", inv=inv, payments=payments,
                           balance=balance, active_page="invoices")


@bp.route("/<int:inv_id>/pay", methods=["POST"])
@login_required
def mark_paid(inv_id):
    db = g.db
    try:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if inv:
            amount = float(request.form.get("amount", inv.total_amount - inv.amount_paid))
            method = request.form.get("payment_method", "Cash")
            ref = request.form.get("reference", "")
            pmt = Payment(invoice_id=inv_id, amount=amount, payment_method=method,
                          reference=ref, notes=request.form.get("notes", ""))
            db.add(pmt)
            inv.amount_paid += amount
            inv.paid_at = datetime.now()
            if inv.amount_paid >= inv.total_amount:
                inv.status = "Paid"
            else:
                inv.status = "Partial"
            db.commit()
            log_audit("payment", "invoice", inv_id, f"${amount:.2f} via {method}")
            customer_email = inv.work_order.customer.email if inv.work_order and inv.work_order.customer else None
            notify_invoice_paid(inv, customer_email)
            flash(f"Payment of ${amount:.2f} recorded", "success")
        return redirect(f"/invoices/{inv_id}")
    except Exception:
        db.rollback()
        logging.exception("Error recording payment")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/invoices/{inv_id}")


@bp.route("/<int:inv_id>/payments", methods=["GET"])
@login_required
def list_payments(inv_id):
    db = g.db
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        return redirect("/invoices")
    payments = db.query(Payment).filter(Payment.invoice_id == inv_id).order_by(Payment.paid_at.desc()).all()
    return render_template("invoices/payments.html", inv=inv, payments=payments, active_page="invoices")
