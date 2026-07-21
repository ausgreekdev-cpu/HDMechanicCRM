from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Date, Boolean, BigInteger, func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(200))
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    company = Column(String(200))
    phone = Column(String(50))
    email = Column(String(200))
    address = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    vehicles = relationship("Vehicle", back_populates="customer", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="customer")
    communications = relationship("Communication", back_populates="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    vin = Column(String(50))
    license_plate = Column(String(30))
    engine_type = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer", back_populates="vehicles")
    work_orders = relationship("WorkOrder", back_populates="vehicle")


class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(50))
    email = Column(String(200))
    specialization = Column(String(200))
    hourly_rate = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    schedules = relationship("Schedule", back_populates="technician")


class WorkOrderStatus(str, enum.Enum):
    NEW = "New"
    DIAGNOSING = "Diagnosing"
    WAITING_PARTS = "Waiting Parts"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    INVOICED = "Invoiced"
    CANCELLED = "Cancelled"


class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    diagnosis = Column(Text)
    status = Column(String(50), default=WorkOrderStatus.NEW.value)
    labor_hours = Column(Float, default=0)
    labor_rate = Column(Float, default=150)
    parts_total = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    odometer = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    notes = Column(Text)
    customer = relationship("Customer", back_populates="work_orders")
    vehicle = relationship("Vehicle", back_populates="work_orders")
    items = relationship("WorkOrderItem", back_populates="work_order", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="work_order")
    invoices = relationship("Invoice", back_populates="work_order")


class WorkOrderItem(Base):
    __tablename__ = "work_order_items"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    description = Column(String(500), nullable=False)
    part_used = Column(String(200))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    total_price = Column(Float, default=0)
    is_labor = Column(Boolean, default=False)
    work_order = relationship("WorkOrder", back_populates="items")


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(String(10))
    end_time = Column(String(10))
    notes = Column(Text)
    status = Column(String(50), default="Scheduled")
    created_at = Column(DateTime, server_default=func.now())
    work_order = relationship("WorkOrder", back_populates="schedules")
    technician = relationship("Technician", back_populates="schedules")


class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    part_number = Column(String(100))
    barcode = Column(String(100))
    category = Column(String(100))
    supplier = Column(String(200))
    supplier_part_number = Column(String(100))
    cost_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    quantity_on_hand = Column(Integer, default=0)
    min_quantity = Column(Integer, default=5)
    max_quantity = Column(Integer, default=0)
    location = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class PartTransaction(Base):
    __tablename__ = "part_transactions"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    quantity_change = Column(Integer, nullable=False)
    transaction_type = Column(String(50))
    reference = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(50), unique=True)
    subtotal = Column(Float, default=0)
    tax_rate = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    amount_paid = Column(Float, default=0)
    status = Column(String(50), default="Unpaid")
    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime)
    notes = Column(Text)
    work_order = relationship("WorkOrder", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class ScrapVendor(Base):
    __tablename__ = "scrap_vendors"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(200))
    phone = Column(String(50))
    email = Column(String(200))
    address = Column(Text)
    material_types = Column(String(500))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    pickups = relationship("ScrapPickup", back_populates="vendor")


class ScrapPickup(Base):
    __tablename__ = "scrap_pickups"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("scrap_vendors.id"), nullable=False)
    pickup_date = Column(Date, nullable=False)
    material_type = Column(String(100), nullable=False)
    weight_kg = Column(Float, nullable=False)
    price_per_kg = Column(Float, default=0)
    total_payout = Column(Float, default=0)
    location = Column(String(300))
    notes = Column(Text)
    status = Column(String(50), default="Completed")
    created_at = Column(DateTime, server_default=func.now())
    vendor = relationship("ScrapVendor", back_populates="pickups")


class ScrapInventory(Base):
    __tablename__ = "scrap_inventory"
    id = Column(Integer, primary_key=True)
    material_type = Column(String(100), nullable=False, unique=True)
    weight_kg = Column(Float, default=0)
    estimated_value = Column(Float, default=0)
    notes = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    company = Column(String(200))
    phone = Column(String(50))
    email = Column(String(200))
    source = Column(String(100))
    status = Column(String(50), default="New")
    interest = Column(String(300))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Communication(Base):
    __tablename__ = "communications"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    comm_type = Column(String(50))
    subject = Column(String(300))
    body = Column(Text)
    direction = Column(String(20), default="Outbound")
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer", back_populates="communications")
    lead = relationship("Lead")


class ServiceReminder(Base):
    __tablename__ = "service_reminders"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    service_type = Column(String(100), nullable=False)
    interval_miles = Column(Integer)
    interval_days = Column(Integer)
    last_odometer = Column(Integer)
    last_service_date = Column(Date)
    next_due_miles = Column(BigInteger)
    next_due_date = Column(Date)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vehicle = relationship("Vehicle")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    message = Column(Text)
    severity = Column(String(20), default="info")
    related_id = Column(Integer)
    related_type = Column(String(50))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    po_number = Column(String(50), unique=True)
    supplier = Column(String(200), nullable=False)
    status = Column(String(50), default="Pending")
    order_date = Column(Date, nullable=False)
    received_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    part_name = Column(String(300))
    part_number = Column(String(100))
    quantity_ordered = Column(Integer, default=1)
    quantity_received = Column(Integer, default=0)
    unit_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    part = relationship("Part")


class DVIInspection(Base):
    __tablename__ = "dvi_inspections"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    odometer = Column(Integer)
    inspection_date = Column(Date, nullable=False)
    summary = Column(Text)
    status = Column(String(50), default="Draft")
    created_at = Column(DateTime, server_default=func.now())
    items = relationship("DVIChecklistItem", back_populates="inspection", cascade="all, delete-orphan")
    vehicle = relationship("Vehicle")
    work_order = relationship("WorkOrder")
    technician = relationship("Technician")


class DVIChecklistItem(Base):
    __tablename__ = "dvi_checklist_items"
    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("dvi_inspections.id"), nullable=False)
    category = Column(String(100))
    check_item = Column(String(300), nullable=False)
    result = Column(String(50), default="Not Checked")
    notes = Column(Text)
    inspection = relationship("DVIInspection", back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(80))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="Cash")
    reference = Column(String(200))
    paid_at = Column(DateTime, server_default=func.now())
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    invoice = relationship("Invoice", back_populates="payments")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    filename = Column(String(300), nullable=False)
    original_name = Column(String(300))
    file_size = Column(Integer)
    content_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    uploader = relationship("User")


class RecurringWorkOrder(Base):
    __tablename__ = "recurring_work_orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    interval_days = Column(Integer, default=30)
    interval_miles = Column(Integer)
    labor_hours = Column(Float, default=1)
    labor_rate = Column(Float, default=150)
    is_active = Column(Boolean, default=True)
    next_due_date = Column(Date)
    last_generated = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    vehicle = relationship("Vehicle")
