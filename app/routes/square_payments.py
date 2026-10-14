import os
import json
import logging
from datetime import datetime, timedelta
from app.timeutils import utcnow
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, session, abort
from app.payments_square import square_enabled, get_square_config, create_payment_link, verify_webhook_signature, find_completed_payment
SQUARE_CURRENCY = os.environ.get("CRM_SQUARE_CURRENCY", "AUD")
from app.models.templates import TemplatePurchase, SubscriptionPlan, UserSubscription, WorkflowTemplate

logger = logging.getLogger(__name__)

bp = Blueprint("square_payments", __name__, url_prefix="/payments")

PENDING_TTL_HOURS = 24


def _is_expired(created_at):
    if not created_at:
        return False
    age = utcnow() - (created_at.replace(tzinfo=None) if created_at.tzinfo else created_at)
    return age.total_seconds() > PENDING_TTL_HOURS * 3600


def _verified_payment_id(amount_cents):
    """Return a captured, not-yet-consumed Square payment id, or None.

    Demo mode (Square disabled) never redirects to /success — checkout
    completes inline — so a missing match always means "not verified".
    """
    if not square_enabled():
        return None
    used = {
        r.stripe_payment_id for r in g.db.query(TemplatePurchase)
        .filter(TemplatePurchase.stripe_payment_id != "").all()
    } | {
        s.stripe_subscription_id for s in g.db.query(UserSubscription)
        .filter(UserSubscription.stripe_subscription_id != "").all()
    }
    return find_completed_payment(amount_cents, currency=SQUARE_CURRENCY, exclude_ids=used)


def _expected_subscription_cents(sub):
    plan = sub.plan
    if not plan:
        return None
    return int(plan.price_monthly * 100) if sub.billing_cycle == "monthly" else int(plan.price_yearly * 100)


def _grant_template_purchase(purchase, payment_id):
    purchase.stripe_payment_id = payment_id
    purchase.payment_method = "square"
    purchase.status = "completed"
    tmpl = g.db.query(WorkflowTemplate).get(purchase.template_id)
    if tmpl:
        tmpl.purchase_count = (tmpl.purchase_count or 0) + 1


def _grant_subscription(sub, payment_id):
    sub.stripe_subscription_id = payment_id
    sub.status = "active"
    sub.current_period_start = utcnow()
    sub.current_period_end = utcnow() + timedelta(days=30 if sub.billing_cycle == "monthly" else 365)


def _handle_payment_completed(payment):
    """Grant a pending purchase/subscription from a Square payment webhook.

    Matches by payment_link_id when present (exact); otherwise grants only
    when exactly one pending row matches the paid amount within the TTL.
    Duplicate deliveries are no-ops.
    """
    payment_id = payment.get("id")
    if not payment_id:
        return
    already = (
        g.db.query(TemplatePurchase).filter_by(stripe_payment_id=payment_id).first()
        or g.db.query(UserSubscription).filter_by(stripe_subscription_id=payment_id).first()
    )
    if already:
        return

    money = payment.get("amount_money") or {}
    amount = money.get("amount")
    currency = money.get("currency")
    link_id = payment.get("payment_link_id") or ""

    def amount_matches(purchase_cents):
        return purchase_cents is not None and amount == purchase_cents and (
            not currency or currency == SQUARE_CURRENCY
        )

    if link_id:
        tp = g.db.query(TemplatePurchase).filter_by(
            status="pending", square_payment_link_id=link_id
        ).first()
        if tp and amount_matches(int(tp.amount_paid * 100)) and not _is_expired(tp.created_at):
            _grant_template_purchase(tp, payment_id)
            g.db.commit()
            logger.info(f"Webhook granted template purchase {tp.id} via payment {payment_id}")
            return
        us = g.db.query(UserSubscription).filter_by(
            status="pending", square_payment_link_id=link_id
        ).first()
        if us and amount_matches(_expected_subscription_cents(us)) and not _is_expired(us.created_at):
            _grant_subscription(us, payment_id)
            g.db.commit()
            logger.info(f"Webhook granted subscription {us.id} via payment {payment_id}")
            return

    tp_candidates = [
        p for p in g.db.query(TemplatePurchase).filter_by(status="pending").all()
        if amount_matches(int(p.amount_paid * 100)) and not _is_expired(p.created_at)
    ]
    us_candidates = [
        s for s in g.db.query(UserSubscription).filter_by(status="pending").all()
        if amount_matches(_expected_subscription_cents(s)) and not _is_expired(s.created_at)
    ]
    total = len(tp_candidates) + len(us_candidates)
    if total == 1:
        if tp_candidates:
            _grant_template_purchase(tp_candidates[0], payment_id)
        else:
            _grant_subscription(us_candidates[0], payment_id)
        g.db.commit()
        logger.info(f"Webhook granted pending row via amount fallback, payment {payment_id}")
    elif total > 1:
        logger.warning(
            f"Ambiguous payment {payment_id}: {total} pending rows match amount {amount}; skipping"
        )


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

    pending = TemplatePurchase(
        user_id=session["user_id"],
        template_id=tid,
        amount_paid=tmpl.price,
        payment_method="square",
        status="pending",
    )
    g.db.add(pending)
    g.db.flush()

    success_url = url_for(
        "square_payments.payment_success",
        source="template",
        item_id=tid,
        purchase_id=pending.id,
        _external=True,
    )
    result = create_payment_link(
        amount_cents=int(tmpl.price * 100),
        currency=SQUARE_CURRENCY,
        title=tmpl.name,
        description=tmpl.description[:200] if tmpl.description else "",
        redirect_url=success_url,
        payment_note=f"crm:tpl:{pending.id}",
        idempotency_key=f"checkout_tpl_{pending.id}",
    )

    if result.get("error"):
        g.db.delete(pending)
        g.db.commit()
        flash(f"Payment error: {result['error']}", "danger")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if result.get("demo"):
        pending.payment_method = "square_demo"
        pending.stripe_payment_id = result.get("payment_id", "")
        pending.status = "completed"
        tmpl.purchase_count = (tmpl.purchase_count or 0) + 1
        g.db.commit()
        flash(f"Purchased '{tmpl.name}' for ${tmpl.price:.2f} (demo mode)!", "success")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    pending.square_payment_link_id = result.get("payment_link_id", "")
    g.db.commit()
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

    pending = UserSubscription(
        user_id=session["user_id"],
        plan_id=plan.id,
        billing_cycle=cycle,
        status="pending",
        current_period_start=utcnow(),
    )
    g.db.add(pending)
    g.db.flush()

    success_url = url_for(
        "square_payments.payment_success",
        source="subscription",
        item_id=plan_id,
        subscription_id=pending.id,
        _external=True,
    )
    result = create_payment_link(
        amount_cents=price_cents,
        currency=SQUARE_CURRENCY,
        title=f"{plan.name} ({cycle})",
        description=plan.description[:200] if plan.description else "",
        redirect_url=success_url,
        payment_note=f"crm:sub:{pending.id}",
        idempotency_key=f"checkout_sub_{pending.id}",
    )

    if result.get("error"):
        g.db.delete(pending)
        g.db.commit()
        flash(f"Payment error: {result['error']}", "danger")
        return redirect(url_for("marketplace.plans"))

    if result.get("demo"):
        pending.stripe_subscription_id = result.get("subscription_id", "")
        pending.status = "active"
        pending.current_period_end = utcnow() + timedelta(days=30 if cycle == "monthly" else 365)
        g.db.commit()
        flash(f"Subscribed to {plan.name} ({cycle}) (demo mode)!", "success")
        return redirect(url_for("marketplace.index"))

    pending.square_payment_link_id = result.get("payment_link_id", "")
    g.db.commit()
    return redirect(result["url"])


