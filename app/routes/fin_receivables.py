"""Receivables: credit memos, deposits, AR aging, statements (same `finance` blueprint)."""
from flask import render_template, request, redirect, flash, g
import logging
from app.timeutils import utcnow
from app.models import CreditMemo, Invoice, CustomerDeposit, WorkOrder, Customer
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.finance import bp


# ---- Credit Memos ----
@bp.route("/credit-memos")
@login_required
def list_credit_memos():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(CreditMemo).order_by(CreditMemo.created_at.desc())
    p = paginate(query, page)
    return render_template("finance/credit_memos.html", items=p["rows"], p=p, active_page="credit_memos")


@bp.route("/credit-memos/new", methods=["POST"])
@login_required
def create_credit_memo():
    db = g.db
    try:
        count = db.query(CreditMemo).count() + 1
        cm = CreditMemo(memo_number=f"CM-{utcnow().strftime('%Y%m')}-{count:04d}",
                        invoice_id=int(request.form.get("invoice_id", 0)) or None,
                        customer_id=int(request.form["customer_id"]),
                        amount=float(request.form["amount"]),
                        reason=request.form.get("reason", ""))
        db.add(cm); db.commit()
        inv = db.query(Invoice).filter(Invoice.id == cm.invoice_id).first()
        if inv:
            inv.amount_paid -= cm.amount
            if inv.amount_paid < 0: inv.amount_paid = 0
            if inv.amount_paid <= 0: inv.status = "Unpaid"
            elif inv.amount_paid < inv.total_amount: inv.status = "Partial"
            db.commit()
        log_audit("create", "credit_memo", cm.id, f"Credit memo ${cm.amount:.2f}")
        flash("Credit memo issued", "success")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Error", "danger")
    return redirect("/finance/credit-memos")
# ---- Customer Deposits ----
@bp.route("/deposits")
@login_required
def list_deposits():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(CustomerDeposit).order_by(CustomerDeposit.created_at.desc())
    p = paginate(query, page)
    return render_template("finance/deposits.html", deposits=p["rows"], p=p, active_page="deposits")


@bp.route("/deposits/new", methods=["POST"])
@login_required
def create_deposit():
    db = g.db
    try:
        d = CustomerDeposit(customer_id=int(request.form["customer_id"]),
                            amount=float(request.form["amount"]),
                            balance=float(request.form["amount"]),
                            payment_method=request.form.get("payment_method", "Cash"),
                            reference=request.form.get("reference", ""),
                            notes=request.form.get("notes", ""))
        db.add(d); db.commit()
        log_audit("create", "deposit", d.id, f"Deposit ${d.amount:.2f}")
        flash("Deposit recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/deposits")
# ---- AR Aging Report ----
@bp.route("/ar-aging")
@login_required
def ar_aging():
    db = g.db
    now = utcnow()
    page = int(request.args.get("page", 1))
    query = db.query(Invoice).filter(Invoice.status.in_(["Unpaid", "Partial"])).order_by(Invoice.created_at)
    p = paginate(query, page)
    aging = {"0-30": [], "31-60": [], "61-90": [], "90+": []}
    for inv in p["rows"]:
        days = (now - inv.created_at).days
        row = {"inv": inv, "customer": inv.work_order.customer.name if inv.work_order and inv.work_order.customer else "N/A",
               "days": days, "total": inv.total_amount, "due": inv.total_amount - inv.amount_paid}
        if days <= 30: aging["0-30"].append(row)
        elif days <= 60: aging["31-60"].append(row)
        elif days <= 90: aging["61-90"].append(row)
        else: aging["90+"].append(row)
    totals = {k: sum(r["due"] for r in v) for k, v in aging.items()}
    return render_template("finance/ar_aging.html", aging=aging, totals=totals, p=p, active_page="ar_aging")
# ---- Customer Statements ----
@bp.route("/customer-statements")
@login_required
def customer_statements():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(Customer).order_by(Customer.name)
    p = paginate(query, page)
    return render_template("finance/statements.html", customers=p["rows"], p=p, active_page="statements")


@bp.route("/customer-statements/<int:cid>")
@login_required
def view_statement(cid):
    db = g.db
    customer = db.query(Customer).filter(Customer.id == cid).first()
    if not customer: return redirect("/finance/customer-statements")
    page = int(request.args.get("page", 1))
    query = db.query(Invoice).join(WorkOrder).filter(
        WorkOrder.customer_id == cid,
        Invoice.status.in_(["Unpaid", "Partial"])
    ).order_by(Invoice.created_at)
    p = paginate(query, page)
    total_due = sum(inv.total_amount - inv.amount_paid for inv in p["rows"])
    return render_template("finance/statement_detail.html", customer=customer,
                           invoices=p["rows"], p=p, total_due=total_due, active_page="statements")
