from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from app.models import Communication, Customer, Lead
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("communications", __name__, url_prefix="/communications")


@bp.route("", methods=["GET"])
@login_required
def list_communications():
    db = g.db
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    q = db.query(Communication)
    if search:
        q = q.filter(Communication.subject.ilike(f"%{search}%") | Communication.body.ilike(f"%{search}%"))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(q.order_by(Communication.created_at.desc()), page, per_page)
    return render_template("communications/list.html", p=p,
                           search=search, active_page="communications", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_comm_form():
    db = g.db
    return render_template("communications/form.html", comm=None,
                           customers=db.query(Customer).order_by(Customer.name).all(),
                           leads=db.query(Lead).order_by(Lead.name).all(),
                           active_page="communications")


@bp.route("/new", methods=["POST"])
@login_required
def create_communication():
    db = g.db
    try:
        cid = int(request.form.get("customer_id", 0)) or None
        lid = int(request.form.get("lead_id", 0)) or None
        if not cid and not lid:
            flash("Select a customer or lead", "warning")
            return redirect("/communications/new")
        c = Communication(customer_id=cid, lead_id=lid, comm_type=request.form["comm_type"],
                          subject=request.form["subject"], body=request.form.get("body", ""),
                          direction=request.form.get("direction", "Outbound"))
        db.add(c)
        db.commit()
        flash("Communication logged", "success")
        return redirect("/communications")
    except Exception as e:
        db.rollback()
        logging.exception("Error in communications")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/communications/new")
