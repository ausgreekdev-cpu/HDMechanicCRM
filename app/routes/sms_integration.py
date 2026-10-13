import os, logging
from datetime import datetime
from app.timeutils import utcnow
from flask import Blueprint, render_template, request, redirect, flash, g, jsonify
from app.models import SMSMessage, SMSTemplate, SMSQueue, Customer
from app.auth import login_required, admin_required
from app.helpers import paginate
from app.audit import log_audit
from app import limiter

bp = Blueprint("sms_integration", __name__, url_prefix="/sms")


def send_sms(to_number, body):
    twilio_sid = os.environ.get("CRM_TWILIO_SID", "")
    twilio_auth = os.environ.get("CRM_TWILIO_AUTH", "")
    from_number = os.environ.get("CRM_TWILIO_PHONE", "")
    if not all([twilio_sid, twilio_auth, from_number]):
        logging.info("Twilio not configured — SMS logged only: %s -> %s", to_number, body[:80])
        return None
    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_auth)
        message = client.messages.create(body=body, from_=from_number, to=to_number)
        return message.sid
    except Exception:
        logging.exception("Twilio send failed")
        return None


def _get_or_create_portal_user_by_phone(db, phone):
    customer = db.query(Customer).filter(Customer.phone.ilike(f"%{phone}%")).first()
    if customer:
        from app.models import CustomerPortalUser
        return customer, db.query(CustomerPortalUser).filter(CustomerPortalUser.customer_id == customer.id).first()
    return None, None


@bp.route("/send", methods=["GET", "POST"])
@login_required
@limiter.limit("20/minute")
def send():
    db = g.db
    if request.method == "POST":
        to_number = request.form.get("to_number", "").strip()
        body = request.form.get("body", "").strip()
        if not to_number or not body:
            flash("Recipient and message are required", "danger")
            return redirect("/sms/send")
        external_id = send_sms(to_number, body)
        status = "sent" if external_id else "logged"
        sms = SMSMessage(to_number=to_number, from_number=os.environ.get("CRM_TWILIO_PHONE", ""),
                         body=body, status=status, direction="outbound", external_id=external_id,
                         sent_at=utcnow() if external_id else None)
        db.add(sms)
        db.commit()
        log_audit("send", "sms", sms.id, f"SMS to {to_number}")
        flash(f"SMS {status}", "success")
        return redirect("/sms/log")
    customers = db.query(Customer).filter(Customer.phone != None, Customer.phone != "").order_by(Customer.name).all()
    return render_template("sms/send.html", customers=customers, active_page="sms")


@bp.route("/send-bulk", methods=["GET", "POST"])
@login_required
@limiter.limit("5/minute")
def send_bulk():
    db = g.db
    if request.method == "POST":
        numbers = request.form.get("numbers", "").strip().split("\n")
        body = request.form.get("body", "").strip()
        template_id = request.form.get("template_id", "")
        if template_id:
            tmpl = db.query(SMSTemplate).filter(SMSTemplate.id == int(template_id)).first()
            if tmpl:
                body = tmpl.body_template
        if not body:
            flash("Message body is required", "danger")
            return redirect("/sms/send-bulk")
        count = 0
        for num in numbers:
            num = num.strip()
            if num:
                external_id = send_sms(num, body)
                status = "sent" if external_id else "logged"
                sms = SMSMessage(to_number=num, from_number=os.environ.get("CRM_TWILIO_PHONE", ""),
                                 body=body, status=status, direction="outbound", external_id=external_id,
                                 sent_at=utcnow() if external_id else None)
                db.add(sms)
                count += 1
        db.commit()
        flash(f"Bulk SMS: {count} messages {('sent' if os.environ.get('CRM_TWILIO_SID') else 'logged')}", "success")
        return redirect("/sms/log")
    templates = db.query(SMSTemplate).filter(SMSTemplate.is_active == True).all()
    return render_template("sms/send_bulk.html", templates=templates, active_page="sms")


@bp.route("/templates", methods=["GET", "POST"])
@login_required
def templates_list():
    db = g.db
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        body_template = request.form.get("body_template", "").strip()
        category = request.form.get("category", "General")
        if name and body_template:
            tmpl = SMSTemplate(name=name, body_template=body_template, category=category)
            db.add(tmpl)
            db.commit()
            log_audit("create", "sms_template", tmpl.id, f"Created SMS template {name}")
            flash("Template created", "success")
        return redirect("/sms/templates")
    page = int(request.args.get("page", 1))
    query = db.query(SMSTemplate).order_by(SMSTemplate.name)
    p = paginate(query, page)
    return render_template("sms/templates.html", templates=p["rows"], p=p, active_page="sms")


@bp.route("/templates/<int:tid>/delete", methods=["POST"])
@login_required
def delete_template(tid):
    db = g.db
    tmpl = db.query(SMSTemplate).filter(SMSTemplate.id == tid).first()
    if tmpl:
        db.delete(tmpl)
        db.commit()
        flash("Template deleted", "info")
    return redirect("/sms/templates")


@bp.route("/log")
@login_required
def sms_log():
    db = g.db
    page = int(request.args.get("page", 1))
    direction = request.args.get("direction", "")
    q = db.query(SMSMessage)
    if direction:
        q = q.filter(SMSMessage.direction == direction)
    p = paginate(q.order_by(SMSMessage.created_at.desc()), page, 50)
    return render_template("sms/log.html", p=p, direction=direction, active_page="sms")


@bp.route("/schedule", methods=["GET", "POST"])
@login_required
def schedule_sms():
    db = g.db
    if request.method == "POST":
        to_number = request.form.get("to_number", "").strip()
        body = request.form.get("body", "").strip()
        scheduled_for = request.form.get("scheduled_for", "")
        if not to_number or not body or not scheduled_for:
            flash("All fields are required", "danger")
            return redirect("/sms/schedule")
        from datetime import datetime as dt
        sched_dt = dt.strptime(scheduled_for, "%Y-%m-%dT%H:%M")
        q = SMSQueue(to_number=to_number, body=body, scheduled_for=sched_dt)
        db.add(q)
        db.commit()
        log_audit("schedule", "sms_queue", q.id, f"Scheduled SMS to {to_number}")
        flash("SMS scheduled", "success")
        return redirect("/sms/log")
    customers = db.query(Customer).filter(Customer.phone != None, Customer.phone != "").order_by(Customer.name).all()
    return render_template("sms/schedule.html", customers=customers, active_page="sms")


@bp.route("/webhook", methods=["POST"])
def sms_webhook():
    db = g.db
    try:
        sms_sid = request.form.get("MessageSid", "")
        status = request.form.get("MessageStatus", "")
        sms = db.query(SMSMessage).filter(SMSMessage.external_id == sms_sid).first()
        if sms:
            sms.status = status
            if status == "delivered":
                sms.delivered_at = utcnow()
            db.commit()
    except Exception:
        logging.exception("SMS webhook error")
    return "", 204
