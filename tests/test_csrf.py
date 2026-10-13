"""CSRF enforcement on protected POSTs, exemptions, and token rendering."""
from app.auth import hash_password
from app.database import SessionLocal
from app.models import User
from app.models.templates import WorkflowTemplate
from tests.conftest import REFERER, get_csrf


def _add_user(username="csrfuser", password="CsrfUserPass1!"):
    db = SessionLocal()
    user = User(username=username, password_hash=hash_password(password),
                role="admin", is_active=True)
    db.add(user)
    db.commit()
    db.close()
    return username, password


def _add_free_template(slug="csrf-free"):
    db = SessionLocal()
    tmpl = WorkflowTemplate(name="CsrfFree", slug=slug, tier="free", price=0,
                            description="d")
    db.add(tmpl)
    db.commit()
    tid = tmpl.id
    db.close()
    return tid


def _login(client, username, password):
    token = get_csrf(client, "/login")
    resp = client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
        headers=REFERER,
    )
    assert resp.status_code == 302, f"login failed: {resp.status_code}"


def test_login_post_without_token_rejected(csrf_client):
    resp = csrf_client.post(
        "/login", data={"username": "x", "password": "y"},
    )
    assert resp.status_code == 400
    assert b"CSRF" in resp.data


def test_login_post_with_token_accepted(csrf_client):
    username, password = _add_user()
    token = get_csrf(csrf_client, "/login")
    resp = csrf_client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
        headers=REFERER,
    )
    assert resp.status_code == 302


def test_apply_template_without_token_rejected(csrf_client):
    _add_user()
    tid = _add_free_template()
    _login(csrf_client, "csrfuser", "CsrfUserPass1!")
    resp = csrf_client.post(f"/marketplace/template/{tid}/apply")
    assert resp.status_code == 400


def test_apply_template_with_token_accepted(csrf_client):
    _add_user()
    tid = _add_free_template()
    _login(csrf_client, "csrfuser", "CsrfUserPass1!")
    token = get_csrf(csrf_client, "/marketplace/template/csrf-free")
    resp = csrf_client.post(
        f"/marketplace/template/{tid}/apply",
        data={"csrf_token": token},
        headers=REFERER,
    )
    assert resp.status_code == 302
    assert "/work-orders" in resp.headers["Location"]


def test_analytics_telemetry_exempt_from_csrf(csrf_client):
    # Android app POSTs JSON with no session cookie or CSRF token.
    resp = csrf_client.post("/api/analytics/session", json={"platform": "android"})
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True


def test_template_detail_renders_csrf_input(csrf_client):
    _add_free_template()
    resp = csrf_client.get("/marketplace/template/csrf-free")
    assert resp.status_code == 200
    assert b'name="csrf_token"' in resp.data


def test_plans_page_renders_csrf_input(csrf_client):
    from app.models.templates import SubscriptionPlan

    db = SessionLocal()
    db.add(SubscriptionPlan(name="P", slug="csrf-plan", price_monthly=10,
                            price_yearly=100, description="d"))
    db.commit()
    db.close()
    resp = csrf_client.get("/marketplace/plans")
    assert resp.status_code == 200
    assert b'name="csrf_token"' in resp.data
