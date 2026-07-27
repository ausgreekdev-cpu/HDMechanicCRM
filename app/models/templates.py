import enum
from datetime import datetime, timedelta
from app.timeutils import utcnow
from sqlalchemy import (
    Column, Integer, String, Text, Float, Numeric, Boolean, DateTime, Date,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class TemplateCategory(Base):
    __tablename__ = "template_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    icon = Column(String(50), default="bi-folder")
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    templates = relationship("WorkflowTemplate", back_populates="category")


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("template_categories.id"))
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    long_description = Column(Text, default="")
    icon = Column(String(50), default="bi-gear")

    tier = Column(String(20), default="free")  # free, pro, enterprise, premium
    price = Column(Numeric(10,2), default=0.0)  # 0 = free, >0 = micro-transaction price

    steps = Column(JSON, default=list)
    checklist = Column(JSON, default=list)
    estimated_time = Column(String(50), default="30 min")
    difficulty = Column(String(20), default="Beginner")  # Beginner, Intermediate, Advanced
    tags = Column(String(500), default="")
    thumbnail = Column(String(200), default="")

    purchase_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("TemplateCategory", back_populates="templates")
    purchases = relationship("TemplatePurchase", back_populates="template")


class TemplatePurchase(Base):
    __tablename__ = "template_purchases"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("workflow_templates.id"), nullable=False)
    amount_paid = Column(Numeric(10,2), nullable=False)
    payment_method = Column(String(50), default="square")
    stripe_payment_id = Column(String(200), default="")
    status = Column(String(20), default="completed")  # completed, refunded, pending
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="template_purchases")
    template = relationship("WorkflowTemplate", back_populates="purchases")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    price_monthly = Column(Numeric(10,2), nullable=False)
    price_yearly = Column(Numeric(10,2), nullable=False)
    stripe_price_monthly = Column(String(100), default="")
    stripe_price_yearly = Column(String(100), default="")

    features = Column(JSON, default=list)
    template_access = Column(String(20), default="free")  # free, pro, enterprise, all
    max_users = Column(Integer, default=1)
    max_templates = Column(Integer, default=0)  # 0 = unlimited
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("UserSubscription", back_populates="plan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    status = Column(String(20), default="active")  # active, canceled, past_due, trialing
    stripe_subscription_id = Column(String(200), default="")
    stripe_customer_id = Column(String(200), default="")
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime)
    cancel_at = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    @property
    def is_active(self):
        if self.status in ("canceled", "past_due"):
            return False
        if self.current_period_end and self.current_period_end < utcnow():
            return False
        return True

    @property
    def days_remaining(self):
        if not self.current_period_end:
            return 0
        delta = self.current_period_end - utcnow()
        return max(0, delta.days)
