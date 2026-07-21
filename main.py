import sys, os, webbrowser, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.database import init_db, SessionLocal
from app.models import User
from app.auth import hash_password
import logging

logging.basicConfig(level=logging.ERROR, format="%(asctime)s [%(levelname)s] %(message)s")

app = create_app()


def open_browser():
    webbrowser.open("http://localhost:8000")


def seed_defaults():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            import secrets
            admin_pw = os.environ.get("CRM_ADMIN_PASSWORD", secrets.token_urlsafe(16))
            db.add(User(username=os.environ.get("CRM_ADMIN_USER", "admin"),
                        password_hash=hash_password(admin_pw),
                        display_name="Administrator", role="admin"))
            db.commit()
            print(f"Default admin created — username: {os.environ.get('CRM_ADMIN_USER', 'admin')}")
            print(f"Set CRM_ADMIN_PASSWORD in .env to control the password, or use the printed value.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_defaults()
    from app.agents import start_scheduler
    start_scheduler()
    threading.Timer(1.5, open_browser).start()
    app.run(host="127.0.0.1", port=8000, debug=False)
