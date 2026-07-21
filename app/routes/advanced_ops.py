from flask import Blueprint, render_template, request, redirect, flash, jsonify, g
import logging
from datetime import datetime, date, timedelta
from app.models import Company, Estimate, EstimateItem, CoreCharge, CoreReturn, Warranty, WarrantyClaim, Vendor, VendorQuote, DieselEmissionRecord, TPMContract, FleetGroup, FleetVehicle, FuelRecord, EquipmentHourMeter, DOTInspection, ELDLog, TireRecord, PartCrossReference, Customer, Vehicle, WorkOrder, WorkOrderItem
from app.auth import login_required, role_required
from app.audit import log_audit
from app.helpers import paginate
import urllib.parse

bp = Blueprint("advanced_ops", __name__, url_prefix="/ops")


# ---- Multi-Company ----
@bp.route("/companies")
@login_required
def list_companies():
    db = g.db
    companies = db.query(Company).order_by(Company.name).all()
    return render_template("advanced_ops/companies.html", companies=companies, active_page="companies")


@bp.route("/companies/new", methods=["POST"])
@login_required
def create_company():
    db = g.db
    try:
        c = Company(name=request.form["name"], legal_name=request.form.get("legal_name", ""),
                    tax_id=request.form.get("tax_id", ""), address=request.form.get("address", ""),
                    phone=request.form.get("phone", ""), email=request.form.get("email", ""))
        db.add(c); db.commit()
        log_audit("create", "company", c.id, f"Created company {c.name}")
        flash("Company created", "success")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Error creating company", "danger")
    return redirect("/ops/companies")


@bp.route("/companies/<int:cid>/toggle", methods=["POST"])
@login_required
def toggle_company(cid):
    db = g.db
    c = db.query(Company).filter(Company.id == cid).first()
    if c: c.is_active = not c.is_active; db.commit()
    return redirect("/ops/companies")


# ---- Estimates (Estimate → Approve → WO) ----
@bp.route("/estimates")
@login_required
def list_estimates():
    db = g.db
    status = request.args.get("status", "")
    q = db.query(Estimate)
    if status: q = q.filter(Estimate.status == status)
    page = int(request.args.get("page", 1))
    p = paginate(q.order_by(Estimate.created_at.desc()), page, 50)
    return render_template("advanced_ops/estimates.html", p=p, status=status, active_page="estimates")


@bp.route("/estimates/new", methods=["GET"])
@login_required
def new_estimate_form():
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    return render_template("advanced_ops/estimate_form.html", estimate=None, customers=customers, vehicles=vehicles, active_page="estimates")


@bp.route("/estimates/new", methods=["POST"])
@login_required
def create_estimate():
    db = g.db
    try:
        count = db.query(Estimate).count() + 1
        est = Estimate(estimate_number=f"EST-{datetime.utcnow().strftime('%Y%m')}-{count:04d}",
                       customer_id=int(request.form["customer_id"]), vehicle_id=int(request.form["vehicle_id"]),
                       title=request.form["title"], description=request.form.get("description", ""),
                       labor_hours=float(request.form.get("labor_hours", 0)),
                       labor_rate=float(request.form.get("labor_rate", 150)),
                       status="Draft", expires_at=date.today() + timedelta(days=30))
        db.add(est); db.flush()
        descs = request.form.getlist("item_desc[]"); qtys = request.form.getlist("item_qty[]")
        prices = request.form.getlist("item_price[]"); labors = request.form.getlist("item_labor[]")
        for d, q, p, l in zip(descs, qtys, prices, labors):
            if d.strip():
                qty = int(q or 1); price = float(p or 0)
                db.add(EstimateItem(estimate_id=est.id, description=d, quantity=qty, unit_price=price,
                                    total_price=qty * price, is_labor=(l == "on")))
        est.parts_total = sum(i.total_price for i in est.items if not i.is_labor) if est.items else 0
        labor_total = sum(i.total_price for i in est.items if i.is_labor) if est.items else est.labor_hours * est.labor_rate
        est.total_amount = est.parts_total + labor_total
        db.commit()
        log_audit("create", "estimate", est.id, f"Created estimate {est.estimate_number}")
        flash("Estimate created", "success")
        return redirect(f"/ops/estimates/{est.id}")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Error creating estimate", "danger")
        return redirect("/ops/estimates/new")


@bp.route("/estimates/<int:eid>")
@login_required
def view_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if not est: return redirect("/ops/estimates")
    return render_template("advanced_ops/estimate_detail.html", est=est, active_page="estimates")


