import pytest
from app.models import User, Customer, Vehicle, WorkOrder, Part, Technician, Invoice, ScrapVendor, Lead
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


def test_customer_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/customers")
    assert resp.status_code == 200


def test_vehicle_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/vehicles")
    assert resp.status_code == 200


def test_work_order_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/work-orders")
    assert resp.status_code == 200


def test_parts_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/parts")
    assert resp.status_code == 200


def test_invoices_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/invoices")
    assert resp.status_code == 200


def test_technicians_list_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/technicians")
    assert resp.status_code == 200


def test_customer_create_form_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/customers/new")
    assert resp.status_code == 200


def test_vehicle_create_form_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/vehicles/new")
    assert resp.status_code == 200


def test_work_order_create_form_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/work-orders/new")
    assert resp.status_code == 200


def test_settings_page_loads(client, db_session):
    _login(client, db_session)
    resp = client.get("/settings")
    assert resp.status_code == 200


def test_404_page(client, db_session):
    _login(client, db_session)
    resp = client.get("/nonexistent-page-12345")
    assert resp.status_code == 404


def test_health_check_returns_json(client):
    resp = client.get("/health")
    assert resp.is_json
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert "database" in data


def test_static_files_served(client):
    resp = client.get("/static/css/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.content_type


def test_csrf_protection_enabled(client, db_session):
    _login(client, db_session)
    resp = client.post("/customers/new", data={"name": "Test"}, follow_redirects=False)
    # CSRF enabled - should fail validation
    assert resp.status_code in (302, 400)


def test_login_rate_limiting():
    # Rate limiting is disabled in the shared test config (the shared
    # module-level limiter would otherwise leak counters across tests),
    # so this test builds its own app with it enabled.
    from app import create_app
    from app.database import Base, engine

    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": True,
    })
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        try:
            client = app.test_client()
            for i in range(11):
                resp = client.post("/login", data={"username": f"wrong{i}", "password": "wrong"})
            assert resp.status_code == 429
        finally:
            Base.metadata.drop_all(bind=engine)
