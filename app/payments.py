import os
import logging
from datetime import datetime, timedelta
from flask import g, session

logger = logging.getLogger(__name__)

STRIPE_KEY = os.environ.get("CRM_STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("CRM_STRIPE_WEBHOOK_SECRET", "")
DEMO_MODE = not STRIPE_KEY


def _get_stripe():
    import stripe
    stripe.api_key = STRIPE_KEY
    return stripe


def stripe_enabled():
    return not DEMO_MODE


def create_checkout_session(line_items, success_url, cancel_url, mode="payment", metadata=None):
    stripe = _get_stripe()
    params = {
        "line_items": line_items,
        "mode": mode,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if metadata:
        params["metadata"] = metadata
    return stripe.checkout.Session.create(**params)


def create_template_checkout(template, user_id, success_url, cancel_url):
    if DEMO_MODE:
        return None

    stripe = _get_stripe()
    price_cents = int(template.price * 100)

    session_obj = stripe.checkout.Session.create(
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": template.name,
                    "description": template.description[:500] if template.description else "",
                },
                "unit_amount": price_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user_id),
            "template_id": str(template.id),
            "type": "template_purchase",
        },
    )
    return session_obj


def create_subscription_checkout(plan, cycle, user_id, success_url, cancel_url):
    if DEMO_MODE:
        return None

    stripe = _get_stripe()

    if cycle == "yearly" and plan.stripe_price_yearly:
        price_id = plan.stripe_price_yearly
    elif plan.stripe_price_monthly:
        price_id = plan.stripe_price_monthly
    else:
        price_cents = int(plan.price_yearly * 100) if cycle == "yearly" else int(plan.price_monthly * 100)
        interval = "year" if cycle == "yearly" else "month"
        price_data = {
            "currency": "usd",
            "recurring": {"interval": interval},
            "product_data": {
                "name": plan.name,
                "description": plan.description[:500] if plan.description else "",
            },
            "unit_amount": price_cents,
        }
        return stripe.checkout.Session.create(
            line_items=[{"price_data": price_data, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "plan_id": str(plan.id),
                "cycle": cycle,
                "type": "subscription",
            },
        )

    return stripe.checkout.Session.create(
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user_id),
            "plan_id": str(plan.id),
            "cycle": cycle,
            "type": "subscription",
        },
    )


def construct_webhook_event(payload, sig_header):
    stripe = _get_stripe()
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)


def handle_checkout_completed(event):
    from app.models.templates import TemplatePurchase, SubscriptionPlan, UserSubscription
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata", {})
        event_type = metadata.get("type", "")

        if event_type == "template_purchase":
            user_id = int(metadata["user_id"])
            template_id = int(metadata["template_id"])

            existing = db.query(TemplatePurchase).filter_by(
                user_id=user_id, template_id=template_id, status="completed"
            ).first()
            if existing:
                logger.info("Template purchase already recorded for user %s template %s", user_id, template_id)
                return

            purchase = TemplatePurchase(
                user_id=user_id,
                template_id=template_id,
                amount_paid=session_obj.get("amount_total", 0) / 100.0,
                payment_method="stripe",
                stripe_payment_id=session_obj.get("payment_intent", session_obj.get("id", "")),
                status="completed",
            )
            db.add(purchase)

            from app.models.templates import WorkflowTemplate
            tmpl = db.query(WorkflowTemplate).get(template_id)
            if tmpl:
                tmpl.purchase_count = (tmpl.purchase_count or 0) + 1

            db.commit()
            logger.info("Template purchase completed: user=%s template=%s", user_id, template_id)

        elif event_type == "subscription":
            user_id = int(metadata["user_id"])
            plan_id = int(metadata["plan_id"])
            cycle = metadata.get("cycle", "monthly")

            sub = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                billing_cycle=cycle,
                status="active",
                stripe_subscription_id=session_obj.get("subscription", ""),
                stripe_customer_id=session_obj.get("customer", ""),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=365 if cycle == "yearly" else 30),
            )
            db.add(sub)
            db.commit()
            logger.info("Subscription created: user=%s plan=%s", user_id, plan_id)

    except Exception:
        db.rollback()
        logger.exception("Error handling checkout.session.completed")
        raise
    finally:
        db.close()


def handle_subscription_updated(event):
    from app.models.templates import UserSubscription
    from app.database import SessionLocal
    from sqlalchemy import or_

    db = SessionLocal()
    try:
        sub_data = event["data"]["object"]
        stripe_sub_id = sub_data.get("id", "")
        status = sub_data.get("status", "")

        sub = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        if not sub:
            logger.warning("Subscription not found for stripe sub ID: %s", stripe_sub_id)
            return

        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
            "trialing": "trialing",
            "incomplete": "past_due",
            "incomplete_expired": "canceled",
            "paused": "canceled",
        }
        sub.status = status_map.get(status, status)

        period_end = sub_data.get("current_period_end")
        if period_end:
            from datetime import timezone
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc).replace(tzinfo=None)

        cancel_at = sub_data.get("cancel_at")
        if cancel_at:
            from datetime import timezone
            sub.cancel_at = datetime.fromtimestamp(cancel_at, tz=timezone.utc).replace(tzinfo=None)
        elif sub_data.get("canceled_at"):
            from datetime import timezone
            sub.cancel_at = datetime.fromtimestamp(sub_data["canceled_at"], tz=timezone.utc).replace(tzinfo=None)

        sub.updated_at = datetime.utcnow()
        db.commit()
        logger.info("Subscription updated: %s -> %s", stripe_sub_id, sub.status)

    except Exception:
        db.rollback()
        logger.exception("Error handling subscription update")
        raise
    finally:
        db.close()


def handle_subscription_deleted(event):
    from app.models.templates import UserSubscription
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        stripe_sub_id = event["data"]["object"].get("id", "")
        sub = db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        if sub:
            sub.status = "canceled"
            sub.updated_at = datetime.utcnow()
            db.commit()
            logger.info("Subscription canceled: %s", stripe_sub_id)
    except Exception:
        db.rollback()
        logger.exception("Error handling subscription deletion")
        raise
    finally:
        db.close()


def create_customer_portal_session(customer_id, return_url):
    stripe = _get_stripe()
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