@bp.route("/estimates/<int:eid>/approve", methods=["POST"])
@login_required
def approve_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if est:
        est.status = "Approved"; est.approved_at = datetime.utcnow()
        db.commit()
        log_audit("approve", "estimate", eid, f"Approved estimate {est.estimate_number}")
        flash("Estimate approved", "success")
    return redirect(f"/ops/estimates/{eid}")


@bp.route("/estimates/<int:eid>/convert", methods=["POST"])
@login_required
def convert_estimate_to_wo(eid):
    db = g.db
    try:
        est = db.query(Estimate).filter(Estimate.id == eid).first()
        if est and est.status == "Approved":
            wo = WorkOrder(customer_id=est.customer_id, vehicle_id=est.vehicle_id,
                           title=est.title, description=est.description,
                           labor_hours=est.labor_hours, labor_rate=est.labor_rate,
                           status="New")
            db.add(wo); db.flush()
            for item in est.items:
                db.add(WorkOrderItem(work_order_id=wo.id, description=item.description,
                                     part_used=item.part_used, quantity=item.quantity,
                                     unit_price=item.unit_price, total_price=item.total_price,
                                     is_labor=item.is_labor))
            est.converted_wo_id = wo.id; est.status = "Converted"
            db.commit()
            log_audit("convert", "estimate", eid, f"Converted to WO #{wo.id}")
            flash(f"Work order #{wo.id} created from estimate", "success")
            return redirect(f"/work-orders/{wo.id}")
        flash("Estimate must be approved first", "warning")
        return redirect(f"/ops/estimates/{eid}")
    except Exception:
        db.rollback(); logging.exception("Error"); flash("Conversion failed", "danger")
        return redirect(f"/ops/estimates/{eid}")


@bp.route("/estimates/<int:eid>/send", methods=["POST"])
@login_required
def send_estimate(eid):
    db = g.db
    est = db.query(Estimate).filter(Estimate.id == eid).first()
    if est:
        est.status = "Sent"; db.commit()
        if est.customer and est.customer.email:
            from app.notifications import send_email
            send_email(est.customer.email, f"Estimate {est.estimate_number} from HD Mechanic CRM",
                       f"Your estimate #{est.estimate_number} for ${est.total_amount:.2f} is ready for review.")
        flash("Estimate sent to customer", "success")
    return redirect(f"/ops/estimates/{eid}")


# ---- Core Charges & Returns ----
@bp.route("/core-charges")
@login_required
def list_core_charges():
    db = g.db
    charges = db.query(CoreCharge).order_by(CoreCharge.created_at.desc()).all()
    return render_template("advanced_ops/core_charges.html", charges=charges, active_page="core_charges")


@bp.route("/core-charges/new", methods=["POST"])
@login_required
def create_core_charge():
    db = g.db
    try:
        cc = CoreCharge(part_id=int(request.form["part_id"]),
                        charge_amount=float(request.form.get("charge_amount", 0)),
                        is_refundable=request.form.get("is_refundable") == "on")
        db.add(cc); db.commit()
        log_audit("create", "core_charge", cc.id, f"Core charge for part #{cc.part_id}")
        flash("Core charge created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/core-charges")


@bp.route("/core-charges/<int:ccid>/return", methods=["POST"])
@login_required
def return_core(ccid):
    db = g.db
    cc = db.query(CoreCharge).filter(CoreCharge.id == ccid).first()
    if cc:
        cr = CoreReturn(core_charge_id=ccid, work_order_id=int(request.form.get("work_order_id", 0)) or None,
                        refund_amount=float(request.form.get("refund_amount", cc.charge_amount)),
                        notes=request.form.get("notes", ""))
        db.add(cr); db.commit()
        log_audit("return", "core", ccid, f"Core returned ${cr.refund_amount:.2f}")
        flash("Core return recorded", "success")
    return redirect("/ops/core-charges")


# ---- Warranties ----
@bp.route("/warranties")
@login_required
def list_warranties():
    db = g.db
    warranties = db.query(Warranty).order_by(Warranty.created_at.desc()).all()
    return render_template("advanced_ops/warranties.html", warranties=warranties, active_page="warranties")


