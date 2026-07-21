from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from datetime import date
from app.models import DVIInspection, DVIChecklistItem, Vehicle, WorkOrder, Technician
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("dvi", __name__, url_prefix="/dvi")

DEFAULT_ITEMS = [
    ("Brakes", "Brake Pads / Shoes"), ("Brakes", "Brake Drums / Rotors"),
    ("Brakes", "Air Brake System"), ("Brakes", "Brake Lines / Hoses"),
    ("Tires", "Tread Depth"), ("Tires", "Tire Pressure"),
    ("Tires", "Sidewall Condition"), ("Tires", "Spare Tire"),
    ("Engine", "Oil Level / Condition"), ("Engine", "Coolant Level / Condition"),
    ("Engine", "Belts & Hoses"), ("Engine", "Air Filter"),
    ("Engine", "Fuel System / Filters"), ("Electrical", "Battery / Cables"),
    ("Electrical", "Alternator / Charging"), ("Electrical", "Lights / Signals"),
    ("Electrical", "Wiring / Connections"), ("Suspension", "Shocks / Struts"),
    ("Suspension", "Leaf Springs / U-Bolts"), ("Suspension", "Steering Linkage"),
    ("Suspension", "Ball Joints / Bushings"), ("Exhaust", "Exhaust Manifold"),
    ("Exhaust", "DPF / Regeneration System"), ("Exhaust", "Muffler / Pipes"),
    ("HVAC", "A/C System"), ("HVAC", "Heater / Defroster"),
    ("Safety", "Seat Belts"), ("Safety", "Horn"),
    ("Safety", "Mirrors"), ("Safety", "Fire Extinguisher"),
    ("Frame", "Frame Condition"), ("Frame", "Body / Mounts"),
]


@bp.route("", methods=["GET"])
@login_required
def list_inspections():
    db = g.db
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(db.query(DVIInspection).order_by(DVIInspection.inspection_date.desc()), page, per_page)
    return render_template("dvi/list.html", p=p, active_page="dvi", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_inspection_form():
    db = g.db
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    techs = db.query(Technician).filter(Technician.is_active == True).order_by(Technician.name).all()
    wos = db.query(WorkOrder).filter(WorkOrder.status.not_in(["Completed", "Invoiced", "Cancelled"])).all()
    return render_template("dvi/form.html", inspection=None, vehicles=vehicles,
                           technicians=techs, work_orders=wos, items=DEFAULT_ITEMS,
                           active_page="dvi")


@bp.route("/new", methods=["POST"])
@login_required
def create_inspection():
    db = g.db
    try:
        inv = DVIInspection(
            work_order_id=int(request.form["work_order_id"]) if request.form.get("work_order_id") else None,
            vehicle_id=int(request.form["vehicle_id"]),
            technician_id=int(request.form["technician_id"]) if request.form.get("technician_id") else None,
            odometer=int(request.form.get("odometer", 0)) or None,
            inspection_date=date.fromisoformat(request.form["inspection_date"]),
            summary=request.form.get("summary", ""),
            status="Completed",
        )
        db.add(inv)
        db.flush()
        categories = request.form.getlist("category[]")
        items = request.form.getlist("item[]")
        results = request.form.getlist("result[]")
        notes_list = request.form.getlist("notes[]")
        for cat, item, result, note in zip(categories, items, results, notes_list):
            db.add(DVIChecklistItem(
                inspection_id=inv.id, category=cat, check_item=item,
                result=result or "Not Checked", notes=note
            ))
        db.commit()
        flash("DVI inspection recorded", "success")
        return redirect(f"/dvi/{inv.id}")
    except Exception:
        db.rollback()
        logging.exception("Error creating DVI")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/dvi/new")


@bp.route("/<int:inv_id>", methods=["GET"])
@login_required
def view_inspection(inv_id):
    db = g.db
    inv = db.query(DVIInspection).filter(DVIInspection.id == inv_id).first()
    if not inv:
        flash("Inspection not found", "warning")
        return redirect("/dvi")
    return render_template("dvi/detail.html", inv=inv, active_page="dvi")


@bp.route("/<int:inv_id>/edit", methods=["GET"])
@login_required
def edit_inspection_form(inv_id):
    db = g.db
    inv = db.query(DVIInspection).filter(DVIInspection.id == inv_id).first()
    if not inv:
        flash("Inspection not found", "warning")
        return redirect("/dvi")
    vehicles = db.query(Vehicle).order_by(Vehicle.make).all()
    techs = db.query(Technician).filter(Technician.is_active == True).order_by(Technician.name).all()
    wos = db.query(WorkOrder).filter(WorkOrder.status.not_in(["Completed", "Invoiced", "Cancelled"])).all()
    existing = {i.check_item: i for i in inv.items}
    return render_template("dvi/form.html", inspection=inv, vehicles=vehicles,
                           technicians=techs, work_orders=wos, items=DEFAULT_ITEMS,
                           existing=existing, active_page="dvi")


@bp.route("/<int:inv_id>/edit", methods=["POST"])
@login_required
def update_inspection(inv_id):
    db = g.db
    try:
        inv = db.query(DVIInspection).filter(DVIInspection.id == inv_id).first()
        if not inv:
            flash("Inspection not found", "warning")
            return redirect("/dvi")
        inv.work_order_id = int(request.form["work_order_id"]) if request.form.get("work_order_id") else None
        inv.vehicle_id = int(request.form["vehicle_id"])
        inv.technician_id = int(request.form["technician_id"]) if request.form.get("technician_id") else None
        inv.odometer = int(request.form.get("odometer", 0)) or None
        inv.inspection_date = date.fromisoformat(request.form["inspection_date"])
        inv.summary = request.form.get("summary", "")
        inv.status = "Completed"
        db.query(DVIChecklistItem).filter(DVIChecklistItem.inspection_id == inv_id).delete()
        categories = request.form.getlist("category[]")
        item_names = request.form.getlist("item[]")
        results = request.form.getlist("result[]")
        notes_list = request.form.getlist("notes[]")
        for cat, item_name, result, note in zip(categories, item_names, results, notes_list):
            db.add(DVIChecklistItem(
                inspection_id=inv.id, category=cat, check_item=item_name,
                result=result or "Not Checked", notes=note
            ))
        db.commit()
        flash("Inspection updated", "success")
        return redirect(f"/dvi/{inv.id}")
    except Exception:
        db.rollback()
        logging.exception("Error updating DVI")
        flash("An error occurred.", "danger")
        return redirect(f"/dvi/{inv_id}/edit")
