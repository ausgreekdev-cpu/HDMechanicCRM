import logging
from datetime import datetime, timedelta
from app.timeutils import utcnow
from flask import Blueprint, request, g, jsonify, session
from sqlalchemy import func
from app.auth import login_required, admin_required
from app import limiter

bp = Blueprint("analytics_api", __name__, url_prefix="/api/analytics")

logger = logging.getLogger(__name__)


def _get_or_create_session(data):
    from app.models.analytics import AppSession
    db = g.db

    platform = data.get("platform", "web")
    app_version = data.get("app_version", "unknown")
    device_info = data.get("device_info", "")
    user_id = session.get("user_id")

    existing = None
    if data.get("session_id"):
        existing = db.query(AppSession).filter(
            AppSession.id == data["session_id"],
            AppSession.is_active == True
        ).first()

    if not existing:
        existing = db.query(AppSession).filter(
            AppSession.user_id == user_id,
            AppSession.platform == platform,
            AppSession.is_active == True
        ).order_by(AppSession.started_at.desc()).first()
        if existing and (utcnow() - (existing.last_active_at or existing.started_at)).total_seconds() > 1800:
            existing = None

    if existing:
        existing.last_active_at = utcnow()
        if app_version and app_version != "unknown":
            existing.app_version = app_version
        if device_info:
            existing.device_info = device_info
    else:
        existing = AppSession(
            user_id=user_id,
            platform=platform,
            app_version=app_version,
            device_info=device_info,
            started_at=utcnow(),
            last_active_at=utcnow(),
            page_views=0,
            is_active=True,
        )
        db.add(existing)

    db.commit()
    return existing.id


@bp.route("/session", methods=["POST"])
@limiter.limit("60/minute")
def create_session():
    try:
        data = request.get_json(force=True, silent=True) or {}
        sid = _get_or_create_session(data)
        return jsonify({"ok": True, "session_id": sid})
    except Exception:
        logger.exception("Failed to create analytics session")
        return jsonify({"ok": False}), 500


@bp.route("/pageview", methods=["POST"])
@limiter.limit("120/minute")
def record_pageview():
    try:
        from app.models.analytics import PageView, AppSession
        db = g.db
        data = request.get_json(force=True, silent=True) or {}

        platform = data.get("platform", "web")
        path = data.get("path", "/")
        load_time_ms = data.get("load_time_ms")
        session_id = data.get("session_id")
        user_id = session.get("user_id")

        if session_id:
            app_session = db.query(AppSession).filter(AppSession.id == session_id).first()
            if app_session:
                app_session.page_views = (app_session.page_views or 0) + 1
                app_session.last_active_at = utcnow()

        pv = PageView(
            session_id=session_id,
            user_id=user_id,
            path=path,
            load_time_ms=load_time_ms,
            platform=platform,
            created_at=utcnow(),
        )
        db.add(pv)
        db.commit()
        return jsonify({"ok": True})
    except Exception:
        logger.exception("Failed to record pageview")
        return jsonify({"ok": False}), 500


@bp.route("/feature", methods=["POST"])
def record_feature():
    try:
        from app.models.analytics import FeatureUsage
        db = g.db
        data = request.get_json(force=True, silent=True) or {}
        user_id = session.get("user_id")
        feature = data.get("feature", "")
        action = data.get("action", "view")

        if not feature:
            return jsonify({"ok": False, "error": "feature required"}), 400

        existing = db.query(FeatureUsage).filter(
            FeatureUsage.user_id == user_id,
            FeatureUsage.feature == feature,
            FeatureUsage.action == action,
        ).first()

        if existing:
            existing.count = (existing.count or 0) + 1
            existing.last_used_at = utcnow()
        else:
            existing = FeatureUsage(
                user_id=user_id,
                feature=feature,
                action=action,
                count=1,
                last_used_at=utcnow(),
            )
            db.add(existing)

        db.commit()
        return jsonify({"ok": True})
    except Exception:
        logger.exception("Failed to record feature usage")
        return jsonify({"ok": False}), 500


@bp.route("/crash", methods=["POST"])
@limiter.limit("10/minute")
def report_crash():
    try:
        from app.models.analytics import CrashReport
        db = g.db
        data = request.get_json(force=True, silent=True) or {}

        report = CrashReport(
            platform=data.get("platform", "unknown"),
            app_version=data.get("app_version", "unknown"),
            error_type=data.get("error_type", ""),
            error_message=data.get("error_message", ""),
            stack_trace=data.get("stack_trace", ""),
            device_info=data.get("device_info", ""),
            reported_at=utcnow(),
        )
        db.add(report)
        db.commit()
        return jsonify({"ok": True, "report_id": report.id})
    except Exception:
        logger.exception("Failed to report crash")
        return jsonify({"ok": False}), 500