@bp.route("/warranties/new", methods=["POST"])
@login_required
def create_warranty():
    db = g.db
    try:
        w = Warranty(entity_type=request.form["entity_type"], entity_id=int(request.form["entity_id"]),
                     warranty_type=request.form.get("warranty_type", "Parts"),
                     duration_days=int(request.form.get("duration_days", 365)),
                     duration_miles=int(request.form.get("duration_miles", 0)) or None,
                     start_date=date.fromisoformat(request.form["start_date"]),
                     notes=request.form.get("notes", ""))
        if w.duration_days: w.end_date = w.start_date + timedelta(days=w.duration_days)
        db.add(w); db.commit()
        log_audit("create", "warranty", w.id, f"Warranty created")
        flash("Warranty created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/warranties")


@bp.route("/warranty-claims")
@login_required
def list_warranty_claims():
    db = g.db
    claims = db.query(WarrantyClaim).order_by(WarrantyClaim.created_at.desc()).all()
    return render_template("advanced_ops/warranty_claims.html", claims=claims, active_page="warranty_claims")


@bp.route("/warranty-claims/new", methods=["POST"])
@login_required
def create_warranty_claim():
    db = g.db
    try:
        c = WarrantyClaim(warranty_id=int(request.form["warranty_id"]),
                          work_order_id=int(request.form.get("work_order_id", 0)) or None,
                          description=request.form.get("description", ""),
                          labor_cost=float(request.form.get("labor_cost", 0)),
                          parts_cost=float(request.form.get("parts_cost", 0)),
                          total_claim=float(request.form.get("total_claim", 0)),
                          notes=request.form.get("notes", ""))
        db.add(c); db.commit()
        log_audit("create", "warranty_claim", c.id, f"Warranty claim filed")
        flash("Warranty claim created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/warranty-claims")


# ---- Vendor Portal (Quotes) ----
@bp.route("/vendors")
@login_required
def list_vendors():
    db = g.db
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    return render_template("advanced_ops/vendors.html", vendors=vendors, active_page="vendors")


@bp.route("/vendors/new", methods=["POST"])
@login_required
def create_vendor():
    db = g.db
    try:
        v = Vendor(name=request.form["name"], contact_person=request.form.get("contact_person", ""),
                   phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                   address=request.form.get("address", ""), vendor_type=request.form.get("vendor_type", ""),
                   payment_terms=request.form.get("payment_terms", ""), tax_id=request.form.get("tax_id", ""))
        db.add(v); db.commit()
        flash("Vendor created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/vendors")


@bp.route("/vendor-quotes")
@login_required
def list_vendor_quotes():
    db = g.db
    quotes = db.query(VendorQuote).order_by(VendorQuote.created_at.desc()).all()
    return render_template("advanced_ops/vendor_quotes.html", quotes=quotes, active_page="vendor_quotes")


@bp.route("/vendor-quotes/new", methods=["POST"])
@login_required
def create_vendor_quote():
    db = g.db
    try:
        q = VendorQuote(vendor_id=int(request.form["vendor_id"]),
                        part_id=int(request.form.get("part_id", 0)) or None,
                        part_name=request.form.get("part_name", ""),
                        part_number=request.form.get("part_number", ""),
                        quantity=int(request.form.get("quantity", 1)),
                        unit_price=float(request.form.get("unit_price", 0)),
                        total_price=float(request.form.get("total_price", 0)),
                        lead_days=int(request.form.get("lead_days", 0)) or None,
                        valid_until=date.fromisoformat(request.form["valid_until"]) if request.form.get("valid_until") else None)
        db.add(q); db.commit()
        flash("Vendor quote added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/vendor-quotes")


# ---- Diesel Emissions ----
@bp.route("/emissions")
@login_required
def list_emissions():
    db = g.db
    records = db.query(DieselEmissionRecord).order_by(DieselEmissionRecord.service_date.desc()).all()
    return render_template("advanced_ops/emissions.html", records=records, active_page="emissions")


@bp.route("/emissions/new", methods=["POST"])
@login_required
def create_emission_record():
    db = g.db
    try:
        r = DieselEmissionRecord(vehicle_id=int(request.form["vehicle_id"]),
                                 record_type=request.form["record_type"],
                                 service_date=date.fromisoformat(request.form["service_date"]),
                                 odometer=int(request.form.get("odometer", 0)) or None,
                                 description=request.form.get("description", ""),
                                 part_number=request.form.get("part_number", ""),
                                 cost=float(request.form.get("cost", 0)),
                                 next_due_odometer=int(request.form.get("next_due_odometer", 0)) or None,
                                 next_due_date=date.fromisoformat(request.form["next_due_date"]) if request.form.get("next_due_date") else None,
                                 notes=request.form.get("notes", ""))
        db.add(r); db.commit()
        log_audit("create", "emission_record", r.id, f"{r.record_type} recorded")
        flash("Emission record added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/emissions")


