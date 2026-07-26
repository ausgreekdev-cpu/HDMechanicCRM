from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base


class SMSMessage(Base):
    __tablename__ = "sms_messages"
    id = Column(Integer, primary_key=True)
    to_number = Column(String(50), nullable=False)
    from_number = Column(String(50))
    body = Column(Text, nullable=False)
    status = Column(String(30), default="queued")
    direction = Column(String(20), default="outbound")
    external_id = Column(String(100))
    error_message = Column(Text)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    work_order = relationship("WorkOrder")


class SMSTemplate(Base):
    __tablename__ = "sms_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    body_template = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class SMSQueue(Base):
    __tablename__ = "sms_queue"
    id = Column(Integer, primary_key=True)
    to_number = Column(String(50), nullable=False)
    body = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey("sms_templates.id"), nullable=True)
    status = Column(String(30), default="pending")
    scheduled_for = Column(DateTime)
    attempts = Column(Integer, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    sent_at = Column(DateTime)
    template = relationship("SMSTemplate")
