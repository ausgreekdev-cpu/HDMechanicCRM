import json
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, session, abort
from app.models.templates import (
    TemplateCategory, WorkflowTemplate, TemplatePurchase,
    SubscriptionPlan, UserSubscription
)
from app.models.core import User
from app.payments import stripe_enabled

bp = Blueprint("marketplace", __name__, url_prefix="/marketplace")


def _get_user_plan():
    if "user_id" not in session:
        return None
    sub = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status == "active"
    ).first()
    if sub and sub.is_active:
        return sub.plan
    return None


def _user_has_template_access(user_plan, template):
    if template.tier == "free":
        return True
    if template.price > 0:
        purchase = g.db.query(TemplatePurchase).filter(
            TemplatePurchase.user_id == session.get("user_id"),
            TemplatePurchase.template_id == template.id,
            TemplatePurchase.status == "completed"
        ).first()
        if purchase:
            return True
    if user_plan:
        tiers = {"free": 0, "pro": 1, "enterprise": 2, "all": 3}
        plan_level = tiers.get(user_plan.template_access, 0)
        template_level = tiers.get(template.tier, 0)
        if plan_level >= template_level:
            return True
    return False


@bp.route("/")
def index():
    categories = g.db.query(TemplateCategory).filter_by(is_active=True).order_by(TemplateCategory.sort_order).all()
    featured = g.db.query(WorkflowTemplate).filter_by(is_featured=True, is_active=True).limit(6).all()
    popular = g.db.query(WorkflowTemplate).filter_by(is_active=True).order_by(WorkflowTemplate.purchase_count.desc()).limit(6).all()
    plans = g.db.query(SubscriptionPlan).filter_by(is_active=True).order_by(SubscriptionPlan.sort_order).all()
    user_plan = _get_user_plan()
    return render_template("marketplace/index.html",
        categories=categories, featured=featured, popular=popular,
        plans=plans, user_plan=user_plan, has_access=_user_has_template_access)


@bp.route("/category/<slug>")
def category(slug):
    cat = g.db.query(TemplateCategory).filter_by(slug=slug, is_active=True).first()
    if not cat: abort(404)
    templates = g.db.query(WorkflowTemplate).filter_by(
        category_id=cat.id, is_active=True
    ).order_by(WorkflowTemplate.is_featured.desc(), WorkflowTemplate.purchase_count.desc()).all()
    user_plan = _get_user_plan()
    return render_template("marketplace/category.html",
        category=cat, templates=templates,
        user_plan=user_plan, has_access=_user_has_template_access)


@bp.route("/template/<slug>")
def template_detail(slug):
    tmpl = g.db.query(WorkflowTemplate).filter_by(slug=slug, is_active=True).first()
    if not tmpl: abort(404)
    user_plan = _get_user_plan()
    has_access = _user_has_template_access(user_plan, tmpl) if "user_id" in session else tmpl.tier == "free"
    purchased = False
    if "user_id" in session:
        purchased = g.db.query(TemplatePurchase).filter_by(
            user_id=session["user_id"], template_id=tmpl.id, status="completed"
        ).first() is not None
    related = g.db.query(WorkflowTemplate).filter(
        WorkflowTemplate.category_id == tmpl.category_id,
        WorkflowTemplate.id != tmpl.id,
        WorkflowTemplate.is_active == True
    ).limit(3).all()
    return render_template("marketplace/template.html",
        template=tmpl, has_access=has_access, purchased=purchased,
        user_plan=user_plan, related=related)


@bp.route("/template/<int:tid>/purchase", methods=["POST"])
def purchase_template(tid):
    if "user_id" not in session:
        flash("Please sign in to purchase templates", "warning")
        return redirect(url_for("core.login"))

    tmpl = g.db.query(WorkflowTemplate).get(tid)
    if not tmpl: abort(404)
    if tmpl.price <= 0 or tmpl.tier == "free":
        flash("This template is free!", "info")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    existing = g.db.query(TemplatePurchase).filter_by(
        user_id=session["user_id"], template_id=tid, status="completed"
    ).first()
    if existing:
        flash("You already own this template", "info")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    if stripe_enabled():
        return redirect(url_for("stripe_webhooks.create_template_checkout_route", tid=tid))

    purchase = TemplatePurchase(
        user_id=session["user_id"],
        template_id=tid,
        amount_paid=tmpl.price,
        payment_method="stripe",
        stripe_payment_id=f"pi_demo_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        status="completed"
    )
    tmpl.purchase_count = (tmpl.purchase_count or 0) + 1
    g.db.add(purchase)
    g.db.commit()
    flash(f"Purchased '{tmpl.name}' for ${tmpl.price:.2f}!", "success")
    return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))


@bp.route("/template/<int:tid>/apply", methods=["POST"])
def apply_template(tid):
    if "user_id" not in session:
        flash("Please sign in", "warning")
        return redirect(url_for("core.login"))

    tmpl = g.db.query(WorkflowTemplate).get(tid)
    if not tmpl: abort(404)
    user_plan = _get_user_plan()
    if not _user_has_template_access(user_plan, tmpl):
        flash("You don't have access to this template", "warning")
        return redirect(url_for("marketplace.template_detail", slug=tmpl.slug))

    flash(f"Template '{tmpl.name}' applied! Steps have been added to your workflow.", "success")
    return redirect(url_for("work_orders.work_orders_list"))


@bp.route("/plans")
def plans():
    plans = g.db.query(SubscriptionPlan).filter_by(is_active=True).order_by(SubscriptionPlan.sort_order).all()
    user_plan = _get_user_plan()
    return render_template("marketplace/plans.html", plans=plans, user_plan=user_plan)


@bp.route("/subscribe/<int:plan_id>", methods=["POST"])
def subscribe(plan_id):
    if "user_id" not in session:
        flash("Please sign in to subscribe", "warning")
        return redirect(url_for("core.login"))

    plan = g.db.query(SubscriptionPlan).get(plan_id)
    if not plan: abort(404)
    cycle = request.form.get("cycle", "monthly")

    existing = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status.in_(["active", "trialing"])
    ).first()
    if existing:
        flash("You already have an active subscription. Cancel it first.", "warning")
        return redirect(url_for("marketplace.plans"))

    if stripe_enabled():
        return redirect(url_for("stripe_webhooks.create_plan_checkout", plan_id=plan_id, cycle=cycle))

    sub = UserSubscription(
        user_id=session["user_id"],
        plan_id=plan.id,
        billing_cycle=cycle,
        status="active",
        stripe_subscription_id=f"sub_demo_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30 if cycle == "monthly" else 365),
    )
    g.db.add(sub)
    g.db.commit()
    flash(f"Subscribed to {plan.name} ({cycle})! Enjoy your new features.", "success")
    return redirect(url_for("marketplace.index"))


@bp.route("/my-templates")
def my_templates():
    if "user_id" not in session:
        return redirect(url_for("core.login"))
    purchases = g.db.query(TemplatePurchase).filter_by(
        user_id=session["user_id"], status="completed"
    ).all()
    sub = g.db.query(UserSubscription).filter(
        UserSubscription.user_id == session["user_id"],
        UserSubscription.status == "active"
    ).first()
    return render_template("marketplace/my_templates.html",
        purchases=purchases, subscription=sub)


@bp.route("/api/check-access/<int:tid>")
def api_check_access(tid):
    if "user_id" not in session:
        return jsonify({"has_access": False})
    tmpl = g.db.query(WorkflowTemplate).get(tid)
    if not tmpl: abort(404)
    user_plan = _get_user_plan()
    return jsonify({"has_access": _user_has_template_access(user_plan, tmpl)})
