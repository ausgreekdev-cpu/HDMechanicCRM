"""Bank reconciliation (same `finance` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date
from app.models import BankAccount, BankTransaction
from app.auth import login_required
from app.helpers import paginate
from app.routes.finance import bp


# ---- Bank Reconciliation ----
@bp.route("/bank-accounts")
@login_required
def list_bank_accounts():
    db = g.db
    page = int(request.args.get("page", 1))
    query = db.query(BankAccount).order_by(BankAccount.name)
    p = paginate(query, page)
    return render_template("finance/bank_accounts.html", accounts=p["rows"], p=p, active_page="bank_accounts")


@bp.route("/bank-accounts/<int:aid>/transactions")
@login_required
def list_bank_transactions(aid):
    db = g.db
    account = db.query(BankAccount).filter(BankAccount.id == aid).first()
    if not account: return redirect("/finance/bank-accounts")
    page = int(request.args.get("page", 1))
    query = db.query(BankTransaction).filter(BankTransaction.account_id == aid).order_by(BankTransaction.transaction_date.desc())
    p = paginate(query, page)
    return render_template("finance/bank_transactions.html", account=account, txns=p["rows"], p=p, active_page="bank_accounts")


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
