"""
Square Payment Integration for HDMechanicCRM.

Supports:
- Square Web Payments SDK (online checkout)
- Square Invoices API (send invoices for work orders and template purchases)
- Square Subscriptions (recurring billing for marketplace plans)
- Webhook handling for payment confirmation

Requires CRM_SQUARE_ACCESS_TOKEN env var. Falls back to demo mode when unset.
"""
import os
import hashlib
import hmac
import logging
from datetime import timedelta
from app.timeutils import utcnow

logger = logging.getLogger(__name__)


def _cfg(key, default=""):
    return os.environ.get(key, default)


def _client():
    from square.client import Client
    return Client(
        access_token=_cfg("CRM_SQUARE_ACCESS_TOKEN"),
        environment=_cfg("CRM_SQUARE_ENVIRONMENT", "sandbox"),
    )


def square_enabled():
    return bool(_cfg("CRM_SQUARE_ACCESS_TOKEN"))


def demo_payments_allowed():
    """Inline fake completions only when explicitly opted in.

    Without this flag, an unconfigured Square integration must fail loudly
    instead of silently granting paid items for free.
    """
    return _cfg("CRM_ALLOW_DEMO_PAYMENTS", "").lower() in ("1", "true", "yes")


def get_square_config():
    return {
        "enabled": square_enabled(),
        "application_id": _cfg("CRM_SQUARE_APPLICATION_ID"),
        "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
        "environment": _cfg("CRM_SQUARE_ENVIRONMENT", "sandbox"),
    }


def create_payment_link(amount_cents, currency, title, description, redirect_url,
                        payment_note=None, idempotency_key=None):
    if not square_enabled():
        if demo_payments_allowed():
            return {"url": redirect_url, "demo": True, "payment_id": f"sq_demo_{int(utcnow().timestamp())}"}
        return {"error": "Online payments are not configured. Please contact the shop."}

    client = _client()
    body = {
        "idempotency_key": idempotency_key or f"tmpl_{int(utcnow().timestamp() * 1000)}",
        "quick_pay": {
            "name": title,
            "price_money": {"amount": int(amount_cents), "currency": currency},
            "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
        },
        "redirect_url": redirect_url,
    }
    if payment_note:
        # Square copies payment_note onto the resulting payment; used as
        # defense-in-depth alongside payment_link_id matching.
        body["payment_note"] = payment_note
    result = client.checkout.create_payment_link(body=body)
    if result.is_success():
        return {"url": result.body["payment_link"]["url"], "payment_link_id": result.body["payment_link"]["id"]}
    else:
        logger.error(f"Square create_payment_link failed: {result.errors}")
        return {"error": str(result.errors)}


def verify_webhook_signature(body, signature_header, notification_url):
    key = _cfg("CRM_SQUARE_WEBHOOK_SIGNATURE_KEY")
    if not key:
        return True
    payload = body + notification_url
    expected = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def find_completed_payment(amount_cents, currency=None, exclude_ids=()):
    """Return the id of a recent COMPLETED Square payment matching amount_cents.

    Used to confirm that a checkout redirect actually corresponds to a
    captured payment before granting a purchase or subscription.
    Returns None when Square is disabled, the API call fails, or no
    unconsumed match is found.
    """
    if not square_enabled():
        return None
    client = _client()
    begin = (utcnow() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = client.payments.list_payments(begin_time=begin, limit=100)
    except Exception:
        logger.exception("Square list_payments raised")
        return None
    if not result.is_success():
        logger.error(f"Square list_payments failed: {result.errors}")
        return None
    excluded = set(exclude_ids)
    for payment in result.body.get("payments", []):
        if payment.get("status") != "COMPLETED":
            continue
        money = payment.get("amount_money") or {}
        if money.get("amount") != amount_cents:
            continue
        if currency and money.get("currency") != currency:
            continue
        if payment.get("id") in excluded:
            continue
        return payment.get("id")
    logger.warning(f"No completed Square payment found for amount={amount_cents}")
    return None