# ---- TPM Contracts ----
@bp.route("/tpm-contracts")
@login_required
def list_tpm():
    db = g.db
    contracts = db.query(TPMContract).order_by(TPMContract.start_date.desc()).all()
    return render_template("advanced_ops/tpm_contracts.html", contracts=contracts, active_page="tpm_contracts")

@bp.route("/tpm-contracts/new", methods=["POST"])
@login_required
def create_tpm():
    db = g.db
    try:
        c = TPMContract(customer_id=int(request.form["customer_id"]),
                        contract_number=request.form.get("contract_number", f"TPM-{datetime.utcnow().strftime('%Y%m')}-{datetime.utcnow().microsecond}"),
                        title=request.form["title"],
                        start_date=date.fromisoformat(request.form["start_date"]),
                        end_date=date.fromisoformat(request.form["end_date"]) if request.form.get("end_date") else None,
                        monthly_fee=float(request.form.get("monthly_fee", 0)),
                        included_services=request.form.get("included_services", ""),
                        excluded_services=request.form.get("excluded_services", ""),
                        max_hours_per_month=float(request.form.get("max_hours_per_month", 0)),
                        notes=request.form.get("notes", ""))
        db.add(c); db.commit()
        flash("TPM contract created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/tpm-contracts")


# ---- Fleet Management ----
@bp.route("/fleet")
@login_required
def list_fleet():
    db = g.db
    groups = db.query(FleetGroup).order_by(FleetGroup.name).all()
    return render_template("advanced_ops/fleet.html", groups=groups, active_page="fleet")


@bp.route("/fleet/new", methods=["POST"])
@login_required
def create_fleet_group():
    db = g.db
    try:
        fleet_group = FleetGroup(customer_id=int(request.form["customer_id"]), name=request.form["name"],
                       billing_cycle=request.form.get("billing_cycle", "Monthly"),
                       consolidated_billing=request.form.get("consolidated_billing") == "on",
                       notes=request.form.get("notes", ""))
        db.add(fleet_group); db.commit()
        flash("Fleet group created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/fleet")


@bp.route("/fleet/<int:gid>/add-vehicle", methods=["POST"])
@login_required
def add_fleet_vehicle(gid):
    db = g.db
    try:
        fv = FleetVehicle(fleet_group_id=gid, vehicle_id=int(request.form["vehicle_id"]),
                          unit_number=request.form.get("unit_number", ""),
                          assigned_driver=request.form.get("assigned_driver", ""))
        db.add(fv); db.commit()
        flash("Vehicle added to fleet", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/fleet")


# ---- Fuel Tracking ----
@bp.route("/fuel")
@login_required
def list_fuel():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(FuelRecord).order_by(FuelRecord.fuel_date.desc()), page, 50)
    return render_template("advanced_ops/fuel.html", p=p, active_page="fuel")


@bp.route("/fuel/new", methods=["POST"])
@login_required
def create_fuel_record():
    db = g.db
    try:
        r = FuelRecord(vehicle_id=int(request.form["vehicle_id"]),
                       fuel_date=date.fromisoformat(request.form["fuel_date"]),
                       gallons=float(request.form["gallons"]),
                       price_per_gallon=float(request.form.get("price_per_gallon", 0)),
                       total_cost=float(request.form.get("total_cost", 0)),
                       odometer=int(request.form.get("odometer", 0)) or None,
                       fuel_type=request.form.get("fuel_type", "Diesel"),
                       vendor=request.form.get("vendor", ""), notes=request.form.get("notes", ""))
        db.add(r); db.commit()
        flash("Fuel record added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/fuel")


# ---- Equipment Hour Meters ----
@bp.route("/hour-meters")
@login_required
def list_hour_meters():
    db = g.db
    records = db.query(EquipmentHourMeter).order_by(EquipmentHourMeter.reading_date.desc()).all()
    return render_template("advanced_ops/hour_meters.html", records=records, active_page="hour_meters")


@bp.route("/hour-meters/new", methods=["POST"])
@login_required
def create_hour_meter():
    db = g.db
    try:
        r = EquipmentHourMeter(vehicle_id=int(request.form["vehicle_id"]),
                               hours=float(request.form["hours"]),
                               reading_date=date.fromisoformat(request.form["reading_date"]) if request.form.get("reading_date") else date.today(),
                               notes=request.form.get("notes", ""))
        db.add(r); db.commit()
        flash("Hour meter reading recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/hour-meters")


