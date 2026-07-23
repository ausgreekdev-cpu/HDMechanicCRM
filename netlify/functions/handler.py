import os
import sys
import json
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

os.environ.setdefault("CRM_SECRET_KEY", os.environ.get("CRM_SECRET_KEY", "netlify-production-key-2024"))
os.environ.setdefault("FLASK_DEBUG", "0")

app = None
error_msg = None

try:
    from app import create_app
    from app.database import init_db

    app = create_app()

    try:
        init_db()
    except Exception:
        pass

    try:
        from app.agents import start_scheduler
        start_scheduler()
    except Exception:
        pass

except Exception:
    error_msg = traceback.format_exc()

try:
    import serverless_wsgi
except ImportError:
    if error_msg is None:
        error_msg = "serverless-wsgi not installed"


def handler(event, context):
    if error_msg:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Startup failed", "detail": error_msg[:3000]})
        }

    return serverless_wsgi.handle_request(app, event, context)
