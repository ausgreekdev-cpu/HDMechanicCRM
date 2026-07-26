from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base


class CustomerPortalUser(Base):
    __tablename__ = "customer_portal_users"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    email = Column(String(200), nullable=False)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    tokens = relationship("CustomerPortalToken", back_populates="portal_user", cascade="all, delete-orphan")
    messages = relationship("CustomerPortalMessage", back_populates="portal_user")


class CustomerPortalToken(Base):
    __tablename__ = "customer_portal_tokens"
    id = Column(Integer, primary_key=True)
    portal_user_id = Column(Integer, ForeignKey("customer_portal_users.id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    portal_user = relationship("CustomerPortalUser", back_populates="tokens")


class CustomerPortalMessage(Base):
    __tablename__ = "customer_portal_messages"
    id = Column(Integer, primary_key=True)
    portal_user_id = Column(Integer, ForeignKey("customer_portal_users.id"), nullable=False)
    subject = Column(String(300))
    body = Column(Text, nullable=False)
    direction = Column(String(20), default="customer")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    portal_user = relationship("CustomerPortalUser", back_populates="messages")