@bp.route("/heartbeat", methods=["POST"])
@limiter.limit("60/minute")
def heartbeat():
    try:
        from app.models.analytics import AppSession
        db = g.db
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id")

        if not session_id:
            sid = _get_or_create_session(data)
            return jsonify({"ok": True, "session_id": sid})

        app_session = db.query(AppSession).filter(
            AppSession.id == session_id,
            AppSession.is_active == True,
        ).first()

        if app_session:
            app_session.last_active_at = utcnow()
            db.commit()
            return jsonify({"ok": True})
        else:
            sid = _get_or_create_session(data)
            return jsonify({"ok": True, "session_id": sid})
    except Exception:
        logger.exception("Failed to process heartbeat")
        return jsonify({"ok": False}), 500


@bp.route("/dashboard", methods=["GET"])
@login_required
@admin_required
def dashboard():
    from app.models.analytics import AppSession, PageView, FeatureUsage, DailyMetrics
    from app.models import WorkOrder, Customer
    db = g.db
    today = utcnow().strftime("%Y-%m-%d")
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    active_sessions = db.query(func.count(AppSession.id)).filter(
        AppSession.is_active == True,
        AppSession.last_active_at >= utcnow() - timedelta(minutes=30),
    ).scalar() or 0

    total_sessions_today = db.query(func.count(AppSession.id)).filter(
        AppSession.started_at >= today_start,
    ).scalar() or 0

    total_pageviews_today = db.query(func.count(PageView.id)).filter(
        PageView.created_at >= today_start,
    ).scalar() or 0

    platform_breakdown = db.query(
        AppSession.platform, func.count(AppSession.id)
    ).filter(
        AppSession.started_at >= today_start,
    ).group_by(AppSession.platform).all()

    top_features = db.query(
        FeatureUsage.feature, func.sum(FeatureUsage.count).label("total")
    ).order_by(func.sum(FeatureUsage.count).desc()).limit(10).all()

    recent_crashes = db.query(CrashReport).filter(
        CrashReport.reported_at >= utcnow() - timedelta(days=7),
    ).order_by(CrashReport.reported_at.desc()).limit(10).all()

    new_orders_today = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.created_at >= today_start,
    ).scalar() or 0

    new_customers_today = db.query(func.count(Customer.id)).filter(
        Customer.created_at >= today_start,
    ).scalar() or 0

    return jsonify({
        "active_sessions": active_sessions,
        "total_sessions_today": total_sessions_today,
        "total_pageviews_today": total_pageviews_today,
        "platform_breakdown": {p: c for p, c in platform_breakdown} if platform_breakdown else {},
        "top_features": [{"feature": f, "count": int(c or 0)} for f, c in top_features] if top_features else [],
        "recent_crashes": [
            {
                "id": c.id,
                "platform": c.platform,
                "error_type": c.error_type,
                "error_message": c.error_message,
                "reported_at": c.reported_at.isoformat() if c.reported_at else None,
                "is_resolved": c.is_resolved,
            } for c in (recent_crashes if recent_crashes else [])
        ],
        "new_work_orders_today": new_orders_today,
        "new_customers_today": new_customers_today,
    })


@bp.route("/features", methods=["GET"])
@login_required
@admin_required
def features():
    from app.models.analytics import FeatureUsage
    db = g.db
    days = request.args.get("days", 30, type=int)
    since = utcnow() - timedelta(days=days)

    features = db.query(
        FeatureUsage.feature,
        FeatureUsage.action,
        func.sum(FeatureUsage.count).label("total"),
    ).filter(
        FeatureUsage.last_used_at >= since,
    ).group_by(
        FeatureUsage.feature, FeatureUsage.action
    ).order_by(func.sum(FeatureUsage.count).desc()).all()

    return jsonify({
        "features": [
            {"feature": f, "action": a, "count": int(c or 0)}
            for f, a, c in features
        ]
    })


@bp.route("/daily", methods=["GET"])
@login_required
@admin_required
def daily():
    from app.models.analytics import DailyMetrics
    db = g.db
    days = request.args.get("days", 30, type=int)
    since = (utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    metrics = db.query(DailyMetrics).filter(
        DailyMetrics.metric_date >= since,
    ).order_by(DailyMetrics.metric_date).all()

    return jsonify({
        "metrics": [
            {
                "date": m.metric_date,
                "active_users": m.active_users,
                "total_sessions": m.total_sessions,
                "total_page_views": m.total_page_views,
                "new_work_orders": m.new_work_orders,
                "new_customers": m.new_customers,
                "revenue": m.revenue,
                "scrap_weight_kg": m.scrap_weight_kg,
                "avg_session_minutes": m.avg_session_minutes,
            } for m in metrics
        ]
    })
