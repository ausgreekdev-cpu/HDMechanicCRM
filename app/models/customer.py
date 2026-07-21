from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(300))
    body_text = Column(Text)
    status = Column(String(50), default="Sent")
    related_type = Column(String(50))
    related_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class SMSLog(Base):
    __tablename__ = "sms_logs"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    phone = Column(String(50), nullable=False)
    message = Column(Text)
    status = Column(String(50), default="Sent")
    related_type = Column(String(50))
    related_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class CustomerSurvey(Base):
    __tablename__ = "customer_surveys"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    rating = Column(Integer, default=5)
    nps_score = Column(Integer)
    feedback = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    work_order = relationship("WorkOrder")
    customer = relationship("Customer")


class CustomerLoyaltyTier(Base):
    __tablename__ = "customer_loyalty_tiers"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    tier = Column(String(50), default="Standard")
    points = Column(Integer, default=0)
    discount_pct = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    appointment_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(String(50), default="Scheduled")
    source = Column(String(50), default="Staff")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    vehicle = relationship("Vehicle")
