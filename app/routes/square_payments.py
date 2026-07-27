import os
import json
import logging
from datetime import datetime, timedelta
from app.timeutils import utcnow
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, session, abort
import os
from app.payments_square import square_enabled, get_square_config, create_payment_link, create_subscription, cancel_subscription, verify_webhook_signature
SQUARE_CURRENCY = os.environ.get("CRM_SQUARE_CURRENCY", "AUD")
from app.models.templates import TemplatePurchase, SubscriptionPlan, UserSubscription, WorkflowTemplate

logger = logging.getLogger(__name__)

bp = Blueprint("square_payments", __name__, url_prefix="/payments")


@bp.route("/config")
def config():
    """Return Square config for frontend."""
    return jsonify(get_square_config())


@bp.route("/checkout/template/<int:tid>", methods=["POST"])
def checkout_template(tid):
    """Initiate Square checkout for a template purchase."""
    if "user_id" not in session:
        flash("Please sign in to purchase templates", "warning")
        return redirect(url_for("core.login"))

    tmpl = g.db.query(WorkflowTemplate).get(tid)
    if not tmpl or tmpl.price <= 0:
        flash("Invalid template", "warning")
        return redirect(url_for("marketplace.index"))

    existing = g.db.query(TemplatePurchase).filter_by(
        user_id=session["user_id"], template_id=tid, status="completed"
    ).first()
    if existing:
        flash("You already own this template", "info")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    success_url = url_for("square_payments.payment_success", source="template", item_id=tid, _external=True)
    result = create_payment_link(
        amount_cents=int(tmpl.price * 100),
        currency=SQUARE_CURRENCY,
        title=tmpl.name,
        description=tmpl.description[:200] if tmpl.description else "",
        redirect_url=success_url,
    )

    if result.get("error"):
        flash(f"Payment error: {result['error']}", "danger")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if result.get("demo"):
        purchase = TemplatePurchase(
            user_id=session["user_id"],
            template_id=tid,
            amount_paid=tmpl.price,
            payment_method="square_demo",
            stripe_payment_id=result.get("payment_id", ""),
            status="completed"
        )
        tmpl.purchase_count = (tmpl.purchase_count or 0) + 1
        g.db.add(purchase)
        g.db.commit()
        flash(f"Purchased '{tmpl.name}' for ${tmpl.price:.2f} (demo mode)!", "success")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    return redirect(result["url"])


@bp.route("/checkout/plan/<int:plan_id>", methods=["POST"])
def checkout_plan(plan_id):
    """Initiate Square checkout for subscription."""
    if "user_id" not in session:
        flash("Please sign in to subscribe", "warning")
        return redirect(url_for("core.login"))

    plan = g.db.query(SubscriptionPlan).get(plan_id)
    if not plan:
        abort(404)

    existing = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status.in_(["active", "trialing"])
    ).first()
    if existing:
        flash("You already have an active subscription. Cancel it first.", "warning")
        return redirect(url_for("marketplace.plans"))

    cycle = request.form.get("cycle", "monthly")
    price_cents = int(plan.price_monthly * 100) if cycle == "monthly" else int(plan.price_yearly * 100)

    success_url = url_for("square_payments.payment_success", source="subscription", item_id=plan_id, cycle=cycle, _external=True)
    result = create_payment_link(
        amount_cents=price_cents,
        currency=SQUARE_CURRENCY,
        title=f"{plan.name} ({cycle})",
        description=plan.description[:200] if plan.description else "",
        redirect_url=success_url,
    )

    if result.get("error"):
        flash(f"Payment error: {result['error']}", "danger")
        return redirect(url_for("marketplace.plans"))

    if result.get("demo"):
        sub = UserSubscription(
            user_id=session["user_id"],
            plan_id=plan.id,
            billing_cycle=cycle,
            status="active",
            stripe_subscription_id=result.get("subscription_id", ""),
            current_period_start=utcnow(),
            current_period_end=utcnow() + timedelta(days=30 if cycle == "monthly" else 365),
        )
        g.db.add(sub)
        g.db.commit()
        flash(f"Subscribed to {plan.name} ({cycle}) (demo mode)!", "success")
        return redirect(url_for("marketplace.index"))

    return redirect(result["url"])


@bp.route("/success")
def payment_success():
    """Payment success callback."""
    source = request.args.get("source", "")
    item_id = request.args.get("item_id", "")
    flash("Payment successful! Thank you.", "success")

    if source == "template" and item_id:
        tmpl = g.db.query(WorkflowTemplate).get(int(item_id))
        if tmpl:
            existing = g.db.query(TemplatePurchase).filter_by(
                user_id=session.get("user_id"), template_id=int(item_id), status="completed"
            ).first()
            if not existing:
                purchase = TemplatePurchase(
                    user_id=session.get("user_id", 0),
                    template_id=int(item_id),
                    amount_paid=tmpl.price,
                    payment_method="square",
                    status="completed"
                )
                tmpl.purchase_count = (tmpl.purchase_count or 0) + 1
                g.db.add(purchase)
                g.db.commit()
            return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if source == "subscription" and item_id:
        cycle = request.args.get("cycle", "monthly")
        existing = g.db.query(UserSubscription).filter(
            UserSubscription.user_id == session.get("user_id"),
            UserSubscription.status.in_(["active", "trialing"])
        ).first()
        if not existing:
            plan = g.db.query(SubscriptionPlan).get(int(item_id))
            if plan:
                sub = UserSubscription(
                    user_id=session.get("user_id", 0),
                    plan_id=plan.id,
                    billing_cycle=cycle,
                    status="active",
                    current_period_start=utcnow(),
                    current_period_end=utcnow() + timedelta(days=30 if cycle == "monthly" else 365),
                )
                g.db.add(sub)
                g.db.commit()
        return redirect(url_for("marketplace.index"))

    return redirect(url_for("marketplace.index"))


@bp.route("/cancel")
def payment_cancel():
    flash("Payment cancelled.", "warning")
    return redirect(url_for("marketplace.index"))


@bp.route("/webhook", methods=["POST"])
def webhook():
    """Square webhook endpoint for payment notifications."""
    body = request.get_data(as_text=True)
    sig = request.headers.get("x-square-hmacsha256-signature", "")
    notification_url = url_for("square_payments.webhook", _external=True)

    if not verify_webhook_signature(body, sig, notification_url):
        return jsonify({"error": "Invalid signature"}), 401

    event = json.loads(body)
    event_type = event.get("type", "")

    if event_type == "payment.completed":
        data = event.get("data", {}).get("object", {}).get("payment", {})
        logger.info(f"Square payment completed: {data.get('id')}")

    elif event_type == "subscription.created":
        logger.info(f"Square subscription created: {event.get('data', {}).get('object', {}).get('subscription', {}).get('id')}")

    elif event_type == "subscription.canceled":
        sub_data = event.get("data", {}).get("object", {}).get("subscription", {})
        sub_id = sub_data.get("id")
        if sub_id:
            sub = g.db.query(UserSubscription).filter_by(stripe_subscription_id=sub_id).first()
            if sub:
                sub.status = "canceled"
                g.db.commit()

    return jsonify({"ok": True})
