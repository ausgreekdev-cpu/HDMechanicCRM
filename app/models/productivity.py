from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Date, Boolean, BigInteger, func
from sqlalchemy.orm import relationship

from app.database import Base


class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    clock_in = Column(DateTime, nullable=False)
    clock_out = Column(DateTime)
    total_hours = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    work_order = relationship("WorkOrder")
    technician = relationship("Technician")


class PushNotification(Base):
    __tablename__ = "push_notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text)
    related_type = Column(String(50))
    related_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")


class LaborStandard(Base):
    __tablename__ = "labor_standards"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    standard_hours = Column(Float, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    entity_type = Column(String(50), nullable=False)
    filter_data = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    widget_type = Column(String(100), nullable=False)
    title = Column(String(200))
    config = Column(Text)
    position = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")


class WorkflowRule(Base):
    __tablename__ = "workflow_rules"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    trigger_event = Column(String(100), nullable=False)
    conditions = Column(Text)
    actions = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class TechnicianCertification(Base):
    __tablename__ = "technician_certifications"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    name = Column(String(300), nullable=False)
    issuer = Column(String(200))
    cert_number = Column(String(100))
    issued_date = Column(Date)
    expiry_date = Column(Date)
    notes = Column(Text)
    technician = relationship("Technician")


class ShopSupply(Base):
    __tablename__ = "shop_supplies"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    category = Column(String(100))
    quantity_on_hand = Column(Integer, default=0)
    unit = Column(String(50), default="Each")
    min_quantity = Column(Integer, default=5)
    cost_per_unit = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class SDSDocument(Base):
    __tablename__ = "sds_documents"
    id = Column(Integer, primary_key=True)
    part_name = Column(String(300))
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    supplier = Column(String(200))
    filename = Column(String(300), nullable=False)
    original_name = Column(String(300))
    revision_date = Column(Date)
    notes = Column(Text)
    uploaded_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")


class CheckInRecord(Base):
    __tablename__ = "check_in_records"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    checked_in_by = Column(String(200))
    customer_name = Column(String(200))
    customer_signature = Column(Text)
    vehicle_condition = Column(Text)
    fuel_level = Column(String(20))
    odometer = Column(BigInteger)
    damage_notes = Column(Text)
    keys_received = Column(Boolean, default=True)
    checked_in_at = Column(DateTime, server_default=func.now())
    work_order = relationship("WorkOrder")


class Franchise(Base):
    __tablename__ = "franchises"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    location = Column(String(300))
    phone = Column(String(50))
    email = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class EnvironmentalRecord(Base):
    __tablename__ = "environmental_records"
    id = Column(Integer, primary_key=True)
    record_type = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String(500))
    quantity = Column(Float, default=0)
    unit = Column(String(50))
    vendor = Column(String(200))
    disposal_method = Column(String(200))
    cost = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
