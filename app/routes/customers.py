from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from app.models import Customer
from app.auth import login_required
from app.helpers import paginate
from app.audit import log_audit
import urllib.parse

bp = Blueprint("customers", __name__, url_prefix="/customers")


@bp.route("", methods=["GET"])
@login_required
def list_customers():
    db = g.db
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    query = db.query(Customer)
    if search:
        query = query.filter(
            Customer.name.ilike(f"%{search}%") | Customer.company.ilike(f"%{search}%") |
            Customer.phone.ilike(f"%{search}%") | Customer.email.ilike(f"%{search}%")
        )
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(query.order_by(Customer.name), page, per_page)
    return render_template("customers/list.html", p=p, search=search, active_page="customers", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_customer_form():
    return render_template("customers/form.html", customer=None, active_page="customers")


@bp.route("/new", methods=["POST"])
@login_required
def create_customer():
    db = g.db
    try:
        c = Customer(name=request.form["name"], company=request.form.get("company", ""),
                     phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                     address=request.form.get("address", ""), notes=request.form.get("notes", ""))
        db.add(c)
        db.commit()
        log_audit("create", "customer", c.id, f"Created customer {c.name}")
        flash("Customer created", "success")
        return redirect(f"/customers/{c.id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in customers")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/customers/new")


@bp.route("/<int:customer_id>", methods=["GET"])
@login_required
def view_customer(customer_id):
    db = g.db
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        flash("Customer not found", "warning")
        return redirect("/customers")
    return render_template("customers/detail.html", customer=customer, active_page="customers")


@bp.route("/<int:customer_id>/edit", methods=["GET"])
@login_required
def edit_customer_form(customer_id):
    db = g.db
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return redirect("/customers")
    return render_template("customers/form.html", customer=customer, active_page="customers")


@bp.route("/<int:customer_id>/edit", methods=["POST"])
@login_required
def update_customer(customer_id):
    db = g.db
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if c:
            c.name = request.form["name"]
            c.company = request.form.get("company", "")
            c.phone = request.form.get("phone", "")
            c.email = request.form.get("email", "")
            c.address = request.form.get("address", "")
            c.notes = request.form.get("notes", "")
            db.commit()
            log_audit("update", "customer", customer_id, f"Updated customer {c.name}")
            flash("Customer updated", "success")
        return redirect(f"/customers/{customer_id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in customers")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/customers/{customer_id}/edit")


@bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete_customer(customer_id):
    db = g.db
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if c:
            log_audit("delete", "customer", customer_id, f"Deleted customer {c.name}")
            db.delete(c)
            db.commit()
            flash("Customer deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete customer failed")
        flash("Cannot delete: customer is linked to existing records", "danger")
    return redirect("/customers")
