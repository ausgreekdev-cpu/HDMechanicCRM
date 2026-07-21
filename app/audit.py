import logging
from flask import session, request
from app.database import SessionLocal
from app.models import AuditLog


def log_audit(action, entity_type, entity_id=None, details=None):
    try:
        db = SessionLocal()
        db.add(AuditLog(
            user_id=session.get("user_id"),
            username=session.get("username", "unknown"),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=request.remote_addr or "",
        ))
        db.commit()
    except Exception:
        logging.exception("Failed to write audit log")
    finally:
        db.close()
