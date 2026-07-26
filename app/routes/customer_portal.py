import os, secrets, logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, flash, g, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Customer, Vehicle, WorkOrder, Invoice, CustomerPortalUser, CustomerPortalToken, CustomerPortalMessage
from app.auth import login_required, admin_required
from app.audit import log_audit

bp = Blueprint("customer_portal", __name__, url_prefix="/portal")


def _get_portal_user():
    pid = session.get("portal_user_id")
    if not pid:
        return None
    return g.db.query(CustomerPortalUser).filter(
        CustomerPortalUser.id == pid, CustomerPortalUser.is_active == True
    ).first()


def portal_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _get_portal_user():
            flash("Please log in to access the portal", "warning")
            return redirect("/portal/login")
        return f(*args, **kwargs)
    return decorated


# ─── Customer Portal Auth ───

@bp.route("/login", methods=["GET", "POST"])
def portal_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        db = g.db
        user = db.query(CustomerPortalUser).filter(
            CustomerPortalUser.email == email, CustomerPortalUser.is_active == True
        ).first()
        if user and check_password_hash(user.password_hash, password):
            session["portal_user_id"] = user.id
            user.last_login = datetime.utcnow()
            db.commit()
            return redirect("/portal/dashboard")
        flash("Invalid email or password", "danger")
    return render_template("portal/login.html")


@bp.route("/token-login/<token>")
def portal_token_login(token):
    db = g.db
    pt = db.query(CustomerPortalToken).filter(
        CustomerPortalToken.token == token,
        CustomerPortalToken.is_used == False,
        CustomerPortalToken.expires_at > datetime.utcnow()
    ).first()
    if not pt:
        flash("Invalid or expired link", "danger")
        return redirect("/portal/login")
    pt.is_used = True
    session["portal_user_id"] = pt.portal_user.id
    pt.portal_user.last_login = datetime.utcnow()
    db.commit()
    flash("Welcome to your portal!", "success")
    return redirect("/portal/dashboard")


@bp.route("/logout")
def portal_logout():
    session.pop("portal_user_id", None)
    return redirect("/portal/login")


# ─── Customer Portal Pages ───

@bp.route("/dashboard")
@portal_login_required
def dashboard():
    db = g.db
    user = _get_portal_user()
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    vehicles = db.query(Vehicle).filter(Vehicle.customer_id == customer.id).all() if customer else []
    recent_wos = []
    invoices = []
    if customer:
        recent_wos = db.query(WorkOrder).filter(WorkOrder.customer_id == customer.id).order_by(WorkOrder.created_at.desc()).limit(5).all()
        invoice_ids = [wo.id for wo in db.query(WorkOrder).filter(WorkOrder.customer_id == customer.id).all()]
        invoices = db.query(Invoice).filter(Invoice.work_order_id.in_(invoice_ids)).order_by(Invoice.created_at.desc()).limit(5).all() if invoice_ids else []
    unread = db.query(CustomerPortalMessage).filter(
        CustomerPortalMessage.portal_user_id == user.id,
        CustomerPortalMessage.direction == "shop",
        CustomerPortalMessage.is_read == False
    ).count()
    return render_template("portal/dashboard.html", customer=customer, vehicles=vehicles,
                           recent_wos=recent_wos, invoices=invoices, unread_messages=unread)


@bp.route("/vehicles")
@portal_login_required
def vehicles():
    db = g.db
    user = _get_portal_user()
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    vehicle_list = db.query(Vehicle).filter(Vehicle.customer_id == customer.id).order_by(Vehicle.make).all() if customer else []
    return render_template("portal/vehicles.html", vehicles=vehicle_list, customer=customer)


@bp.route("/work-orders")
@portal_login_required
def work_orders():
    db = g.db
    user = _get_portal_user()
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    wos = []
    if customer:
        wos = db.query(WorkOrder).filter(WorkOrder.customer_id == customer.id).order_by(WorkOrder.created_at.desc()).all()
    return render_template("portal/work_orders.html", work_orders=wos, customer=customer)


@bp.route("/invoices")
@portal_login_required
def invoices():
    db = g.db
    user = _get_portal_user()
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    invoice_list = []
    if customer:
        wo_ids = [wo.id for wo in db.query(WorkOrder).filter(WorkOrder.customer_id == customer.id).all()]
        invoice_list = db.query(Invoice).filter(Invoice.work_order_id.in_(wo_ids)).order_by(Invoice.created_at.desc()).all() if wo_ids else []
    return render_template("portal/invoices.html", invoices=invoice_list, customer=customer)