@bp.route("/success")
def payment_success():
    """Square checkout redirect.

    Grants are tied to a pending record created at checkout time and
    verified against a captured Square payment — never to query params.
    """
    source = request.args.get("source", "")

    if "user_id" not in session:
        flash("Please sign in to confirm your purchase", "warning")
        return redirect(url_for("core.login"))

    if source == "template":
        purchase = g.db.query(TemplatePurchase).get(request.args.get("purchase_id", type=int) or 0)
        if not purchase or purchase.user_id != session["user_id"]:
            flash("No pending purchase found for this account.", "warning")
            return redirect(url_for("marketplace.index"))
        tmpl = g.db.query(WorkflowTemplate).get(purchase.template_id)
        if not tmpl:
            flash("Template no longer exists.", "warning")
            return redirect(url_for("marketplace.index"))
        if purchase.status == "completed":
            # The webhook already granted this purchase (user closed the
            # tab after paying, then came back).
            flash(f"'{tmpl.name}' is already confirmed — enjoy!", "success")
            return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))
        if purchase.status != "pending":
            flash("This checkout expired. Please try again.", "warning")
            return redirect(url_for("marketplace.index"))
        if _is_expired(purchase.created_at):
            purchase.status = "expired"
            g.db.commit()
            flash("This checkout expired. Please try again.", "warning")
            return redirect(url_for("marketplace.index"))
        pay_id = _verified_payment_id(int(purchase.amount_paid * 100))
        if not pay_id:
            flash("Payment not confirmed yet — give it a moment, then refresh.", "info")
            return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))
        _grant_template_purchase(purchase, pay_id)
        g.db.commit()
        flash(f"Purchased '{tmpl.name}'!", "success")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if source == "subscription":
        sub = g.db.query(UserSubscription).get(request.args.get("subscription_id", type=int) or 0)
        if not sub or sub.user_id != session["user_id"]:
            flash("No pending subscription found for this account.", "warning")
            return redirect(url_for("marketplace.index"))
        plan = sub.plan
        if sub.status in ("active", "trialing"):
            flash(f"Subscription to {plan.name if plan else 'this plan'} is already active!", "success")
            return redirect(url_for("marketplace.index"))
        if sub.status != "pending":
            flash("This checkout expired. Please try again.", "warning")
            return redirect(url_for("marketplace.plans"))
        if _is_expired(sub.created_at):
            sub.status = "expired"
            g.db.commit()
            flash("This checkout expired. Please try again.", "warning")
            return redirect(url_for("marketplace.plans"))
        if not plan:
            flash("Plan no longer exists.", "warning")
            return redirect(url_for("marketplace.plans"))
        pay_id = _verified_payment_id(_expected_subscription_cents(sub))
        if not pay_id:
            flash("Payment not confirmed yet — give it a moment, then refresh.", "info")
            return redirect(url_for("marketplace.plans"))
        _grant_subscription(sub, pay_id)
        g.db.commit()
        flash(f"Subscribed to {plan.name}!", "success")
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
        _handle_payment_completed(data)

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
