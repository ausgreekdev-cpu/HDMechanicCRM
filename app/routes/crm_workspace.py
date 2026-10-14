"""Saved filters, dashboard widgets, workflow rules (same `crm_advanced` blueprint)."""
from flask import render_template, request, redirect, flash, g, session
import json
from app.models import SavedFilter, DashboardWidget, WorkflowRule
from app.auth import login_required
from app.helpers import paginate
from sqlalchemy import func
from app.routes.crm_advanced import bp


# ---- Saved Filters ----
@bp.route("/saved-filters")
@login_required
def list_saved_filters():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(SavedFilter).filter(SavedFilter.user_id == session.get("user_id")).order_by(SavedFilter.name), page)
    return render_template("crm_advanced/saved_filters.html", p=pagination, active_page="saved_filters")


@bp.route("/saved-filters/new", methods=["POST"])
@login_required
def create_saved_filter():
    db = g.db
    try:
        data = {k: v for k, v in request.form.items() if k not in ("csrf_token", "name", "entity_type")}
        sf = SavedFilter(user_id=session["user_id"], name=request.form["name"],
                         entity_type=request.form["entity_type"],
                         filter_data=json.dumps(data),
                         is_default=request.form.get("is_default") == "on")
        db.add(sf); db.commit()
        flash("Filter saved", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/saved-filters")
# ---- Dashboard Widgets ----
@bp.route("/dashboard-widgets")
@login_required
def list_widgets():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(DashboardWidget).filter(DashboardWidget.user_id == session.get("user_id")).order_by(DashboardWidget.position), page)
    return render_template("crm_advanced/dashboard_widgets.html", p=pagination, active_page="dashboard_widgets")


@bp.route("/dashboard-widgets/new", methods=["POST"])
@login_required
def create_widget():
    db = g.db
    try:
        w = DashboardWidget(user_id=session["user_id"], widget_type=request.form["widget_type"],
                            title=request.form.get("title", ""),
                            config=request.form.get("config", "{}"),
                            position=(db.query(func.max(DashboardWidget.position)).filter(
                                DashboardWidget.user_id == session["user_id"]).scalar() or 0) + 1)
        db.add(w); db.commit()
        flash("Widget added to dashboard", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/dashboard-widgets")


@bp.route("/dashboard-widgets/<int:wid>/toggle", methods=["POST"])
@login_required
def toggle_widget(wid):
    db = g.db
    w = db.query(DashboardWidget).filter(DashboardWidget.id == wid).first()
    if w: w.is_visible = not w.is_visible; db.commit()
    return redirect("/crm/dashboard-widgets")
# ---- Workflow Rules ----
@bp.route("/workflow-rules")
@login_required
def list_workflow_rules():
    db = g.db
    page = int(request.args.get("page", 1))
    pagination = paginate(db.query(WorkflowRule).order_by(WorkflowRule.name), page)
    return render_template("crm_advanced/workflow_rules.html", p=pagination, active_page="workflow_rules")


@bp.route("/workflow-rules/new", methods=["POST"])
@login_required
def create_workflow_rule():
    db = g.db
    try:
        r = WorkflowRule(name=request.form["name"], trigger_event=request.form["trigger_event"],
                         conditions=request.form.get("conditions", "{}"),
                         actions=request.form.get("actions", "{}"))
        db.add(r); db.commit()
        flash("Workflow rule created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/crm/workflow-rules")


@bp.route("/workflow-rules/<int:rid>/toggle", methods=["POST"])
@login_required
def toggle_workflow_rule(rid):
    db = g.db
    r = db.query(WorkflowRule).filter(WorkflowRule.id == rid).first()
    if r: r.is_active = not r.is_active; db.commit()
    return redirect("/crm/workflow-rules")
