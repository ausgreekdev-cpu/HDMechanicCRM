import pytest
from app.models import User, Customer, Vehicle, WorkOrder, Part
from app.auth import hash_password


def _login(client, db_session, username="admin", password="adminpass", role="admin"):
    u = User(
        username=username,
        password_hash=hash_password(password),
        display_name="Admin",
        role=role,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    client.post("/login", data={"username": username, "password": password})


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_root_redirects_to_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_root_redirects_to_dashboard_when_logged_in(client, db_session):
    _login(client, db_session)
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_dashboard_loads_when_authenticated(client, db_session):
    _login(client, db_session)
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_search_requires_login(client):
    resp = client.get("/search?q=test", follow_redirects=False)
    assert resp.status_code == 302


def test_search_empty_query(client, db_session):
    _login(client, db_session)
    resp = client.get("/search?q=")
    assert resp.status_code == 200


def test_search_returns_results(client, db_session):
    _login(client, db_session)
    db_session.add(Customer(name="John Smith Auto"))
    db_session.commit()
    resp = client.get("/search?q=John")
    assert resp.status_code == 200


def test_kanban_requires_login(client):
    resp = client.get("/kanban", follow_redirects=False)
    assert resp.status_code == 302


def test_kanban_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/kanban")
    assert resp.status_code == 200


def test_logout_and_relogin(client, db_session):
    _login(client, db_session, username="u1", password="p1")
    resp = client.get("/dashboard")
    assert resp.status_code == 200

    client.get("/logout")
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302

    _login(client, db_session, username="u2", password="p2")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
