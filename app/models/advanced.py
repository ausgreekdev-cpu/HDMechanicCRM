from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Date, Boolean, BigInteger, func
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    legal_name = Column(String(300))
    tax_id = Column(String(100))
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(200))
    website = Column(String(200))
    logo_filename = Column(String(300))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class DigitalSignature(Base):
    __tablename__ = "digital_signatures"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    signatory_name = Column(String(200), nullable=False)
    signature_data = Column(Text, nullable=False)
    signed_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(50))


class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True)
    estimate_number = Column(String(50), unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    labor_hours = Column(Float, default=0)
    labor_rate = Column(Float, default=150)
    parts_total = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(String(50), default="Draft")
    expires_at = Column(Date)
    approved_at = Column(DateTime)
    converted_wo_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    vehicle = relationship("Vehicle")
    converted_wo = relationship("WorkOrder")
    items = relationship("EstimateItem", back_populates="estimate", cascade="all, delete-orphan")


class EstimateItem(Base):
    __tablename__ = "estimate_items"
    id = Column(Integer, primary_key=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    description = Column(String(500), nullable=False)
    part_used = Column(String(200))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    total_price = Column(Float, default=0)
    is_labor = Column(Boolean, default=False)
    estimate = relationship("Estimate", back_populates="items")


class PartCrossReference(Base):
    __tablename__ = "part_cross_references"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    cross_type = Column(String(50), default="OEM")
    cross_part_number = Column(String(100), nullable=False)
    cross_brand = Column(String(100))
    cross_description = Column(String(300))
    notes = Column(Text)
    part = relationship("Part")


class CoreCharge(Base):
    __tablename__ = "core_charges"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    charge_amount = Column(Float, default=0)
    is_refundable = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")
    returns = relationship("CoreReturn", back_populates="core_charge")


class CoreReturn(Base):
    __tablename__ = "core_returns"
    id = Column(Integer, primary_key=True)
    core_charge_id = Column(Integer, ForeignKey("core_charges.id"), nullable=False)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    returned_at = Column(DateTime, server_default=func.now())
    refund_amount = Column(Float, default=0)
    notes = Column(Text)
    core_charge = relationship("CoreCharge", back_populates="returns")
    work_order = relationship("WorkOrder")


class Warranty(Base):
    __tablename__ = "warranties"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    warranty_type = Column(String(50), default="Parts")
    duration_days = Column(Integer, default=365)
    duration_miles = Column(Integer)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    end_miles = Column(BigInteger)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    id = Column(Integer, primary_key=True)
    warranty_id = Column(Integer, ForeignKey("warranties.id"), nullable=False)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    claim_number = Column(String(50))
    status = Column(String(50), default="Open")
    description = Column(Text)
    labor_cost = Column(Float, default=0)
    parts_cost = Column(Float, default=0)
    total_claim = Column(Float, default=0)
    approved_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    warranty = relationship("Warranty")
    work_order = relationship("WorkOrder")


class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    contact_person = Column(String(200))
    phone = Column(String(50))
    email = Column(String(200))
    address = Column(Text)
    vendor_type = Column(String(100))
    payment_terms = Column(String(100))
    tax_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    rating = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    quotes = relationship("VendorQuote", back_populates="vendor")


class VendorQuote(Base):
    __tablename__ = "vendor_quotes"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    part_name = Column(String(300))
    part_number = Column(String(100))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    total_price = Column(Float, default=0)
    lead_days = Column(Integer)
    valid_until = Column(Date)
    status = Column(String(50), default="Pending")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vendor = relationship("Vendor", back_populates="quotes")
    part = relationship("Part")


class DieselEmissionRecord(Base):
    __tablename__ = "diesel_emission_records"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    record_type = Column(String(50), nullable=False)
    service_date = Column(Date, nullable=False)
    odometer = Column(BigInteger)
    description = Column(String(300))
    part_number = Column(String(100))
    cost = Column(Float, default=0)
    next_due_odometer = Column(BigInteger)
    next_due_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vehicle = relationship("Vehicle")


class TPMContract(Base):
    __tablename__ = "tpm_contracts"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    contract_number = Column(String(50), unique=True)
    title = Column(String(300), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    monthly_fee = Column(Float, default=0)
    included_services = Column(Text)
    excluded_services = Column(Text)
    max_hours_per_month = Column(Float, default=0)
    status = Column(String(50), default="Active")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")


class FleetGroup(Base):
    __tablename__ = "fleet_groups"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    billing_cycle = Column(String(50), default="Monthly")
    consolidated_billing = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("Customer")
    vehicles = relationship("FleetVehicle", back_populates="fleet_group")


class FleetVehicle(Base):
    __tablename__ = "fleet_vehicles"
    id = Column(Integer, primary_key=True)
    fleet_group_id = Column(Integer, ForeignKey("fleet_groups.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    unit_number = Column(String(50))
    assigned_driver = Column(String(200))
    fleet_group = relationship("FleetGroup", back_populates="vehicles")
    vehicle = relationship("Vehicle")


class TireRecord(Base):
    __tablename__ = "tire_records"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    position = Column(String(50))
    brand = Column(String(100))
    model = Column(String(100))
    size = Column(String(100))
    serial_number = Column(String(100))
    install_date = Column(Date)
    install_odometer = Column(BigInteger)
    removal_date = Column(Date)
    removal_odometer = Column(BigInteger)
    retread_count = Column(Integer, default=0)
    notes = Column(Text)
    vehicle = relationship("Vehicle")


class FuelRecord(Base):
    __tablename__ = "fuel_records"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    fuel_date = Column(Date, nullable=False)
    gallons = Column(Float, nullable=False)
    price_per_gallon = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    odometer = Column(BigInteger)
    fuel_type = Column(String(50), default="Diesel")
    vendor = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vehicle = relationship("Vehicle")


class EquipmentHourMeter(Base):
    __tablename__ = "equipment_hour_meters"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    hours = Column(Float, default=0)
    reading_date = Column(Date, server_default=func.now())
    notes = Column(Text)
    vehicle = relationship("Vehicle")


class DOTInspection(Base):
    __tablename__ = "dot_inspections"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    inspection_date = Column(Date, nullable=False)
    inspector = Column(String(200))
    inspection_type = Column(String(100))
    result = Column(String(50), default="Pass")
    odometer = Column(BigInteger)
    defects = Column(Text)
    next_inspection_date = Column(Date)
    certificate_number = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vehicle = relationship("Vehicle")


class ELDLog(Base):
    __tablename__ = "eld_logs"
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_name = Column(String(200))
    log_date = Column(Date, nullable=False)
    duty_status = Column(String(50))
    hours_driven = Column(Float, default=0)
    hours_on_duty = Column(Float, default=0)
    hours_off_duty = Column(Float, default=0)
    odometer_start = Column(BigInteger)
    odometer_end = Column(BigInteger)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    vehicle = relationship("Vehicle")
