import os
from flask import Flask, g, session, redirect
from flask_wtf.csrf import CSRFProtect
from app.database import SessionLocal


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

    if config_override:
        app.config.update(config_override)

    CSRFProtect(app)

    @app.before_request
    def open_session():
        g.db = SessionLocal()

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
        advanced_ops, finance, inventory_advanced, crm_advanced
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

    return app
