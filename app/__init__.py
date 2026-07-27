import os
import logging
from datetime import datetime, timezone
from flask import Flask, g, session, request, render_template
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.database import SessionLocal

limiter = Limiter(key_func=get_remote_address)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crm")


def create_app(config_override=None):
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    _secret = os.environ.get("CRM_SECRET_KEY", "")
    if not _secret or _secret == "change-me-to-a-random-64-char-string":
        raise RuntimeError(
            "CRM_SECRET_KEY environment variable is required. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    app.config["SECRET_KEY"] = _secret
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.config["DEBUG"] = debug

    if not debug:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_NAME"] = "__Host-session"
        app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 7
        app.config["PREFERRED_URL_SCHEME"] = "https"

    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    if config_override:
        app.config.update(config_override)

    csrf = CSRFProtect(app)
    limiter.init_app(app)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html", active_page=""), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", active_page=""), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Internal server error")
        return render_template("500.html", active_page=""), 500

    _cache: dict = {}
    _CACHE_TTL = 60

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.before_request
    def open_session():
        g.db = SessionLocal()
        g._req_start = datetime.now(timezone.utc)
        _path = request.path
        _cached = _cache.get(_path)
        if _cached and (datetime.now(timezone.utc) - _cached["ts"]).total_seconds() < _CACHE_TTL:
            g._cached_dashboard = _cached["data"]

    @app.after_request
    def log_request(response):
        if request.path.startswith("/static"):
            return response
        start = getattr(g, "_req_start", None)
        if start:
            ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(level, "%s %s %s %.0fms", request.method, request.path, response.status_code, ms)
        return response

    @app.teardown_request
    def close_session(exc=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    from app.models import User, Alert

    @app.context_processor
    def inject_user():
        ctx = {"current_user": None, "unread_alerts": 0}
        if "user_id" in session:
            user = g.db.query(User).filter(User.id == session["user_id"]).first()
            if user:
                ctx["current_user"] = user
                ctx["unread_alerts"] = g.db.query(Alert).filter(Alert.is_read == False).count()
        return ctx

    from app.routes import (
        core, dashboard, customers, vehicles, work_orders, parts, scrap_metal,
        operations, communications, technicians, invoices, purchase_orders, dvi,
        advanced_ops, finance, inventory_advanced, crm_advanced, marketplace,
        customer_portal, sms_integration, quote_to_wo, terms, square_payments,
        analytics_api
    )

    app.register_blueprint(core.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(customers.bp)
    app.register_blueprint(vehicles.bp)
    app.register_blueprint(work_orders.bp)
    app.register_blueprint(parts.bp)
    app.register_blueprint(scrap_metal.bp)
    app.register_blueprint(operations.bp)
    app.register_blueprint(communications.bp)
    app.register_blueprint(technicians.bp)
    app.register_blueprint(invoices.bp)
    app.register_blueprint(purchase_orders.bp)
    app.register_blueprint(dvi.bp)
    app.register_blueprint(advanced_ops.bp)
    app.register_blueprint(finance.bp)
    app.register_blueprint(inventory_advanced.bp)
    app.register_blueprint(crm_advanced.bp)
    app.register_blueprint(marketplace.bp)
    app.register_blueprint(customer_portal.bp)
    app.register_blueprint(sms_integration.bp)
    app.register_blueprint(quote_to_wo.bp)
    app.register_blueprint(terms.bp)
    app.register_blueprint(square_payments.bp)
    csrf.exempt(square_payments.bp)
    app.register_blueprint(analytics_api.bp)
    csrf.exempt(analytics_api.bp)

    return app
