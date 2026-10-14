"""Fleet, fuel, tires, meters, DOT, ELD, emissions, TPM (same `advanced_ops` blueprint)."""
from flask import render_template, request, redirect, flash, g
from datetime import date
from app.timeutils import utcnow
from app.models import DieselEmissionRecord, TPMContract, FleetGroup, FleetVehicle, FuelRecord, EquipmentHourMeter, DOTInspection, ELDLog, TireRecord
from app.auth import login_required
from app.audit import log_audit
from app.helpers import paginate
from app.routes.advanced_ops import bp


# ---- Diesel Emissions ----
@bp.route("/emissions")
@login_required
def list_emissions():
    db = g.db
    page = int(request.args.get("page", 1))
    p = paginate(db.query(DieselEmissionRecord).order_by(DieselEmissionRecord.service_date.desc()), page)
    return render_template("advanced_ops/emissions.html", records=p["rows"], p=p, active_page="emissions")


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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(TPMContract).order_by(TPMContract.start_date.desc()), page)
    return render_template("advanced_ops/tpm_contracts.html", contracts=p["rows"], p=p, active_page="tpm_contracts")

@bp.route("/tpm-contracts/new", methods=["POST"])
@login_required
def create_tpm():
    db = g.db
    try:
        c = TPMContract(customer_id=int(request.form["customer_id"]),
                        contract_number=request.form.get("contract_number", f"TPM-{utcnow().strftime('%Y%m')}-{utcnow().microsecond}"),
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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(FleetGroup).order_by(FleetGroup.name), page)
    return render_template("advanced_ops/fleet.html", groups=p["rows"], p=p, active_page="fleet")


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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(EquipmentHourMeter).order_by(EquipmentHourMeter.reading_date.desc()), page)
    return render_template("advanced_ops/hour_meters.html", records=p["rows"], p=p, active_page="hour_meters")


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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(DOTInspection).order_by(DOTInspection.inspection_date.desc()), page)
    return render_template("advanced_ops/dot_inspections.html", inspections=p["rows"], p=p, active_page="dot_inspections")


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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(ELDLog).order_by(ELDLog.log_date.desc()), page)
    return render_template("advanced_ops/eld_logs.html", logs=p["rows"], p=p, active_page="eld_logs")


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
    page = int(request.args.get("page", 1))
    p = paginate(db.query(TireRecord).order_by(TireRecord.install_date.desc().nullslast()), page)
    return render_template("advanced_ops/tires.html", tires=p["rows"], p=p, active_page="tires")


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
