import pytest
from app.auth import hash_password, verify_password, ROLE_HIERARCHY
from app.models import User


def test_hash_password_returns_string():
    h = hash_password("mypassword")
    assert isinstance(h, str)
    assert len(h) > 0


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_wrong():
    h = hash_password("secret123")
    assert verify_password("wrongpassword", h) is False


def test_role_hierarchy_ordering():
    assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["manager"]
    assert ROLE_HIERARCHY["manager"] > ROLE_HIERARCHY["tech"]
    assert ROLE_HIERARCHY["tech"] > ROLE_HIERARCHY["view-only"]


def test_login_required_redirects_unauthenticated(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_login_invalid_credentials(client, db_session):
    resp = client.post("/login", data={
        "username": "nonexistent",
        "password": "wrong"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_valid_credentials(client, db_session):
    u = User(
        username="testuser",
        password_hash=hash_password("testpass"),
        display_name="Test User",
        role="admin",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    resp = client.post("/login", data={
        "username": "testuser",
        "password": "testpass"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


def test_logout_clears_session(client, db_session):
    u = User(
        username="logouter",
        password_hash=hash_password("pass123"),
        role="user",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    client.post("/login", data={"username": "logouter", "password": "pass123"})
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp2 = client.get("/dashboard")
    assert resp2.status_code == 302
    assert "/login" in resp2.headers["Location"]
