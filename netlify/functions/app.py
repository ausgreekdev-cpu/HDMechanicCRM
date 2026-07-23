import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("CRM_SECRET_KEY", os.environ.get("CRM_SECRET_KEY", ""))
os.environ.setdefault("CRM_DATABASE_URL", os.environ.get("CRM_DATABASE_URL", ""))

import serverless_wsgi
from app import create_app
from app.database import init_db

application = create_app()

try:
    init_db()
except Exception:
    pass

try:
    from app.agents import start_scheduler
    start_scheduler()
except Exception:
    pass


def handler(event, context):
    return serverless_wsgi.handle_request(application, event, context)
