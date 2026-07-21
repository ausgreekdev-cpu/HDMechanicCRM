import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import (
    WorkOrder, Invoice, Part, PartTransaction, Alert, ServiceReminder,
    Customer, ScrapPickup, ScrapInventory, Schedule
)

scheduler = BackgroundScheduler()


def _create_alert(atype, title, message, severity="info", related_id=None, related_type=None):
    db = SessionLocal()
    try:
        db.add(Alert(alert_type=atype, title=title, message=message,
                     severity=severity, related_id=related_id, related_type=related_type))
        db.commit()
    except Exception:
        logging.exception("Failed to create alert")
    finally:
        db.close()


def auto_invoice_completed():
    db = SessionLocal()
    try:
        wos = db.query(WorkOrder).filter(
            WorkOrder.status == "Completed", ~WorkOrder.invoices.any()
        ).all()
        for wo in wos:
            count = db.query(Invoice).count() + 1
            inv = Invoice(
                work_order_id=wo.id,
                invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m')}-{count:04d}",
                subtotal=wo.total_amount, tax_rate=0, tax_amount=0,
                total_amount=wo.total_amount, status="Unpaid"
            )
            db.add(inv)
            wo.status = "Invoiced"
            _create_alert("invoice_created", f"Invoice auto-generated for {wo.title}",
                          f"WO #{wo.id} completed — invoice INV-{datetime.utcnow().strftime('%Y%m')}-{count:04d} created",
                          "success", wo.id, "work_order")
        db.commit()
        if wos:
            logging.info("Auto-invoiced %d completed work orders", len(wos))
    except Exception:
        logging.exception("Auto-invoice failed")
    finally:
        db.close()


def check_low_stock():
    db = SessionLocal()
    try:
        parts = db.query(Part).filter(Part.quantity_on_hand <= Part.min_quantity).all()
        for p in parts:
            exists = db.query(Alert).filter(
                Alert.alert_type == "low_stock", Alert.is_read == False,
                Alert.related_id == p.id, Alert.related_type == "part"
            ).first()
            if not exists:
                _create_alert("low_stock", f"Low Stock: {p.name}",
                              f"Qty: {p.quantity_on_hand} / Min: {p.min_quantity} — {p.location or 'No location'}",
                              "warning", p.id, "part")
    except Exception:
        logging.exception("Low stock check failed")
    finally:
        db.close()


def check_service_reminders():
    db = SessionLocal()
    try:
        reminders = db.query(ServiceReminder).filter(ServiceReminder.is_active == True).all()
        today = date.today()
        for r in reminders:
            due = False
            if r.next_due_date and r.next_due_date <= today:
                due = True
            if r.next_due_miles and r.vehicle:
                last_wo = db.query(WorkOrder).filter(
                    WorkOrder.vehicle_id == r.vehicle_id, WorkOrder.status == "Completed"
                ).order_by(WorkOrder.completed_at.desc()).first()
                if last_wo and hasattr(last_wo, 'odometer') and last_wo.odometer:
                    if last_wo.odometer >= r.next_due_miles:
                        due = True
            if due:
                exists = db.query(Alert).filter(
                    Alert.alert_type == "service_due", Alert.is_read == False,
                    Alert.related_id == r.id, Alert.related_type == "service_reminder"
                ).first()
                if not exists:
                    vname = f"{r.vehicle.make} {r.vehicle.model}" if r.vehicle else "Vehicle"
                    _create_alert("service_due", f"Service Due: {r.service_type}",
                                  f"{vname} — {r.service_type} is due",
                                  "danger", r.id, "service_reminder")
    except Exception:
        logging.exception("Service reminder check failed")
    finally:
        db.close()


def check_overdue_invoices():
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        invoices = db.query(Invoice).filter(
            Invoice.status == "Unpaid", Invoice.created_at <= thirty_days_ago
        ).all()
        for inv in invoices:
            exists = db.query(Alert).filter(
                Alert.alert_type == "overdue_invoice", Alert.is_read == False,
                Alert.related_id == inv.id, Alert.related_type == "invoice"
            ).first()
            if not exists:
                _create_alert("overdue_invoice", f"Overdue Invoice {inv.invoice_number}",
                              f"${inv.total_amount:.2f} — {inv.created_at.strftime('%m/%d/%Y')}",
                              "danger", inv.id, "invoice")
    except Exception:
        logging.exception("Overdue invoice check failed")
    finally:
        db.close()


def check_inactive_customers():
    db = SessionLocal()
    try:
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        customers = db.query(Customer).filter(
            Customer.updated_at <= ninety_days_ago
        ).all()
        for c in customers:
            exists = db.query(Alert).filter(
                Alert.alert_type == "inactive_customer", Alert.is_read == False,
                Alert.related_id == c.id, Alert.related_type == "customer"
            ).first()
            if not exists:
                _create_alert("inactive_customer", f"Inactive Customer: {c.name}",
                              f"No activity since {c.updated_at.strftime('%m/%d/%Y')}",
                              "info", c.id, "customer")
    except Exception:
        logging.exception("Inactive customer check failed")
    finally:
        db.close()


