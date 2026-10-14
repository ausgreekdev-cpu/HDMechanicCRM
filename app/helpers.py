import os
import logging
from math import ceil

logger = logging.getLogger(__name__)


def send_email(to_email, subject, body_html, body_text=None):
    api_key = os.environ.get("CRM_SENDGRID_API_KEY", "")
    from_email = os.environ.get("CRM_FROM_EMAIL", "noreply@hdmechaniccrm.com")
    from_name = os.environ.get("CRM_FROM_NAME", "HD Mechanic CRM")

    if not api_key:
        logger.info("SendGrid not configured — email logged: To=%s Subject=%s", to_email, subject)
        return None

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Content

        content = Content("text/html", body_html)
        message = Mail(from_email=f"{from_name} <{from_email}>", to_emails=to_email, subject=subject, html_content=content)
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info("Email sent: To=%s Status=%s", to_email, response.status_code)
        return response
    except ImportError:
        logger.warning("sendgrid package not installed — pip install sendgrid")
        return None
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return None


def paginate(query, page, per_page=50):
    page = max(1, page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, ceil(total / per_page))
    return {
        "rows": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }