import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_database_url():
    env_url = os.environ.get("CRM_DATABASE_URL", "")
    if env_url:
        return env_url

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "crm.db")
    return f"sqlite:///{db_path}"


DATABASE_URL = _get_database_url()
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs = {
    "echo": os.environ.get("CRM_DB_ECHO", "0") == "1",
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = int(os.environ.get("CRM_DB_POOL_SIZE", "10"))
    _engine_kwargs["max_overflow"] = int(os.environ.get("CRM_DB_MAX_OVERFLOW", "20"))
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = int(os.environ.get("CRM_DB_POOL_RECYCLE", "3600"))

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    _ensure_indexes()


def _ensure_indexes():
    """Create indexes that may not exist yet (idempotent)."""
    index_statements = [
        # --- Core models ---
        "CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
        "CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active)",
        "CREATE INDEX IF NOT EXISTS ix_customers_name ON customers(name)",
        "CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers(phone)",
        "CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email)",
        "CREATE INDEX IF NOT EXISTS ix_vehicles_customer_id ON vehicles(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_vehicles_vin ON vehicles(vin)",
        "CREATE INDEX IF NOT EXISTS ix_vehicles_license_plate ON vehicles(license_plate)",
        "CREATE INDEX IF NOT EXISTS ix_work_orders_customer_id ON work_orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_work_orders_vehicle_id ON work_orders(vehicle_id)",
        "CREATE INDEX IF NOT EXISTS ix_work_orders_status ON work_orders(status)",
        "CREATE INDEX IF NOT EXISTS ix_work_orders_created_at ON work_orders(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_parts_name ON parts(name)",
        "CREATE INDEX IF NOT EXISTS ix_parts_part_number ON parts(part_number)",
        "CREATE INDEX IF NOT EXISTS ix_parts_category ON parts(category)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_work_order_id ON invoices(work_order_id)",
        "CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices(status)",
        "CREATE INDEX IF NOT EXISTS ix_scrap_pickups_vendor_id ON scrap_pickups(vendor_id)",
        "CREATE INDEX IF NOT EXISTS ix_scrap_pickups_pickup_date ON scrap_pickups(pickup_date)",
        "CREATE INDEX IF NOT EXISTS ix_scrap_pickups_status ON scrap_pickups(status)",
        "CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status)",
        "CREATE INDEX IF NOT EXISTS ix_leads_source ON leads(source)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_is_read ON alerts(is_read)",
        "CREATE INDEX IF NOT EXISTS ix_purchase_orders_status ON purchase_orders(status)",
        "CREATE INDEX IF NOT EXISTS ix_schedules_technician_id ON schedules(technician_id)",
        "CREATE INDEX IF NOT EXISTS ix_schedules_scheduled_date ON schedules(scheduled_date)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_payments_invoice_id ON payments(invoice_id)",
        "CREATE INDEX IF NOT EXISTS ix_attachments_entity ON attachments(entity_type, entity_id)",
        # --- Advanced models ---
        "CREATE INDEX IF NOT EXISTS ix_estimates_customer_id ON estimates(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_estimates_status ON estimates(status)",
        "CREATE INDEX IF NOT EXISTS ix_estimates_created_at ON estimates(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_estimate_items_estimate_id ON estimate_items(estimate_id)",
        "CREATE INDEX IF NOT EXISTS ix_warranties_entity ON warranties(entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS ix_warranty_claims_status ON warranty_claims(status)",
        "CREATE INDEX IF NOT EXISTS ix_warranty_claims_warranty_id ON warranty_claims(warranty_id)",
        "CREATE INDEX IF NOT EXISTS ix_vendors_is_active ON vendors(is_active)",
        "CREATE INDEX IF NOT EXISTS ix_vendor_quotes_vendor_id ON vendor_quotes(vendor_id)",
        "CREATE INDEX IF NOT EXISTS ix_vendor_quotes_status ON vendor_quotes(status)",
        "CREATE INDEX IF NOT EXISTS ix_dot_inspections_vehicle_id ON dot_inspections(vehicle_id)",
        "CREATE INDEX IF NOT EXISTS ix_dot_inspections_next_date ON dot_inspections(next_inspection_date)",
        "CREATE INDEX IF NOT EXISTS ix_tpm_contracts_customer_id ON tpm_contracts(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_tpm_contracts_status ON tpm_contracts(status)",
        "CREATE INDEX IF NOT EXISTS ix_fleet_groups_customer_id ON fleet_groups(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_tire_records_vehicle_id ON tire_records(vehicle_id)",
        "CREATE INDEX IF NOT EXISTS ix_fuel_records_vehicle_id ON fuel_records(vehicle_id)",
        "CREATE INDEX IF NOT EXISTS ix_diesel_emission_records_vehicle_id ON diesel_emission_records(vehicle_id)",
        "CREATE INDEX IF NOT EXISTS ix_digital_signatures_entity ON digital_signatures(entity_type, entity_id)",
        # --- Finance models ---
        "CREATE INDEX IF NOT EXISTS ix_credit_memos_customer_id ON credit_memos(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_credit_memos_status ON credit_memos(status)",
        "CREATE INDEX IF NOT EXISTS ix_customer_deposits_customer_id ON customer_deposits(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_bank_transactions_account_id ON bank_transactions(account_id)",
        "CREATE INDEX IF NOT EXISTS ix_bank_transactions_date ON bank_transactions(transaction_date)",
        "CREATE INDEX IF NOT EXISTS ix_expenses_work_order_id ON expenses(work_order_id)",
        "CREATE INDEX IF NOT EXISTS ix_expenses_date ON expenses(expense_date)",
        "CREATE INDEX IF NOT EXISTS ix_payment_gateway_transactions_invoice_id ON payment_gateway_transactions(invoice_id)",
        "CREATE INDEX IF NOT EXISTS ix_payment_gateway_transactions_status ON payment_gateway_transactions(status)",
        # --- Inventory models ---
        "CREATE INDEX IF NOT EXISTS ix_bin_locations_warehouse_id ON bin_locations(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS ix_bin_locations_part_id ON bin_locations(part_id)",
        "CREATE INDEX IF NOT EXISTS ix_serial_numbers_part_id ON serial_numbers(part_id)",
        "CREATE INDEX IF NOT EXISTS ix_serial_numbers_status ON serial_numbers(status)",
        "CREATE INDEX IF NOT EXISTS ix_kit_items_kit_id ON kit_items(kit_id)",
        "CREATE INDEX IF NOT EXISTS ix_inventory_transfers_part_id ON inventory_transfers(part_id)",
        # --- Customer models ---
        "CREATE INDEX IF NOT EXISTS ix_email_logs_customer_id ON email_logs(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_email_logs_status ON email_logs(status)",
        "CREATE INDEX IF NOT EXISTS ix_sms_logs_customer_id ON sms_logs(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_appointments_customer_id ON appointments(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_appointments_date ON appointments(appointment_date)",
        "CREATE INDEX IF NOT EXISTS ix_appointments_status ON appointments(status)",
        "CREATE INDEX IF NOT EXISTS ix_customer_loyalty_tiers_customer_id ON customer_loyalty_tiers(customer_id)",
        # --- Productivity models ---
        "CREATE INDEX IF NOT EXISTS ix_time_entries_work_order_id ON time_entries(work_order_id)",
        "CREATE INDEX IF NOT EXISTS ix_time_entries_technician_id ON time_entries(technician_id)",
        "CREATE INDEX IF NOT EXISTS ix_push_notifications_user_id ON push_notifications(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_push_notifications_is_read ON push_notifications(is_read)",
        "CREATE INDEX IF NOT EXISTS ix_technician_certifications_technician_id ON technician_certifications(technician_id)",
        "CREATE INDEX IF NOT EXISTS ix_technician_certifications_expiry ON technician_certifications(expiry_date)",
        "CREATE INDEX IF NOT EXISTS ix_workflow_rules_trigger ON workflow_rules(trigger_event)",
        "CREATE INDEX IF NOT EXISTS ix_workflow_rules_is_active ON workflow_rules(is_active)",
        # --- Templates / Marketplace models ---
        "CREATE INDEX IF NOT EXISTS ix_workflow_templates_category_id ON workflow_templates(category_id)",
        "CREATE INDEX IF NOT EXISTS ix_workflow_templates_tier ON workflow_templates(tier)",
        "CREATE INDEX IF NOT EXISTS ix_workflow_templates_is_featured ON workflow_templates(is_featured)",
        "CREATE INDEX IF NOT EXISTS ix_workflow_templates_is_active ON workflow_templates(is_active)",
        "CREATE INDEX IF NOT EXISTS ix_template_purchases_user_id ON template_purchases(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_template_purchases_template_id ON template_purchases(template_id)",
        "CREATE INDEX IF NOT EXISTS ix_template_purchases_status ON template_purchases(status)",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status)",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_period_end ON user_subscriptions(current_period_end)",
        # --- Analytics models ---
        "CREATE INDEX IF NOT EXISTS ix_app_sessions_user_id ON app_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_app_sessions_started_at ON app_sessions(started_at)",
        "CREATE INDEX IF NOT EXISTS ix_page_views_session_id ON page_views(session_id)",
        "CREATE INDEX IF NOT EXISTS ix_page_views_created_at ON page_views(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_feature_usage_user_id ON feature_usage(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_feature_usage_feature ON feature_usage(feature)",
        "CREATE INDEX IF NOT EXISTS ix_crash_reports_is_resolved ON crash_reports(is_resolved)",
        "CREATE INDEX IF NOT EXISTS ix_daily_metrics_date ON daily_metrics(metric_date)",
        # --- Portal models ---
        "CREATE INDEX IF NOT EXISTS ix_portal_users_customer_id ON customer_portal_users(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_portal_users_email ON customer_portal_users(email)",
        "CREATE INDEX IF NOT EXISTS ix_portal_tokens_user_id ON customer_portal_tokens(portal_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_portal_tokens_is_used ON customer_portal_tokens(is_used)",
        "CREATE INDEX IF NOT EXISTS ix_portal_messages_user_id ON customer_portal_messages(portal_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_portal_messages_is_read ON customer_portal_messages(is_read)",
        # --- SMS models ---
        "CREATE INDEX IF NOT EXISTS ix_sms_messages_customer_id ON sms_messages(customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_sms_messages_status ON sms_messages(status)",
        "CREATE INDEX IF NOT EXISTS ix_sms_messages_created_at ON sms_messages(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_sms_queue_status ON sms_queue(status)",
        "CREATE INDEX IF NOT EXISTS ix_sms_queue_scheduled ON sms_queue(scheduled_for)",
    ]

    with engine.connect() as conn:
        for stmt in index_statements:
            try:
                conn.execute(stmt if isinstance(stmt, str) else stmt)
            except Exception:
                pass  # Table may not exist yet
        conn.commit()
