from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship

from app.database import Base


class CreditMemo(Base):
    __tablename__ = "credit_memos"
    id = Column(Integer, primary_key=True)
    memo_number = Column(String(50), unique=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text)
    status = Column(String(50), default="Issued")
    created_at = Column(DateTime, server_default=func.now())
    invoice = relationship("Invoice")
    customer = relationship("Customer")


class CustomerDeposit(Base):
    __tablename__ = "customer_deposits"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    payment_method = Column(String(50))
    reference = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class TaxExemption(Base):
    __tablename__ = "tax_exemptions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    exemption_number = Column(String(100))
    jurisdiction = Column(String(200))
    certificate_file = Column(String(300))
    expires_at = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class Contractor1099(Base):
    __tablename__ = "contractors_1099"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    tax_id = Column(String(100))
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(200))
    total_paid_ytd = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    account_number = Column(String(100))
    routing_number = Column(String(50))
    account_type = Column(String(50), default="Checking")
    balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    transactions = relationship("BankTransaction", back_populates="account")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    description = Column(String(300))
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(50))
    reference = Column(String(200))
    reconciled = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    account = relationship("BankAccount", back_populates="transactions")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, nullable=False)
    vendor = Column(String(200))
    description = Column(Text)
    receipt_filename = Column(String(300))
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    work_order = relationship("WorkOrder")
    payer = relationship("User")


class LateFeeRule(Base):
    __tablename__ = "late_fee_rules"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    days_overdue = Column(Integer, default=30)
    fee_type = Column(String(50), default="Percentage")
    fee_value = Column(Float, default=5.0)
    max_fee = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class PaymentGatewayTransaction(Base):
    __tablename__ = "payment_gateway_transactions"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    gateway = Column(String(50), nullable=False)
    transaction_id = Column(String(200))
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50))
    response_data = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    invoice = relationship("Invoice")
    payment = relationship("Payment")


class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)
    category = Column(String(100))
    budgeted_amount = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