# ---- DOT Inspections ----
@bp.route("/dot-inspections")
@login_required
def list_dot():
    db = g.db
    inspections = db.query(DOTInspection).order_by(DOTInspection.inspection_date.desc()).all()
    return render_template("advanced_ops/dot_inspections.html", inspections=inspections, active_page="dot_inspections")


@bp.route("/dot-inspections/new", methods=["POST"])
@login_required
def create_dot():
    db = g.db
    try:
        i = DOTInspection(vehicle_id=int(request.form["vehicle_id"]),
                          inspection_date=date.fromisoformat(request.form["inspection_date"]),
                          inspector=request.form.get("inspector", ""),
                          inspection_type=request.form.get("inspection_type", ""),
                          result=request.form.get("result", "Pass"),
                          odometer=int(request.form.get("odometer", 0)) or None,
                          defects=request.form.get("defects", ""),
                          certificate_number=request.form.get("certificate_number", ""),
                          notes=request.form.get("notes", ""))
        db.add(i); db.commit()
        log_audit("create", "dot_inspection", i.id, f"DOT inspection result: {i.result}")
        flash("DOT inspection recorded", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/dot-inspections")


# ---- ELD Logs ----
@bp.route("/eld-logs")
@login_required
def list_eld():
    db = g.db
    logs = db.query(ELDLog).order_by(ELDLog.log_date.desc()).all()
    return render_template("advanced_ops/eld_logs.html", logs=logs, active_page="eld_logs")


@bp.route("/eld-logs/new", methods=["POST"])
@login_required
def create_eld():
    db = g.db
    try:
        l = ELDLog(vehicle_id=int(request.form["vehicle_id"]),
                   driver_name=request.form.get("driver_name", ""),
                   log_date=date.fromisoformat(request.form["log_date"]),
                   duty_status=request.form.get("duty_status", ""),
                   hours_driven=float(request.form.get("hours_driven", 0)),
                   hours_on_duty=float(request.form.get("hours_on_duty", 0)),
                   hours_off_duty=float(request.form.get("hours_off_duty", 0)),
                   odometer_start=int(request.form.get("odometer_start", 0)) or None,
                   odometer_end=int(request.form.get("odometer_end", 0)) or None,
                   notes=request.form.get("notes", ""))
        db.add(l); db.commit()
        flash("ELD log entry created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/eld-logs")


# ---- Tire Records ----
@bp.route("/tires")
@login_required
def list_tires():
    db = g.db
    tires = db.query(TireRecord).order_by(TireRecord.install_date.desc().nullslast()).all()
    return render_template("advanced_ops/tires.html", tires=tires, active_page="tires")


@bp.route("/tires/new", methods=["POST"])
@login_required
def create_tire():
    db = g.db
    try:
        t = TireRecord(vehicle_id=int(request.form["vehicle_id"]), position=request.form.get("position", ""),
                       brand=request.form.get("brand", ""), model=request.form.get("model", ""),
                       size=request.form.get("size", ""), serial_number=request.form.get("serial_number", ""),
                       install_date=date.fromisoformat(request.form["install_date"]) if request.form.get("install_date") else None,
                       install_odometer=int(request.form.get("install_odometer", 0)) or None,
                       notes=request.form.get("notes", ""))
        db.add(t); db.commit()
        flash("Tire record created", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/tires")


# ---- Part Cross References ----
@bp.route("/cross-references")
@login_required
def list_cross_refs():
    db = g.db
    refs = db.query(PartCrossReference).order_by(PartCrossReference.cross_brand).all()
    return render_template("advanced_ops/cross_refs.html", refs=refs, active_page="cross_refs")


@bp.route("/cross-references/new", methods=["POST"])
@login_required
def create_cross_ref():
    db = g.db
    try:
        cr = PartCrossReference(part_id=int(request.form["part_id"]),
                                cross_type=request.form.get("cross_type", "OEM"),
                                cross_part_number=request.form["cross_part_number"],
                                cross_brand=request.form.get("cross_brand", ""),
                                cross_description=request.form.get("cross_description", ""),
                                notes=request.form.get("notes", ""))
        db.add(cr); db.commit()
        flash("Cross reference added", "success")
    except Exception:
        db.rollback(); flash("Error", "danger")
    return redirect("/ops/cross-references")
