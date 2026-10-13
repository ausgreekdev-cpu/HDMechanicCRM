"""Payment security tests: forgery resistance, server-side verification, webhooks."""
from datetime import datetime, timedelta

from app.auth import hash_password
from app.database import SessionLocal
from app.models import User
from app.models.templates import (
    SubscriptionPlan,
    TemplatePurchase,
    UserSubscription,
    WorkflowTemplate,
)
from tests.conftest import REFERER, get_csrf


def _add_user(username="buyer", password="BuyerPass1!"):
    db = SessionLocal()
    user = User(username=username, password_hash=hash_password(password),
                role="admin", is_active=True)
    db.add(user)
    db.commit()
    uid = user.id
    db.close()
    return uid, username, password


def _add_template(slug="sec-tpl", price=19.99, tier="paid"):
    db = SessionLocal()
    tmpl = WorkflowTemplate(name="SecTpl", slug=slug, tier=tier, price=price,
                            description="d")
    db.add(tmpl)
    db.commit()
    tid = tmpl.id
    db.close()
    return tid


def _add_plan(slug="secplan"):
    db = SessionLocal()
    plan = SubscriptionPlan(name="SecPlan", slug=slug, price_monthly=29.99,
                            price_yearly=299.0, description="d")
    db.add(plan)
    db.commit()
    pid = plan.id
    db.close()
    return pid


def _pending_purchase(uid, tid, amount=19.99, age_hours=None):
    db = SessionLocal()
    purchase = TemplatePurchase(user_id=uid, template_id=tid, amount_paid=amount,
                                status="pending")
    if age_hours is not None:
        purchase.created_at = datetime.utcnow() - timedelta(hours=age_hours)
    db.add(purchase)
    db.commit()
    purchase_id = purchase.id
    db.close()
    return purchase_id


def _login(client, username, password):
    token = get_csrf(client, "/login")
    resp = client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
        headers=REFERER,
    )
    assert resp.status_code == 302, f"login failed: {resp.status_code}"


class _Result:
    def __init__(self, body=None, success=True, errors=None):
        self.body = body or {}
        self._success = success
        self.errors = errors or []

    def is_success(self):
        return self._success


class _FakeSquareClient:
    def __init__(self, result):
        payments = self

        class _Payments:
            def list_payments(self, **kwargs):
                payments.last_kwargs = kwargs
                if isinstance(payments.result, Exception):
                    raise payments.result
                return payments.result

        self.result = result
        self.last_kwargs = None
        self.payments = _Payments()


def _find_completed_payment(amount_cents=1999, **kwargs):
    from app.payments_square import find_completed_payment
    return find_completed_payment(amount_cents, **kwargs)


# --- checkout ---------------------------------------------------------------

def test_checkout_without_csrf_token_rejected(csrf_client):
    uid, username, password = _add_user()
    tid = _add_template()
    _login(csrf_client, username, password)
    resp = csrf_client.post(f"/payments/checkout/template/{tid}")
    assert resp.status_code == 400


def test_demo_checkout_completes_inline_and_no_duplicates(csrf_client):
    uid, username, password = _add_user()
    tid = _add_template()
    _login(csrf_client, username, password)

    token = get_csrf(csrf_client, "/marketplace/template/sec-tpl")
    resp = csrf_client.post(
        f"/payments/checkout/template/{tid}",
        data={"csrf_token": token},
        headers=REFERER,
    )
    assert resp.status_code == 302

    db = SessionLocal()
    purchases = db.query(TemplatePurchase).filter_by(template_id=tid).all()
    assert len(purchases) == 1
    assert purchases[0].status == "completed"
    assert purchases[0].payment_method == "square_demo"
    assert purchases[0].user_id == uid
    tmpl = db.query(WorkflowTemplate).get(tid)
    assert tmpl.purchase_count == 1
    db.close()

    # Repeat attempt: already owned, still exactly one row.
    token = get_csrf(csrf_client, "/marketplace/template/sec-tpl")
    csrf_client.post(
        f"/payments/checkout/template/{tid}",
        data={"csrf_token": token},
        headers=REFERER,
    )
    db = SessionLocal()
    assert db.query(TemplatePurchase).filter_by(template_id=tid).count() == 1
    db.close()


