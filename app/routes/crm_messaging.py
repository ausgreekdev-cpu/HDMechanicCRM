"""Email and SMS logs (same `crm_advanced` blueprint)."""
from flask import render_template, request, redirect, flash, g
from app.models import EmailLog, SMSLog
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.crm_advanced import bp


# ---- Email Log ----
@bp.route("/email-log")
@login_required
def list_emails():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(EmailLog).order_by(EmailLog.created_at.desc()), page, 50)
    return render_template("crm_advanced/email_log.html", p=p, active_page="email_log")


@bp.route("/email-log/send", methods=["POST"])
@login_required
def send_custom_email():
    from app.notifications import send_email
    db = g.db
    try:
        to = request.form.get("to", "").strip()
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        if to and subject:
            send_email(to, subject, body)
            db.add(EmailLog(recipient=to, subject=subject, body_text=body,
                            customer_id=int(request.form.get("customer_id", 0)) or None,
                            related_type=request.form.get("related_type", ""),
                            related_id=int(request.form.get("related_id", 0)) or None))
            db.commit()
            flash("Email sent", "success")
        return redirect("/crm/email-log")
    except Exception:
        db.rollback(); flash("Error sending email", "danger")
        return redirect("/crm/email-log")
# ---- SMS Log ----
@bp.route("/sms-log")
@login_required
def list_sms():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(SMSLog).order_by(SMSLog.created_at.desc()), page, 50)
    return render_template("crm_advanced/sms_log.html", p=p, active_page="sms_log")


@bp.route("/sms-log/send", methods=["POST"])
@login_required
def send_sms():
    db = g.db
    try:
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "")
        if phone and message:
            log_audit("send_sms", "sms", None, f"To {phone}")
            db.add(SMSLog(phone=phone, message=message,
                          customer_id=int(request.form.get("customer_id", 0)) or None,
                          related_type=request.form.get("related_type", ""),
                          related_id=int(request.form.get("related_id", 0)) or None))
            db.commit()
            flash("SMS queued (requires Twilio integration)", "info")
        return redirect("/crm/sms-log")
    except Exception:
        db.rollback(); flash("Error", "danger")
        return redirect("/crm/sms-log")
