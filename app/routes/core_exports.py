"""CSV/QuickBooks/PDF exports and CSV imports (same `core` blueprint)."""
import csv
import io
import logging
from datetime import datetime
from flask import redirect, render_template, request, flash, g
from app.auth import login_required
from app.export import export_csv
from app.timeutils import utcnow
from app.routes.core import bp


# ---- CSV Export ----
@bp.route("/export/customers")
@login_required
def export_customers():
    from app.models import Customer
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    return export_csv(
        ["Name", "Company", "Phone", "Email", "Address", "Vehicles", "Notes"],
        [[c.name, c.company or "", c.phone or "", c.email or "", c.address or "", len(c.vehicles), c.notes or ""] for c in customers],
        "customers.csv"
    )


@bp.route("/export/parts")
@login_required
def export_parts():
    from app.models import Part
    db = g.db
    parts = db.query(Part).order_by(Part.name).all()
    return export_csv(
        ["Name", "Part #", "Category", "Supplier", "Qty", "Min", "Cost", "Sell", "Location"],
        [[p.name, p.part_number or "", p.category or "", p.supplier or "", p.quantity_on_hand, p.min_quantity, p.cost_price, p.selling_price, p.location or ""] for p in parts],
        "parts.csv"
    )


@bp.route("/export/work-orders")
@login_required
def export_work_orders():
    from app.models import WorkOrder
    db = g.db
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    return export_csv(
        ["ID", "Title", "Customer", "Vehicle", "Status", "Labor Hrs", "Parts", "Total", "Created"],
        [[wo.id, wo.title, wo.customer.name if wo.customer else "", f"{wo.vehicle.make} {wo.vehicle.model}" if wo.vehicle else "", wo.status, wo.labor_hours, wo.parts_total, wo.total_amount, wo.created_at.strftime("%Y-%m-%d")] for wo in wos],
        "work_orders.csv"
    )


@bp.route("/export/scrap-pickups")
@login_required
def export_scrap_pickups():
    from app.models import ScrapPickup
    db = g.db
    pickups = db.query(ScrapPickup).order_by(ScrapPickup.pickup_date.desc()).all()
    return export_csv(
        ["Date", "Vendor", "Material", "Weight (kg)", "Price/kg", "Total Payout"],
        [[p.pickup_date, p.vendor.name if p.vendor else "", p.material_type, p.weight_kg, p.price_per_kg, p.total_payout] for p in pickups],
        "scrap_pickups.csv"
    )


@bp.route("/export/invoices")
@login_required
def export_invoices():
    from app.models import Invoice
    db = g.db
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return export_csv(
        ["Invoice #", "Work Order", "Customer", "Subtotal", "Tax", "Total", "Status", "Paid Date"],
        [[inv.invoice_number or "", inv.work_order.title if inv.work_order else "", inv.work_order.customer.name if inv.work_order and inv.work_order.customer else "", inv.subtotal, inv.tax_amount, inv.total_amount, inv.status, inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else ""] for inv in invoices],
        "invoices.csv"
    )
# ---- QuickBooks Export ----
@bp.route("/export/quickbooks")
@login_required
def export_quickbooks():
    from app.models import Invoice, WorkOrder
    db = g.db
    invoices = db.query(Invoice).filter(Invoice.status == "Paid").order_by(Invoice.paid_at.desc()).all()
    rows = []
    for inv in invoices:
        cust = inv.work_order.customer if inv.work_order and inv.work_order.customer else None
        rows.append([
            inv.invoice_number or "", inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else "",
            cust.name if cust else "", cust.company or "", cust.address or "",
            cust.email or "", inv.total_amount, inv.subtotal, inv.tax_amount
        ])
    return export_csv(
        ["Invoice #", "Date Paid", "Customer Name", "Company", "Address", "Email",
         "Total Amount", "Subtotal", "Tax"],
        rows, "quickbooks_export.csv"
    )
