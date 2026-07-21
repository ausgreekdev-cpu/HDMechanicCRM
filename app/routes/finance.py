from flask import Blueprint, render_template, request, redirect, flash, Response, jsonify, g
import logging, csv, io
from datetime import datetime, date, timedelta
from app.models import CreditMemo, Invoice, CustomerDeposit, Expense, WorkOrder, Budget, LateFeeRule, BankAccount, BankTransaction, Contractor1099, TaxExemption, Customer, WorkOrder, ScrapPickup, Payment
from app.auth import login_required, role_required
from app.audit import log_audit
from app.helpers import paginate
from app.export import export_csv
from sqlalchemy import func

bp = Blueprint("finance", __name__, url_prefix="/finance")


# ---- Credit Memos ----
@bp.route("/credit-memos")
@login_required
def list_credit_memos():
    db = g.db
    items = db.query(CreditMemo).order_by(CreditMemo.created_at.desc()).all()
    return render_template("finance/credit_memos.html", items=items, active_page="credit_memos")


@bp.route("/credit-memos/new", methods=["POST"])
@login_required
def create_credit_memo():
    db = g.db
    try:
        count = db.query(CreditMemo).count() + 1
        cm = CreditMemo(memo_number=f"CM-{datetime.utcnow().strftime('%Y%m')}-{count:04d}",
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
    deposits = db.query(CustomerDeposit).order_by(CustomerDeposit.created_at.desc()).all()
    return render_template("finance/deposits.html", deposits=deposits, active_page="deposits")


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
    now = datetime.utcnow()
    invoices = db.query(Invoice).filter(Invoice.status.in_(["Unpaid", "Partial"])).order_by(Invoice.created_at).all()
    aging = {"0-30": [], "31-60": [], "61-90": [], "90+": []}
    for inv in invoices:
        days = (now - inv.created_at).days
        row = {"inv": inv, "customer": inv.work_order.customer.name if inv.work_order and inv.work_order.customer else "N/A",
               "days": days, "total": inv.total_amount, "due": inv.total_amount - inv.amount_paid}
        if days <= 30: aging["0-30"].append(row)
        elif days <= 60: aging["31-60"].append(row)
        elif days <= 90: aging["61-90"].append(row)
        else: aging["90+"].append(row)
    totals = {k: sum(r["due"] for r in v) for k, v in aging.items()}
    return render_template("finance/ar_aging.html", aging=aging, totals=totals, active_page="ar_aging")


# ---- Expenses ----
@bp.route("/expenses")
@login_required
def list_expenses():
    db = g.db
    page = int(request.args.get("page", 1))
    q = db.query(Expense).order_by(Expense.expense_date.desc())
    p = paginate(q, page, 50)
    total = db.query(func.sum(Expense.amount)).scalar() or 0
    return render_template("finance/expenses.html", p=p, total=total, active_page="expenses")


@bp.route("/expenses/new", methods=["POST"])
@login_required
def create_expense():
    db = g.db
    try:
        e = Expense(work_order_id=int(request.form.get("work_order_id", 0)) or None,
                    category=request.form["category"], amount=float(request.form["amount"]),
                    expense_date=date.fromisoformat(request.form["expense_date"]),
                    vendor=request.form.get("vendor", ""), description=request.form.get("description", ""),
                    notes=request.form.get("notes", ""))
        db.add(e); db.commit()
        log_audit("create", "expense", e.id, f"Expense ${e.amount:.2f} - {e.category}")
        flash("Expense recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/expenses")


# ---- Job Costing ----
@bp.route("/job-costing")
@login_required
def job_costing():
    db = g.db
    from sqlalchemy import func
    wos = db.query(WorkOrder).filter(WorkOrder.status.in_(["Completed", "Invoiced"])).order_by(WorkOrder.updated_at.desc()).limit(100).all()
    results = []
    for wo in wos:
        parts_cost = wo.parts_total
        labor_cost = wo.labor_hours * wo.labor_rate
        expenses = db.query(func.sum(Expense.amount)).filter(Expense.work_order_id == wo.id).scalar() or 0
        total_cost = parts_cost + labor_cost + expenses
        revenue = wo.total_amount
        results.append({"wo": wo, "parts_cost": parts_cost, "labor_cost": labor_cost,
                       "expenses": expenses, "total_cost": total_cost, "revenue": revenue,
                       "profit": revenue - total_cost, "margin_pct": ((revenue - total_cost) / revenue * 100) if revenue else 0})
    return render_template("finance/job_costing.html", results=results, active_page="job_costing")


# ---- Budget vs Actual ----
@bp.route("/budgets")
@login_required
def list_budgets():
    db = g.db
    year = int(request.args.get("year", datetime.utcnow().year))
    budgets = db.query(Budget).filter(Budget.year == year).order_by(Budget.category).all()
    revenue = db.query(func.sum(WorkOrder.total_amount)).filter(
        func.strftime("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).scalar() or 0
    expenses = db.query(func.sum(Expense.amount)).filter(
        func.strftime("%Y", Expense.expense_date) == str(year)).scalar() or 0
    return render_template("finance/budgets.html", budgets=budgets, year=year,
                           revenue=revenue, expenses=expenses, active_page="budgets")


@bp.route("/budgets/new", methods=["POST"])
@login_required
def create_budget():
    db = g.db
    try:
        b = Budget(year=int(request.form["year"]), month=int(request.form.get("month", 0)) or None,
                   category=request.form.get("category", ""),
                   budgeted_amount=float(request.form.get("budgeted_amount", 0)),
                   notes=request.form.get("notes", ""))
        db.add(b); db.commit()
        flash("Budget entry created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/finance/budgets")


# ---- Late Fees ----
@bp.route("/late-fee-rules")
@login_required
def list_late_fee_rules():
    db = g.db
    rules = db.query(LateFeeRule).order_by(LateFeeRule.name).all()
    return render_template("finance/late_fee_rules.html", rules=rules, active_page="late_fee_rules")


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
        now = datetime.utcnow()
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


# ---- Bank Reconciliation ----
@bp.route("/bank-accounts")
@login_required
def list_bank_accounts():
    db = g.db
    accounts = db.query(BankAccount).order_by(BankAccount.name).all()
    return render_template("finance/bank_accounts.html", accounts=accounts, active_page="bank_accounts")


@bp.route("/bank-accounts/<int:aid>/transactions")
@login_required
def list_bank_transactions(aid):
    db = g.db
    account = db.query(BankAccount).filter(BankAccount.id == aid).first()
    if not account: return redirect("/finance/bank-accounts")
    txns = db.query(BankTransaction).filter(BankTransaction.account_id == aid).order_by(BankTransaction.transaction_date.desc()).all()
    return render_template("finance/bank_transactions.html", account=account, txns=txns, active_page="bank_accounts")


@bp.route("/bank-accounts/<int:aid>/transactions/new", methods=["POST"])
@login_required
def create_bank_transaction(aid):
    db = g.db
    try:
        t = BankTransaction(account_id=aid,
                            transaction_date=date.fromisoformat(request.form["transaction_date"]),
                            description=request.form.get("description", ""),
                            amount=float(request.form["amount"]),
                            transaction_type=request.form.get("transaction_type", "Deposit"),
                            reference=request.form.get("reference", ""),
                            notes=request.form.get("notes", ""))
        db.add(t)
        acct = db.query(BankAccount).filter(BankAccount.id == aid).first()
        if acct: acct.balance += t.amount if t.transaction_type == "Deposit" else -t.amount
        db.commit()
        flash("Transaction recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect(f"/finance/bank-accounts/{aid}/transactions")


@bp.route("/bank-accounts/<int:aid>/reconcile", methods=["POST"])
@login_required
def reconcile_bank(aid):
    db = g.db
    try:
        txn_ids = request.form.getlist("txn_ids")
        for tid in txn_ids:
            t = db.query(BankTransaction).filter(BankTransaction.id == int(tid)).first()
            if t: t.reconciled = True
        db.commit()
        flash(f"Reconciled {len(txn_ids)} transactions", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect(f"/finance/bank-accounts/{aid}/transactions")


# ---- 1099 Contractors ----
@bp.route("/contractors")
@login_required
def list_contractors():
    db = g.db
    contractors = db.query(Contractor1099).order_by(Contractor1099.name).all()
    return render_template("finance/contractors.html", contractors=contractors, active_page="contractors")


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
    items = db.query(TaxExemption).order_by(TaxExemption.customer_id).all()
    return render_template("finance/tax_exemptions.html", items=items, active_page="tax_exemptions")


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


# ---- Revenue by Category ----
@bp.route("/revenue-by-category")
@login_required
def revenue_by_category():
    db = g.db
    from sqlalchemy import func
    year = int(request.args.get("year", datetime.utcnow().year))
    revenue = db.query(func.sum(WorkOrder.total_amount)).filter(
        func.strftime("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).scalar() or 0
    scrap = db.query(func.sum(ScrapPickup.total_payout)).filter(
        func.strftime("%Y", ScrapPickup.pickup_date) == str(year)).scalar() or 0
    wo_count = db.query(WorkOrder).filter(
        func.strftime("%Y", WorkOrder.updated_at) == str(year),
        WorkOrder.status.in_(["Completed", "Invoiced"])).count() or 0
    return render_template("finance/revenue_categories.html", year=year,
                           revenue=revenue, scrap=scrap, wo_count=wo_count, active_page="revenue_categories")


# ---- Customer Statements ----
@bp.route("/customer-statements")
@login_required
def customer_statements():
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    return render_template("finance/statements.html", customers=customers, active_page="statements")


@bp.route("/customer-statements/<int:cid>")
@login_required
def view_statement(cid):
    db = g.db
    customer = db.query(Customer).filter(Customer.id == cid).first()
    if not customer: return redirect("/finance/customer-statements")
    invoices = db.query(Invoice).join(WorkOrder).filter(
        WorkOrder.customer_id == cid,
        Invoice.status.in_(["Unpaid", "Partial"])
    ).order_by(Invoice.created_at).all()
    total_due = sum(inv.total_amount - inv.amount_paid for inv in invoices)
    return render_template("finance/statement_detail.html", customer=customer,
                           invoices=invoices, total_due=total_due, active_page="statements")
