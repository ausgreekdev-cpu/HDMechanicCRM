import os
import re
import tempfile
import pytest

os.environ["CRM_SECRET_KEY"] = "test-secret-key-for-testing-only-1234567890abcdef"
# Isolate tests from the developer database (app.database reads this at import).
os.environ.setdefault(
    "CRM_DATABASE_URL",
    "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="crm_tests_"), "test.db"),
)

from app import create_app
from app.database import Base, engine, SessionLocal

# The app sets PREFERRED_URL_SCHEME=https, so test requests are treated as
# HTTPS and flask-wtf's strict referrer check requires a matching Referer.
REFERER = {"Referer": "https://localhost/"}


def _build_app(csrf):
    return create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": csrf,
        "RATELIMIT_ENABLED": False,
    })


def get_csrf(client, path="/login"):
    """GET a page so the client session holds a token, then extract it."""
    resp = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', resp.data)
    assert match, f"no csrf_token input rendered at {path} (status={resp.status_code})"
    return match.group(1).decode()


@pytest.fixture
def app():
    # NOTE: no `with app.app_context()` around yield — Flask reuses an active
    # app context for same-app requests, which would share `g` across requests
    # and break flask-wtf's per-request CSRF token caching. create_all does
    # not need an app context.
    app = _build_app(csrf=False)
    Base.metadata.create_all(bind=engine)
    yield app
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def csrf_app():
    app = _build_app(csrf=True)
    Base.metadata.create_all(bind=engine)
    yield app
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        session = SessionLocal()
        yield session
        session.rollback()
        session.close()