# --- /payments/success forgery ----------------------------------------------

def test_forged_template_success_grants_nothing(csrf_client):
    uid, username, password = _add_user()
    tid = _add_template()
    _login(csrf_client, username, password)

    resp = csrf_client.get(f"/payments/success?source=template&item_id={tid}")
    assert resp.status_code == 302

    db = SessionLocal()
    assert db.query(TemplatePurchase).filter_by(template_id=tid).count() == 0
    db.close()


def test_forged_subscription_success_grants_nothing(csrf_client):
    uid, username, password = _add_user()
    pid = _add_plan()
    _login(csrf_client, username, password)

    resp = csrf_client.get(
        f"/payments/success?source=subscription&item_id={pid}&cycle=monthly"
    )
    assert resp.status_code == 302

    db = SessionLocal()
    assert db.query(UserSubscription).filter_by(user_id=uid).count() == 0
    db.close()


def test_success_requires_login(csrf_client):
    uid, username, password = _add_user()
    tid = _add_template()
    pending = _pending_purchase(uid, tid)

    resp = csrf_client.get(
        f"/payments/success?source=template&item_id={tid}&purchase_id={pending}"
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    db = SessionLocal()
    assert db.query(TemplatePurchase).get(pending).status == "pending"
    db.close()


def test_pending_not_activated_without_square_verification(csrf_client):
    # Square is disabled in tests (demo mode); demo never redirects to
    # /success, so an unverifiable pending row must stay pending.
    uid, username, password = _add_user()
    tid = _add_template()
    pending = _pending_purchase(uid, tid)
    _login(csrf_client, username, password)

    resp = csrf_client.get(
        f"/payments/success?source=template&item_id={tid}&purchase_id={pending}"
    )
    assert resp.status_code == 302

    db = SessionLocal()
    assert db.query(TemplatePurchase).get(pending).status == "pending"
    db.close()


def test_other_user_cannot_consume_pending(csrf_client):
    uid_a, _, _ = _add_user("usera", "UseraPass1!")
    uid_b, username_b, password_b = _add_user("userb", "UserbPass1!")
    tid = _add_template()
    pending = _pending_purchase(uid_a, tid)
    _login(csrf_client, username_b, password_b)

    csrf_client.get(
        f"/payments/success?source=template&item_id={tid}&purchase_id={pending}"
    )

    db = SessionLocal()
    purchase = db.query(TemplatePurchase).get(pending)
    assert purchase.status == "pending"
    assert purchase.user_id == uid_a
    db.close()


def test_expired_pending_rejected(csrf_client):
    uid, username, password = _add_user()
    tid = _add_template()
    pending = _pending_purchase(uid, tid, age_hours=25)
    _login(csrf_client, username, password)

    csrf_client.get(
        f"/payments/success?source=template&item_id={tid}&purchase_id={pending}"
    )

    db = SessionLocal()
    purchase = db.query(TemplatePurchase).get(pending)
    assert purchase.status == "expired"
    db.close()


def test_verified_grant_completes_purchase(csrf_client, monkeypatch):
    monkeypatch.setattr("app.routes.square_payments.square_enabled", lambda: True)
    monkeypatch.setattr(
        "app.routes.square_payments.find_completed_payment",
        lambda amount_cents, currency=None, exclude_ids=(): "sq_granted_1",
    )
    uid, username, password = _add_user()
    tid = _add_template()
    pending = _pending_purchase(uid, tid)
    _login(csrf_client, username, password)

    resp = csrf_client.get(
        f"/payments/success?source=template&item_id={tid}&purchase_id={pending}"
    )
    assert resp.status_code == 302

    db = SessionLocal()
    purchase = db.query(TemplatePurchase).get(pending)
    assert purchase.status == "completed"
    assert purchase.stripe_payment_id == "sq_granted_1"
    assert db.query(WorkflowTemplate).get(tid).purchase_count == 1
    db.close()


def test_verified_grant_activates_subscription(csrf_client, monkeypatch):
    monkeypatch.setattr("app.routes.square_payments.square_enabled", lambda: True)
    monkeypatch.setattr(
        "app.routes.square_payments.find_completed_payment",
        lambda amount_cents, currency=None, exclude_ids=(): "sq_granted_2",
    )
    uid, username, password = _add_user()
    pid = _add_plan()
    db = SessionLocal()
    sub = UserSubscription(user_id=uid, plan_id=pid, billing_cycle="monthly",
                           status="pending")
    db.add(sub)
    db.commit()
    sub_id = sub.id
    db.close()
    _login(csrf_client, username, password)

    resp = csrf_client.get(
        f"/payments/success?source=subscription&item_id={pid}&subscription_id={sub_id}"
    )
    assert resp.status_code == 302

    db = SessionLocal()
    sub = db.query(UserSubscription).get(sub_id)
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sq_granted_2"
    assert sub.current_period_end is not None
    db.close()


# --- webhook ----------------------------------------------------------------

def test_webhook_rejects_bad_signature(csrf_client, monkeypatch):
    monkeypatch.setenv("CRM_SQUARE_WEBHOOK_SIGNATURE_KEY", "whsec_test")
    resp = csrf_client.post(
        "/payments/webhook", data="{}", content_type="application/json",
        headers=REFERER,
    )
    assert resp.status_code == 401


def test_webhook_exempt_from_csrf(csrf_client, monkeypatch):
    # With a signature key set, a missing CSRF token must not produce a
    # 400 — the view runs and rejects via HMAC instead (401).
    monkeypatch.setenv("CRM_SQUARE_WEBHOOK_SIGNATURE_KEY", "whsec_test")
    resp = csrf_client.post(
        "/payments/webhook", data="{}", content_type="application/json",
    )
    assert resp.status_code == 401


# --- find_completed_payment unit tests --------------------------------------

def test_find_payment_disabled_returns_none(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: False)
    assert _find_completed_payment() is None


def test_find_payment_matching_completed(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: True)
    result = _Result(body={"payments": [
        {"id": "p1", "status": "COMPLETED",
         "amount_money": {"amount": 1999, "currency": "AUD"}},
    ]})
    monkeypatch.setattr("app.payments_square._client", lambda: _FakeSquareClient(result))
    assert _find_completed_payment(currency="AUD") == "p1"


def test_find_payment_skips_pending_and_wrong_amount(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: True)
    result = _Result(body={"payments": [
        {"id": "p_pending", "status": "PENDING",
         "amount_money": {"amount": 1999, "currency": "AUD"}},
        {"id": "p_wrong_amt", "status": "COMPLETED",
         "amount_money": {"amount": 500, "currency": "AUD"}},
        {"id": "p_ok", "status": "COMPLETED",
         "amount_money": {"amount": 1999, "currency": "AUD"}},
    ]})
    monkeypatch.setattr("app.payments_square._client", lambda: _FakeSquareClient(result))
    assert _find_completed_payment(currency="AUD") == "p_ok"


def test_find_payment_excludes_consumed_ids(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: True)
    result = _Result(body={"payments": [
        {"id": "p1", "status": "COMPLETED",
         "amount_money": {"amount": 1999, "currency": "AUD"}},
    ]})
    monkeypatch.setattr("app.payments_square._client", lambda: _FakeSquareClient(result))
    assert _find_completed_payment(currency="AUD", exclude_ids=["p1"]) is None


def test_find_payment_api_failure_returns_none(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: True)
    result = _Result(success=False, errors=["boom"])
    monkeypatch.setattr("app.payments_square._client", lambda: _FakeSquareClient(result))
    assert _find_completed_payment() is None


def test_find_payment_exception_returns_none(monkeypatch):
    monkeypatch.setattr("app.payments_square.square_enabled", lambda: True)
    monkeypatch.setattr(
        "app.payments_square._client",
        lambda: _FakeSquareClient(RuntimeError("network down")),
    )
    assert _find_completed_payment() is None
