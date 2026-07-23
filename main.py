import sys
import os
import logging
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.database import init_db, SessionLocal
from app.models import User
from app.auth import hash_password


def _setup_logging(app):
    log_level = os.environ.get("CRM_LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("CRM_LOG_FILE", "")

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))
    logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))


def _seed_defaults():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            import secrets
            admin_pw = os.environ.get("CRM_ADMIN_PASSWORD", secrets.token_urlsafe(16))
            db.add(User(
                username=os.environ.get("CRM_ADMIN_USER", "admin"),
                password_hash=hash_password(admin_pw),
                display_name="Administrator",
                role="admin"
            ))
            db.commit()
            logging.info(f"Default admin created — username: {os.environ.get('CRM_ADMIN_USER', 'admin')}")
    finally:
        db.close()


app = create_app()

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    init_db()
    _seed_defaults()
    _setup_logging(app)

    try:
        from app.agents import start_scheduler
        start_scheduler()
    except Exception as e:
        logging.warning(f"Scheduler failed to start: {e}")


if __name__ == "__main__":
    import webbrowser
    import threading
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000")).start()
    app.run(host="127.0.0.1", port=8000, debug=True)
