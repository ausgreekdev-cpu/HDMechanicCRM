import pytest
from datetime import datetime, date
from app.models import (
    User, Customer, Vehicle, WorkOrder, Part, Technician,
    Invoice, ScrapVendor, ScrapPickup, Lead, Alert,
    WorkOrderItem, Payment, Schedule, Estimate, Vendor,
    FuelRecord, TimeEntry, RecurringWorkOrder, ServiceReminder,
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


def test_work_order_item_creation(db_session):
    c = Customer(name="WO Cust")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Test", model="Car")
    db_session.add(v)
    db_session.flush()
    wo = WorkOrder(customer_id=c.id, vehicle_id=v.id, title="Test WO")
    db_session.add(wo)
    db_session.flush()
    item = WorkOrderItem(work_order_id=wo.id, description="Labor", quantity=2, unit_price=100, total_price=200)
    db_session.add(item)
    db_session.commit()
    assert item.id is not None
    assert item.description == "Labor"
    assert item.quantity == 2
    assert item.unit_price == 100


def test_payment_creation(db_session):
    c = Customer(name="Pay Cust")
    v = Vehicle(customer_id=1, make="Test", model="Car")
    db_session.add(c)
    db_session.add(v)
    db_session.flush()
    wo = WorkOrder(customer_id=c.id, vehicle_id=v.id, title="Work")
    db_session.add(wo)
    db_session.flush()
    inv = Invoice(work_order_id=wo.id, invoice_number="INV-001", total_amount=500)
    db_session.add(inv)
    db_session.flush()
    pay = Payment(invoice_id=inv.id, amount=250, payment_method="Cash")
    db_session.add(pay)
    db_session.commit()
    assert pay.id is not None
    assert pay.amount == 250


def test_schedule_creation(db_session):
    tech = Technician(name="Tech 1")
    c = Customer(name="Sched Cust")
    v = Vehicle(customer_id=1, make="Test", model="Car")
    db_session.add(c)
    db_session.add(v)
    db_session.flush()
    wo = WorkOrder(customer_id=c.id, vehicle_id=v.id, title="Work")
    db_session.add(wo)
    db_session.add(tech)
    db_session.flush()
    sched = Schedule(work_order_id=wo.id, technician_id=tech.id, scheduled_date=date.today())
    db_session.add(sched)
    db_session.commit()
    assert sched.id is not None
    assert sched.status == "Scheduled"


def test_estimate_creation(db_session):
    c = Customer(name="Est Customer")
    v = Vehicle(customer_id=1, make="Test", model="Car")
    db_session.add(c)
    db_session.add(v)
    db_session.flush()
    est = Estimate(customer_id=c.id, vehicle_id=v.id, title="Repair", labor_hours=5, labor_rate=120)
    db_session.add(est)
    db_session.commit()
    assert est.status == "Draft"
    assert est.labor_hours == 5


def test_vendor_creation(db_session):
    v = Vendor(name="Parts Co", contact_person="John", phone="555-0000")
    db_session.add(v)
    db_session.commit()
    assert v.id is not None
    assert v.is_active is True


def test_fuel_record_creation(db_session):
    c = Customer(name="Fuel Cust")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Truck", model="Big")
    db_session.add(v)
    db_session.flush()
    fr = FuelRecord(vehicle_id=v.id, fuel_date=date.today(), gallons=50, price_per_gallon=4.50, odometer=100000)
    db_session.add(fr)
    db_session.commit()
    assert fr.id is not None
    assert fr.gallons == 50
    assert fr.price_per_gallon == 4.50


def test_time_entry_creation(db_session):
    c = Customer(name="Time Cust")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Test", model="Car")
    db_session.add(v)
    db_session.flush()
    wo = WorkOrder(customer_id=c.id, vehicle_id=v.id, title="Time Test")
    tech = Technician(name="Timer")
    db_session.add(wo)
    db_session.add(tech)
    db_session.flush()
    from app.timeutils import utcnow
    te = TimeEntry(work_order_id=wo.id, technician_id=tech.id, clock_in=utcnow())
    db_session.add(te)
    db_session.commit()
    assert te.id is not None


def test_recurring_work_order_creation(db_session):
    c = Customer(name="Recurring Cust")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Test", model="Car")
    db_session.add(v)
    db_session.flush()
    rwo = RecurringWorkOrder(customer_id=c.id, vehicle_id=v.id, title="Monthly PM", interval_days=30)
    db_session.add(rwo)
    db_session.commit()
    assert rwo.is_active is True


def test_service_reminder_creation(db_session):
    c = Customer(name="Reminder Cust")
    db_session.add(c)
    db_session.flush()
    v = Vehicle(customer_id=c.id, make="Test", model="Car")
    db_session.add(v)
    db_session.flush()
    sr = ServiceReminder(vehicle_id=v.id, service_type="Oil Change", interval_days=90)
    db_session.add(sr)
    db_session.commit()
    assert sr.id is not None


def test_scrap_vendor_creation(db_session):
    sv = ScrapVendor(name="Scrap Yard", contact_person="Bob", phone="555-1111")
    db_session.add(sv)
    db_session.commit()
    assert sv.id is not None


def test_scrap_pickup_creation(db_session):
    sv = ScrapVendor(name="Scrap Yard")
    db_session.add(sv)
    db_session.flush()
    sp = ScrapPickup(vendor_id=sv.id, pickup_date=date.today(), material_type="Steel", weight_kg=1000, price_per_kg=0.50, total_payout=500)
    db_session.add(sp)
    db_session.commit()
    assert sp.total_payout == 500


def test_lead_creation(db_session):
    lead = Lead(name="New Lead", source="Website", status="New")
    db_session.add(lead)
    db_session.commit()
    assert lead.id is not None


def test_user_role_hierarchy(db_session):
    admin = User(username="admin1", password_hash=hash_password("x"), role="admin")
    mgr = User(username="mgr1", password_hash=hash_password("x"), role="manager")
    tech = User(username="tech1", password_hash=hash_password("x"), role="technician")
    user = User(username="user1", password_hash=hash_password("x"), role="user")
    db_session.add_all([admin, mgr, tech, user])
    db_session.commit()
    assert admin.role == "admin"
    assert mgr.role == "manager"
