"""Smoke: routes touched by the phase-1 pagination/import fixes still respond.

Every route must return 200/302 (auth redirects are fine) and never 5xx.
"""
import pytest

from app.auth import hash_password
from app.database import SessionLocal
from app.models import User

ROUTES = [
    "/admin/users",
    "/alerts",
    "/service-reminders",
    "/recurring-work-orders",
    "/reports/technician-efficiency",
    "/finance/credit-memos",
    "/finance/deposits",
    "/finance/ar-aging",
    "/finance/budgets",
    "/finance/late-fee-rules",
    "/finance/bank-accounts",
    "/finance/contractors",
    "/finance/tax-exemptions",
    "/finance/customer-statements",
    "/finance/revenue-by-category",
    "/inv/warehouses",
    "/inv/bins",
    "/inv/serial-numbers",
    "/inv/kits",
    "/inv/cycle-counts",
    "/inv/transfers",
    "/marketplace/",
    "/sms/templates",
    "/crm/saved-filters",
    "/crm/dashboard-widgets",
    "/portal/login",
    "/portal/dashboard",
    "/api/analytics/dashboard",
    "/api/analytics/features",
    "/backup",
    "/api/chart/revenue",
    "/api/chart/scrap",
    "/api/chart/wo-status",
    "/dashboard",
    "/",
    "/health",
    "/reports",
    "/search?q=test",
]


@pytest.fixture
def auth_client(client):
    db = SessionLocal()
    db.add(User(username="admin", password_hash=hash_password("adminpw"),
                display_name="Admin", role="admin", is_active=True))
    db.commit()
    db.close()
    resp = client.post("/login", data={"username": "admin", "password": "adminpw"})
    assert resp.status_code == 302, f"login failed: {resp.status_code}"
    return client


@pytest.mark.parametrize("path", ROUTES)
def test_get_route_ok(auth_client, path):
    resp = auth_client.get(path)
    assert resp.status_code in (200, 302), (
        f"{path} returned {resp.status_code}: "
        f"{resp.get_data(as_text=True)[:200]}"
    )