@bp.route("/messages", methods=["GET", "POST"])
@portal_login_required
def messages():
    db = g.db
    user = _get_portal_user()
    if request.method == "POST":
        subject = request.form.get("subject", "Portal Message")
        body = request.form.get("body", "").strip()
        if body:
            msg = CustomerPortalMessage(portal_user_id=user.id, subject=subject, body=body, direction="customer")
            db.add(msg)
            db.commit()
            flash("Message sent to the shop", "success")
        return redirect("/portal/messages")
    db.query(CustomerPortalMessage).filter(
        CustomerPortalMessage.portal_user_id == user.id,
        CustomerPortalMessage.direction == "shop",
        CustomerPortalMessage.is_read == False
    ).update({"is_read": True})
    db.commit()
    all_msgs = db.query(CustomerPortalMessage).filter(
        CustomerPortalMessage.portal_user_id == user.id
    ).order_by(CustomerPortalMessage.created_at.desc()).all()
    return render_template("portal/messages.html", messages=all_msgs)


@bp.route("/request-service", methods=["GET", "POST"])
@portal_login_required
def request_service():
    db = g.db
    user = _get_portal_user()
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    vehicles = db.query(Vehicle).filter(Vehicle.customer_id == customer.id).all() if customer else []
    if request.method == "POST":
        msg = CustomerPortalMessage(
            portal_user_id=user.id,
            subject="Service Request",
            body=f"Vehicle: {request.form.get('vehicle_info', '')}\n"
                 f"Service Needed: {request.form.get('service_type', '')}\n"
                 f"Preferred Date: {request.form.get('preferred_date', '')}\n"
                 f"Details: {request.form.get('details', '')}",
            direction="customer"
        )
        db.add(msg)
        db.commit()
        flash("Service request submitted. We'll contact you to confirm.", "success")
        return redirect("/portal/dashboard")
    return render_template("portal/request_service.html", customer=customer, vehicles=vehicles)


# ─── Admin Routes ───

@bp.route("/admin/invite", methods=["GET", "POST"])
@login_required
@admin_required
def admin_invite():
    db = g.db
    if request.method == "POST":
        customer_id = int(request.form["customer_id"])
        email = request.form.get("email", "").strip()
        password = request.form.get("temp_password", "portal123")
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            flash("Customer not found", "danger")
            return redirect("/portal/admin/invite")
        existing = db.query(CustomerPortalUser).filter(
            CustomerPortalUser.customer_id == customer_id
        ).first()
        if existing:
            token = secrets.token_hex(32)
            pt = CustomerPortalToken(portal_user_id=existing.id, token=token,
                                     expires_at=datetime.utcnow() + timedelta(days=7))
            db.add(pt)
            db.commit()
            log_audit("invite", "portal", existing.id, f"Sent portal invite to {email}")
            flash(f"Invite link: /portal/token-login/{token}", "success")
            return redirect("/portal/admin/customers")
        pu = CustomerPortalUser(customer_id=customer_id, email=email or customer.email,
                                password_hash=generate_password_hash(password),
                                display_name=customer.name)
        db.add(pu)
        db.flush()
        token = secrets.token_hex(32)
        pt = CustomerPortalToken(portal_user_id=pu.id, token=token,
                                 expires_at=datetime.utcnow() + timedelta(days=7))
        db.add(pt)
        db.commit()
        log_audit("create", "portal_user", pu.id, f"Created portal user for {customer.name}")
        flash(f"Portal access created. Invite link: /portal/token-login/{token}", "success")
        return redirect("/portal/admin/customers")
    customers = db.query(Customer).order_by(Customer.name).all()
    return render_template("portal/admin_invite.html", customers=customers)


@bp.route("/admin/customers")
@login_required
@admin_required
def admin_customers():
    db = g.db
    users = db.query(CustomerPortalUser).order_by(CustomerPortalUser.created_at.desc()).all()
    return render_template("portal/admin_customers.html", portal_users=users)


@bp.route("/admin/message/<int:msg_id>/reply", methods=["POST"])
@login_required
@admin_required
def admin_reply(msg_id):
    db = g.db
    msg = db.query(CustomerPortalMessage).filter(CustomerPortalMessage.id == msg_id).first()
    if msg:
        body = request.form.get("reply", "").strip()
        if body:
            reply = CustomerPortalMessage(
                portal_user_id=msg.portal_user_id, subject=f"Re: {msg.subject}",
                body=body, direction="shop"
            )
            db.add(reply)
            db.commit()
            flash("Reply sent", "success")
    return redirect("/portal/admin/customers")
