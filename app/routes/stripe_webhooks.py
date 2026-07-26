import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, g
from app.payments import (
    stripe_enabled, create_template_checkout, create_subscription_checkout,
    construct_webhook_event, handle_checkout_completed, handle_subscription_updated,
    handle_subscription_deleted, create_customer_portal_session, STRIPE_WEBHOOK_SECRET,
)
from app.models.templates import (
    WorkflowTemplate, TemplatePurchase, SubscriptionPlan, UserSubscription,
)
from app.models.core import User

logger = logging.getLogger(__name__)

bp = Blueprint("stripe_webhooks", __name__, url_prefix="/stripe")


@bp.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but CRM_STRIPE_WEBHOOK_SECRET is not set")
        return jsonify({"error": "webhook secret not configured"}), 500

    try:
        event = construct_webhook_event(payload, sig_header)
    except Exception as e:
        logger.error("Webhook signature verification failed: %s", e)
        return jsonify({"error": "invalid signature"}), 400

    event_type = event["type"]
    logger.info("Stripe webhook event: %s", event_type)

    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(event)
        except Exception:
            logger.exception("Error processing webhook event %s", event_type)
            return jsonify({"error": "processing error"}), 500
    else:
        logger.debug("Unhandled webhook event type: %s", event_type)

    return jsonify({"status": "ok"}), 200


@bp.route("/create-checkout/<int:tid>", methods=["POST"])
def create_template_checkout_route(tid):
    if "user_id" not in session:
        flash("Please sign in to purchase templates", "warning")
        return redirect(url_for("core.login"))

    if not stripe_enabled():
        return jsonify({"error": "Stripe is not configured"}), 503

    tmpl = g.db.query(WorkflowTemplate).get(tid)
    if not tmpl:
        return jsonify({"error": "template not found"}), 404

    if tmpl.price <= 0 or tmpl.tier == "free":
        return jsonify({"error": "template is free"}), 400

    existing = g.db.query(TemplatePurchase).filter_by(
        user_id=session["user_id"], template_id=tid, status="completed"
    ).first()
    if existing:
        flash("You already own this template", "info")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    base = request.host_url.rstrip("/")
    success_url = f"{base}/stripe/success?type=template&id={tmpl.id}"
    cancel_url = f"{base}/stripe/cancel?type=template&id={tmpl.id}"

    try:
        checkout = create_template_checkout(tmpl, session["user_id"], success_url, cancel_url)
        if checkout:
            return redirect(checkout.url, code=303)
    except Exception:
        logger.exception("Failed to create Stripe checkout session for template %s", tid)
        flash("Payment session could not be created. Please try again.", "error")

    return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))


@bp.route("/create-subscription/<int:plan_id>", methods=["POST"])
def create_plan_checkout(plan_id):
    if "user_id" not in session:
        flash("Please sign in to subscribe", "warning")
        return redirect(url_for("core.login"))

    if not stripe_enabled():
        return jsonify({"error": "Stripe is not configured"}), 503

    plan = g.db.query(SubscriptionPlan).get(plan_id)
    if not plan:
        return jsonify({"error": "plan not found"}), 404

    cycle = request.form.get("cycle", "monthly")

    existing = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status.in_(["active", "trialing"]),
    ).first()
    if existing:
        flash("You already have an active subscription. Cancel it first.", "warning")
        return redirect(url_for("marketplace.plans"))

    base = request.host_url.rstrip("/")
    success_url = f"{base}/stripe/success?type=subscription&id={plan.id}&cycle={cycle}"
    cancel_url = f"{base}/stripe/cancel?type=subscription&id={plan.id}&cycle={cycle}"

    try:
        checkout = create_subscription_checkout(plan, cycle, session["user_id"], success_url, cancel_url)
        if checkout:
            return redirect(checkout.url, code=303)
    except Exception:
        logger.exception("Failed to create Stripe checkout session for plan %s", plan_id)
        flash("Payment session could not be created. Please try again.", "error")

    return redirect(url_for("marketplace.plans"))


@bp.route("/customer-portal", methods=["POST"])
def customer_portal():
    if "user_id" not in session:
        flash("Please sign in", "warning")
        return redirect(url_for("core.login"))

    if not stripe_enabled():
        return jsonify({"error": "Stripe is not configured"}), 503

    sub = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status.in_(["active", "trialing", "past_due"]),
    ).first()

    if not sub or not sub.stripe_customer_id:
        flash("No active subscription found to manage.", "warning")
        return redirect(url_for("marketplace.plans"))

    try:
        portal = create_customer_portal_session(
            sub.stripe_customer_id,
            return_url=request.host_url.rstrip("/") + url_for("marketplace.my_templates"),
        )
        return redirect(portal.url, code=303)
    except Exception:
        logger.exception("Failed to create customer portal session for user %s", session["user_id"])
        flash("Could not open billing portal. Please try again.", "error")
        return redirect(url_for("marketplace.my_templates"))


@bp.route("/success")
def success():
    pay_type = request.args.get("type", "")
    item_id = request.args.get("id", "")

    if pay_type == "template" and item_id:
        tmpl = g.db.query(WorkflowTemplate).get(int(item_id))
        if tmpl:
            flash(f"Payment successful! You now have access to '{tmpl.name}'.", "success")
            return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if pay_type == "subscription" and item_id:
        flash("Subscription activated! Welcome to your new plan.", "success")
        return redirect(url_for("marketplace.index"))

    flash("Payment successful!", "success")
    return redirect(url_for("marketplace.index"))


@bp.route("/cancel")
def cancel():
    pay_type = request.args.get("type", "")
    item_id = request.args.get("id", "")

    if pay_type == "template" and item_id:
        tmpl = g.db.query(WorkflowTemplate).get(int(item_id))
        if tmpl:
            return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if pay_type == "subscription":
        return redirect(url_for("marketplace.plans"))

    flash("Payment was cancelled.", "info")
    return redirect(url_for("marketplace.index"))
