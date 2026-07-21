from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship

from app.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    location = Column(String(300))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    bins = relationship("BinLocation", back_populates="warehouse")


class BinLocation(Base):
    __tablename__ = "bin_locations"
    id = Column(Integer, primary_key=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    bin_code = Column(String(100), nullable=False)
    max_capacity = Column(Integer, default=0)
    notes = Column(Text)
    warehouse = relationship("Warehouse", back_populates="bins")
    part = relationship("Part")


class SerialNumber(Base):
    __tablename__ = "serial_numbers"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    serial_number = Column(String(200), nullable=False, unique=True)
    status = Column(String(50), default="In Stock")
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")
    work_order = relationship("WorkOrder")
    purchase_order = relationship("PurchaseOrder")


class KitAssembly(Base):
    __tablename__ = "kit_assemblies"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    description = Column(Text)
    selling_price = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    items = relationship("KitItem", back_populates="kit", cascade="all, delete-orphan")


class KitItem(Base):
    __tablename__ = "kit_items"
    id = Column(Integer, primary_key=True)
    kit_id = Column(Integer, ForeignKey("kit_assemblies.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Integer, default=1)
    kit = relationship("KitAssembly", back_populates="items")
    part = relationship("Part")


class SupplierScorecard(Base):
    __tablename__ = "supplier_scorecards"
    id = Column(Integer, primary_key=True)
    supplier_name = Column(String(300), nullable=False)
    rating_date = Column(Date, nullable=False)
    on_time_delivery_pct = Column(Float, default=100)
    quality_rating = Column(Float, default=100)
    pricing_rating = Column(Float, default=100)
    overall_score = Column(Float, default=100)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class DropShipPO(Base):
    __tablename__ = "drop_ship_pos"
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    ship_to_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    ship_to_address = Column(Text)
    tracking_number = Column(String(200))
    notes = Column(Text)
    purchase_order = relationship("PurchaseOrder")
    ship_to_customer = relationship("Customer")


class PartSupersession(Base):
    __tablename__ = "part_supersessions"
    id = Column(Integer, primary_key=True)
    old_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    new_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    old_part_number = Column(String(100))
    new_part_number = Column(String(100))
    notes = Column(Text)
    superseded_at = Column(DateTime, server_default=func.now())
    old_part = relationship("Part", foreign_keys=[old_part_id])
    new_part = relationship("Part", foreign_keys=[new_part_id])


class NonStockItem(Base):
    __tablename__ = "non_stock_items"
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    description = Column(Text)
    supplier = Column(String(200))
    estimated_cost = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    lead_days = Column(Integer, default=7)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ConsignmentItem(Base):
    __tablename__ = "consignment_items"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    supplier = Column(String(200), nullable=False)
    quantity = Column(Integer, default=0)
    unit_cost = Column(Float, default=0)
    sold_quantity = Column(Integer, default=0)
    paid_quantity = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")


class CycleCount(Base):
    __tablename__ = "cycle_counts"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    counted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expected_qty = Column(Integer, default=0)
    actual_qty = Column(Integer, default=0)
    variance = Column(Integer, default=0)
    count_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")
    counter = relationship("User")


class InventoryTransfer(Base):
    __tablename__ = "inventory_transfers"
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    from_warehouse = Column(String(200))
    to_warehouse = Column(String(200))
    quantity = Column(Integer, nullable=False)
    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    part = relationship("Part")
    transferrer = relationship("User")
