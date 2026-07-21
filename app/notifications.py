import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_CONFIG = {
    "server": os.environ.get("CRM_SMTP_SERVER", ""),
    "port": int(os.environ.get("CRM_SMTP_PORT", 587)),
    "username": os.environ.get("CRM_SMTP_USERNAME", ""),
    "password": os.environ.get("CRM_SMTP_PASSWORD", ""),
    "from_addr": os.environ.get("CRM_SMTP_FROM", ""),
    "use_tls": True,
}


def send_email(to_addr, subject, body_text, body_html=None):
    config = SMTP_CONFIG
    if not config["server"] or not config["from_addr"]:
        logging.warning("SMTP not configured — email not sent")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["from_addr"]
        msg["To"] = to_addr
        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(config["server"], config["port"]) as s:
            if config["use_tls"]:
                s.starttls()
            if config["username"]:
                s.login(config["username"], config["password"])
            s.send_message(msg)
        logging.info("Email sent to %s: %s", to_addr, subject)
        return True
    except Exception:
        logging.exception("Failed to send email to %s", to_addr)
        return False


def notify_invoice_created(invoice, customer_email=None):
    if not customer_email:
        return
    send_email(
        customer_email,
        f"Invoice {invoice.invoice_number} from HD Mechanic CRM",
        f"Your invoice #{invoice.invoice_number} for ${invoice.total_amount:.2f} is now available.\nStatus: {invoice.status}",
    )


def notify_invoice_paid(invoice, customer_email=None):
    if not customer_email:
        return
    send_email(
        customer_email,
        f"Payment Received — Invoice {invoice.invoice_number}",
        f"Thank you! Payment of ${invoice.amount_paid:.2f} received for invoice #{invoice.invoice_number}.\nBalance: ${max(0, invoice.total_amount - invoice.amount_paid):.2f}",
    )
