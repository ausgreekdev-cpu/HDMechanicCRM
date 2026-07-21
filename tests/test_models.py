import pytest
from datetime import datetime, date
from app.models import (
    User, Customer, Vehicle, WorkOrder, Part, Technician,
    Invoice, ScrapVendor, ScrapPickup, Lead, Alert,
)
from app.auth import hash_password


def test_user_creation_defaults(db_session):
    u = User(username="alice", password_hash=hash_password("pass"), role="user")
    db_session.add(u)
    db_session.commit()
    assert u.id is not None
    assert u.is_active is True
    assert u.created_at is not None


def test_customer_creation(db_session):
    c = Customer(name="Acme Corp", phone="555-1234", email="acme@test.com")
    db_session.add(c)
    db_session.commit()
    assert c.id is not None
    assert c.name == "Acme Corp"
    assert c.created_at is not None
    assert c.updated_at is not None


def test_vehicle_belongs_to_customer(db_session):
    c = Customer(name="Bob's Shop")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Toyota", model="Camry", year=2022)
    db_session.add(v)
    db_session.commit()
    assert v.customer_id == c.id
    assert v.make == "Toyota"
    assert v.year == 2022


def test_work_order_defaults(db_session):
    c = Customer(name="Test Customer")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Ford", model="F-150")
    db_session.add(v)
    db_session.flush()
    wo = WorkOrder(customer_id=c.id, vehicle_id=v.id, title="Oil Change")
    db_session.add(wo)
    db_session.commit()
    assert wo.status == "New"
    assert wo.labor_hours == 0
    assert wo.labor_rate == 150
    assert wo.created_at is not None


def test_part_defaults(db_session):
    p = Part(name="Brake Pad")
    db_session.add(p)
    db_session.commit()
    assert p.id is not None
    assert p.quantity_on_hand == 0
    assert p.min_quantity == 5
    assert p.cost_price == 0
    assert p.selling_price == 0


def test_technician_defaults(db_session):
    t = Technician(name="Mike", hourly_rate=85)
    db_session.add(t)
    db_session.commit()
    assert t.is_active is True
    assert t.hourly_rate == 85


def test_customer_vehicles_relationship(db_session):
    c = Customer(name="Fleet Owner")
    db_session.add(c)
    db_session.flush()
    db_session.add(Vehicle(customer_id=c.id, make="Kenworth", model="T680"))
    db_session.add(Vehicle(customer_id=c.id, make="Peterbilt", model="579"))
    db_session.commit()
    db_session.refresh(c)
    assert len(c.vehicles) == 2


def test_invoice_defaults(db_session):
    inv = Invoice(invoice_number="INV-001")
    db_session.add(inv)
    db_session.commit()
    assert inv.status == "Unpaid"
    assert inv.subtotal == 0
    assert inv.tax_amount == 0
    assert inv.total_amount == 0
    assert inv.paid_at is None


def test_alert_defaults(db_session):
    a = Alert(alert_type="low_stock", title="Low Stock Alert", message="Brake pads low")
    db_session.add(a)
    db_session.commit()
    assert a.is_read is False
    assert a.severity == "info"
    assert a.created_at is not None
