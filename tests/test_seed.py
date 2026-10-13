"""Demo/marketplace seeds: functional and idempotent."""
from app.database import SessionLocal
from app.models import Alert, Customer, Invoice, Lead, WorkOrder
from app.models.templates import SubscriptionPlan, WorkflowTemplate


def _counts():
    db = SessionLocal()
    counts = {
        "customers": db.query(Customer).count(),
        "work_orders": db.query(WorkOrder).count(),
        "invoices": db.query(Invoice).count(),
        # Leads are created near the end of seed_demo_data — if the seed
        # crashes mid-way (e.g. the Decimal+float regression), they are 0.
        "leads": db.query(Lead).count(),
        "alerts": db.query(Alert).count(),
    }
    db.close()
    return counts


def test_seed_demo_data_completes_and_is_idempotent(app):
    from app.seed import seed_demo_data

    seed_demo_data()
    first = _counts()
    assert first["customers"] == 20
    assert first["work_orders"] > 0
    assert first["leads"] > 0
    assert first["alerts"] > 0

    seed_demo_data()  # customers exist -> guard skips
    assert _counts() == first


def test_seed_template_data_completes_and_is_idempotent(app):
    from app.seed import seed_template_data

    seed_template_data()
    db = SessionLocal()
    templates = db.query(WorkflowTemplate).count()
    plans = db.query(SubscriptionPlan).count()
    db.close()
    assert templates > 0
    assert plans > 0

    seed_template_data()
    db = SessionLocal()
    assert db.query(WorkflowTemplate).count() == templates
    assert db.query(SubscriptionPlan).count() == plans
    db.close()
