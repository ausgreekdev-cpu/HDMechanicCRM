from sqlalchemy import Index
from app.database import engine
from app.models import Base

INDEXES = [
    # Core queries
    Index("idx_work_orders_status", "work_orders", "status"),
    Index("idx_work_orders_customer", "work_orders", "customer_id"),
    Index("idx_work_orders_vehicle", "work_orders", "vehicle_id"),
    Index("idx_work_orders_created", "work_orders", "created_at"),
    
    Index("idx_customers_name", "customers", "name"),
    Index("idx_customers_email", "customers", "email"),
    
    Index("idx_vehicles_customer", "vehicles", "customer_id"),
    Index("idx_vehicles_vin", "vehicles", "vin"),
    
    Index("idx_parts_name", "parts", "name"),
    Index("idx_parts_part_number", "parts", "part_number"),
    Index("idx_parts_category", "parts", "category"),
    
    Index("idx_invoices_status", "invoices", "status"),
    Index("idx_invoices_work_order", "invoices", "work_order_id"),
    
    Index("idx_schedules_date", "schedules", "scheduled_date"),
    Index("idx_schedules_technician", "schedules", "technician_id"),
    
    Index("idx_audit_logs_created", "audit_logs", "created_at"),
    Index("idx_audit_logs_entity", "audit_logs", "entity_type", "entity_id"),
    
    Index("idx_alerts_read", "alerts", "is_read"),
    Index("idx_alerts_type", "alerts", "alert_type"),
    
    Index("idx_scrap_pickups_date", "scrap_pickups", "pickup_date"),
    Index("idx_scrap_pickups_vendor", "scrap_pickups", "vendor_id"),
    
    Index("idx_part_transactions_part", "part_transactions", "part_id"),
    Index("idx_attachments_entity", "attachments", "entity_type", "entity_id"),
    
    Index("idx_recurring_wo_due", "recurring_work_orders", "next_due_date"),
]

def create_indexes():
    for idx in INDEXES:
        idx.create(bind=engine, checkfirst=True)