def check_today_schedule():
    db = SessionLocal()
    try:
        today = date.today()
        scheds = db.query(Schedule).filter(Schedule.scheduled_date == today).all()
        for s in scheds:
            exists = db.query(Alert).filter(
                Alert.alert_type == "schedule_today", Alert.is_read == False,
                Alert.related_id == s.id, Alert.related_type == "schedule"
            ).first()
            if not exists:
                tech = s.technician.name if s.technician else "Unknown"
                wo = s.work_order.title if s.work_order else "N/A"
                _create_alert("schedule_today", f"Job Scheduled Today: {wo}",
                              f"Technician: {tech} — {s.start_time or '--'} to {s.end_time or '--'}",
                              "info", s.id, "schedule")
    except Exception:
        logging.exception("Schedule check failed")
    finally:
        db.close()


def reconcile_inventory():
    db = SessionLocal()
    try:
        parts = db.query(Part).all()
        for p in parts:
            txns = db.query(PartTransaction).filter(PartTransaction.part_id == p.id).all()
            calc_qty = sum(t.quantity_change for t in txns)
            if calc_qty != p.quantity_on_hand:
                logging.warning("Inventory mismatch: Part %s (id=%d): calculated=%d, actual=%d",
                                p.name, p.id, calc_qty, p.quantity_on_hand)
                _create_alert("inventory_mismatch", f"Inventory Mismatch: {p.name}",
                              f"Calculated: {calc_qty}, Recorded: {p.quantity_on_hand}",
                              "warning", p.id, "part")
    except Exception:
        logging.exception("Inventory reconciliation failed")
    finally:
        db.close()


def watch_scrap_prices():
    db = SessionLocal()
    try:
        from sqlalchemy import func
        mats = db.query(ScrapPickup.material_type).distinct().all()
        for (mat,) in mats:
            recent = db.query(ScrapPickup).filter(
                ScrapPickup.material_type == mat
            ).order_by(ScrapPickup.pickup_date.desc()).limit(2).all()
            if len(recent) == 2:
                old_price = recent[1].price_per_kg
                new_price = recent[0].price_per_kg
                if old_price > 0:
                    pct = ((new_price - old_price) / old_price) * 100
                    if abs(pct) > 10:
                        direction = "up" if pct > 0 else "down"
                        _create_alert("price_change", f"Scrap Price Alert: {mat}",
                                      f"Price moved {direction} {abs(pct):.0f}% (${old_price:.2f} → ${new_price:.2f})",
                                      "info" if pct > 0 else "warning")
    except Exception:
        logging.exception("Price watcher failed")
    finally:
        db.close()


def cleanup_data():
    db = SessionLocal()
    try:
        old = datetime.utcnow() - timedelta(days=90)
        db.query(Alert).filter(Alert.is_read == True, Alert.created_at <= old).delete()
        db.commit()
        db.execute("VACUUM")
        logging.info("Data cleanup complete")
    except Exception:
        logging.exception("Data cleanup failed")
    finally:
        db.close()


def generate_recurring_work_orders():
    from app.models import RecurringWorkOrder, WorkOrder
    from datetime import date as dt_date, timedelta
    db = SessionLocal()
    try:
        today = dt_date.today()
        items = db.query(RecurringWorkOrder).filter(
            RecurringWorkOrder.is_active == True,
            RecurringWorkOrder.next_due_date <= today
        ).all()
        for r in items:
            wo = WorkOrder(
                customer_id=r.customer_id, vehicle_id=r.vehicle_id,
                title=r.title, description=r.description,
                labor_hours=r.labor_hours, labor_rate=r.labor_rate,
                status="New",
            )
            db.add(wo)
            db.flush()
            r.last_generated = datetime.utcnow()
            if r.interval_days:
                r.next_due_date = today + timedelta(days=r.interval_days)
        if items:
            db.commit()
            logging.info("Generated %d recurring work orders", len(items))
    except Exception:
        logging.exception("Recurring WO generation failed")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(auto_invoice_completed, "interval", hours=1, id="auto_invoice")
    scheduler.add_job(check_low_stock, "interval", hours=6, id="check_low_stock")
    scheduler.add_job(check_service_reminders, "interval", hours=12, id="check_service")
    scheduler.add_job(check_overdue_invoices, "interval", hours=24, id="check_overdue")
    scheduler.add_job(check_inactive_customers, "interval", hours=24, id="check_inactive")
    scheduler.add_job(check_today_schedule, "interval", hours=6, id="check_schedule")
    scheduler.add_job(reconcile_inventory, "interval", hours=24, id="reconcile_inv")
    scheduler.add_job(watch_scrap_prices, "interval", hours=24, id="watch_prices")
    scheduler.add_job(cleanup_data, "interval", days=7, id="cleanup")
    scheduler.add_job(generate_recurring_work_orders, "interval", hours=24, id="recurring_wo")
    scheduler.start()
    logging.info("Background scheduler started with 10 agents")