# ---- QuickBooks Sync (enhanced) ----
@bp.route("/export/quickbooks-import", methods=["POST"])
@login_required
def quickbooks_import():
    from app.models import Invoice, WorkOrder, Customer
    db = g.db
    try:
        f = request.files.get("file")
        if not f:
            flash("No file selected", "warning")
            return redirect(request.referrer or "/")
        reader = csv.DictReader(io.StringIO(f.read().decode("utf-8")))
        count = 0
        for row in reader:
            if row.get("Invoice #") and row.get("Date Paid"):
                inv = db.query(Invoice).filter(Invoice.invoice_number == row["Invoice #"]).first()
                if inv:
                    from datetime import date as dt_date
                    try:
                        paid = dt_date.fromisoformat(row["Date Paid"])
                    except ValueError:
                        paid = None
                    inv.status = "Paid"
                    inv.paid_at = datetime.combine(paid, datetime.min.time()) if paid else utcnow()
                    count += 1
        db.commit()
        flash(f"Synced {count} invoices from QuickBooks", "success")
    except Exception:
        db.rollback()
        logging.exception("QB import failed")
        flash("QuickBooks import failed", "danger")
    return redirect(request.referrer or "/")
# ---- CSV Import ----
@bp.route("/import/<entity>", methods=["POST"])
@login_required
def csv_import(entity):
    from app.models import Customer, Vehicle, Part, Lead, Technician, ScrapVendor
    db = g.db
    try:
        f = request.files.get("file")
        if not f:
            flash("No file selected", "warning")
            return redirect(request.referrer or "/")
        reader = csv.DictReader(io.StringIO(f.read().decode("utf-8")))
        count = 0
        if entity == "customers":
            for row in reader:
                if row.get("name"):
                    db.add(Customer(name=row["name"], company=row.get("company", ""),
                                    phone=row.get("phone", ""), email=row.get("email", ""),
                                    address=row.get("address", ""), notes=row.get("notes", "")))
                    count += 1
        elif entity == "parts":
            for row in reader:
                if row.get("name"):
                    db.add(Part(name=row["name"], part_number=row.get("part_number", ""),
                                category=row.get("category", ""), supplier=row.get("supplier", ""),
                                cost_price=float(row.get("cost_price", 0)),
                                selling_price=float(row.get("selling_price", 0)),
                                quantity_on_hand=int(row.get("quantity_on_hand", 0)),
                                min_quantity=int(row.get("min_quantity", 5)),
                                location=row.get("location", "")))
                    count += 1
        elif entity == "leads":
            for row in reader:
                if row.get("name"):
                    db.add(Lead(name=row["name"], company=row.get("company", ""),
                                phone=row.get("phone", ""), email=row.get("email", ""),
                                source=row.get("source", ""), status=row.get("status", "New"),
                                notes=row.get("notes", "")))
                    count += 1
        elif entity == "technicians":
            for row in reader:
                if row.get("name"):
                    db.add(Technician(name=row["name"], phone=row.get("phone", ""),
                                      email=row.get("email", ""),
                                      specialization=row.get("specialization", ""),
                                      hourly_rate=float(row.get("hourly_rate", 0))))
                    count += 1
        db.commit()
        from app.audit import log_audit
        log_audit("import", entity, None, f"Imported {count} records")
        flash(f"Imported {count} {entity}", "success")
    except Exception:
        db.rollback()
        logging.exception("Import failed")
        flash("Import failed. Check file format.", "danger")
    return redirect(request.referrer or "/")
# ---- PDF Export (simple HTML-to-PDF print) ----
@bp.route("/export/pdf/<entity>/<int:eid>")
@login_required
def export_pdf(entity, eid):
    from app.models import WorkOrder, Invoice, Customer, Vehicle, Estimate
    db = g.db
    template = None
    ctx = {}
    if entity == "work_order":
        obj = db.query(WorkOrder).filter(WorkOrder.id == eid).first()
        if obj: template, ctx = "pdf/work_order.html", {"wo": obj}
    elif entity == "invoice":
        obj = db.query(Invoice).filter(Invoice.id == eid).first()
        if obj: template, ctx = "pdf/invoice.html", {"inv": obj}
    elif entity == "estimate":
        obj = db.query(Estimate).filter(Estimate.id == eid).first()
        if obj: template, ctx = "pdf/estimate.html", {"est": obj}
    elif entity == "vehicle":
        obj = db.query(Vehicle).filter(Vehicle.id == eid).first()
        if obj: template, ctx = "pdf/vehicle_history.html", {"vehicle": obj}
    if template:
        return render_template(template, **ctx)
    return "Not found", 404
