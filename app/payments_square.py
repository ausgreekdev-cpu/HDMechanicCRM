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
from datetime import datetime, timedelta

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


def get_square_config():
    return {
        "enabled": square_enabled(),
        "application_id": _cfg("CRM_SQUARE_APPLICATION_ID"),
        "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
        "environment": _cfg("CRM_SQUARE_ENVIRONMENT", "sandbox"),
    }


def create_payment_link(amount_cents, currency, title, description, redirect_url, metadata=None):
    if not square_enabled():
        return {"url": redirect_url, "demo": True, "payment_id": f"sq_demo_{int(datetime.utcnow().timestamp())}"}

    client = _client()
    result = client.checkout.create_payment_link(
        body={
            "idempotency_key": f"tmpl_{int(datetime.utcnow().timestamp() * 1000)}",
            "quick_pay": {
                "name": title,
                "price_money": {"amount": int(amount_cents), "currency": currency},
                "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
            },
            "redirect_url": redirect_url,
        }
    )
    if result.is_success():
        return {"url": result.body["payment_link"]["url"], "payment_link_id": result.body["payment_link"]["id"]}
    else:
        logger.error(f"Square create_payment_link failed: {result.errors}")
        return {"error": str(result.errors)}


def create_invoice(customer_name, customer_email, amount_cents, currency, title, description, due_date_days=30):
    if not square_enabled():
        return {"demo": True, "invoice_id": f"sq_inv_demo_{int(datetime.utcnow().timestamp())}"}

    client = _client()
    customer_id = _find_or_create_customer(client, customer_name, customer_email)
    due_date = (datetime.utcnow() + timedelta(days=due_date_days)).strftime("%Y-%m-%d")

    result = client.invoices.create_invoice(
        body={
            "idempotency_key": f"inv_{int(datetime.utcnow().timestamp() * 1000)}",
            "invoice": {
                "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
                "customer_id": customer_id,
                "title": title,
                "description": description,
                "due_date": due_date,
                "payment_requests": [
                    {
                        "request_type": "BALANCE",
                        "payment_method": "CARD",
                        "computed_amount_money": {"amount": int(amount_cents), "currency": currency},
                    }
                ],
                "sale_order_id": None,
            }
        }
    )
    if result.is_success():
        invoice_id = result.body["invoice"]["id"]
        client.invoices.publish_invoice(invoice_id=invoice_id)
        return {"invoice_id": invoice_id}
    else:
        logger.error(f"Square create_invoice failed: {result.errors}")
        return {"error": str(result.errors)}


def create_subscription(customer_email, customer_name, plan_price_cents, plan_name, cycle_months=1):
    if not square_enabled():
        return {"demo": True, "subscription_id": f"sq_sub_demo_{int(datetime.utcnow().timestamp())}"}

    client = _client()
    customer_id = _find_or_create_customer(client, customer_name, customer_email)

    result = client.catalog.upsert_object(
        body={
            "idempotency_key": f"sub_{int(datetime.utcnow().timestamp() * 1000)}",
            "object": {
                "type": "SUBSCRIPTION_PLAN",
                "subscription_plan_data": {
                    "name": plan_name,
                    "phases": [
                        {
                            "cadence": "MONTHLY" if cycle_months == 1 else "ANNUALLY",
                            "recurring_price_money": {
                                "amount": int(plan_price_cents),
                                "currency": "USD",
                            },
                        }
                    ],
                },
            }
        }
    )
    if result.is_success():
        plan_id = result.body["id_mappings"][0]["object_id"]
        sub_result = client.subscriptions.create_subscription(
            body={
                "idempotency_key": f"sub_create_{int(datetime.utcnow().timestamp() * 1000)}",
                "location_id": _cfg("CRM_SQUARE_LOCATION_ID"),
                "customer_id": customer_id,
                "plan_id": plan_id,
                "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
            }
        )
        if sub_result.is_success():
            return {"subscription_id": sub_result.body["subscription"]["id"]}
        return {"error": str(sub_result.errors)}
    return {"error": str(result.errors)}


def cancel_subscription(subscription_id):
    if not square_enabled():
        return {"demo": True}
    client = _client()
    result = client.subscriptions.cancel_subscription(subscription_id=subscription_id)
    return {"success": result.is_success()}


def verify_webhook_signature(body, signature_header, notification_url):
    key = _cfg("CRM_SQUARE_WEBHOOK_SIGNATURE_KEY")
    if not key:
        return True
    payload = body + notification_url
    expected = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _find_or_create_customer(client, name, email):
    result = client.customers.search_customers(
        body={"query": {"filter": {"email_address": {"exact": email}}}}
    )
    if result.is_success() and result.body.get("customers"):
        return result.body["customers"][0]["id"]

    result = client.customers.create_customer(
        body={
            "idempotency_key": f"cust_{int(datetime.utcnow().timestamp() * 1000)}",
            "given_name": name.split()[0] if name else "Customer",
            "family_name": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
            "email_address": email,
        }
    )
    if result.is_success():
        return result.body["customer"]["id"]
    logger.error(f"Failed to create Square customer: {result.errors}")
    return None
