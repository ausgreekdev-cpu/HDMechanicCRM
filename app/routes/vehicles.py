from flask import Blueprint, render_template, request, redirect, flash, g
import logging
from app.models import Vehicle, Customer
from app.auth import login_required
from app.helpers import paginate
import urllib.parse

bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")


@bp.route("", methods=["GET"])
@login_required
def list_vehicles():
    db = g.db
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    query = db.query(Vehicle).join(Customer)
    if search:
        query = query.filter(
            Vehicle.make.ilike(f"%{search}%") | Vehicle.model.ilike(f"%{search}%") |
            Vehicle.license_plate.ilike(f"%{search}%") | Vehicle.vin.ilike(f"%{search}%") |
            Customer.name.ilike(f"%{search}%")
        )
    params = {k: v for k, v in request.args.items() if k not in ("page", "per_page")}
    extra = urllib.parse.urlencode(params) if params else ""
    p = paginate(query.order_by(Vehicle.make), page, per_page)
    return render_template("vehicles/list.html", p=p, search=search, active_page="vehicles", extra=extra)


@bp.route("/new", methods=["GET"])
@login_required
def new_vehicle_form():
    db = g.db
    customers = db.query(Customer).order_by(Customer.name).all()
    preselected = request.args.get("customer_id", "")
    return render_template("vehicles/form.html", vehicle=None, customers=customers,
                           preselected_customer=preselected, active_page="vehicles")


@bp.route("/new", methods=["POST"])
@login_required
def create_vehicle():
    db = g.db
    try:
        v = Vehicle(customer_id=int(request.form["customer_id"]),
                    make=request.form.get("make", ""), model=request.form.get("model", ""),
                    year=int(request.form.get("year", 0)), vin=request.form.get("vin", ""),
                    license_plate=request.form.get("license_plate", ""),
                    engine_type=request.form.get("engine_type", ""), notes=request.form.get("notes", ""))
        db.add(v)
        db.commit()
        flash("Vehicle added", "success")
        return redirect(f"/vehicles/{v.id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in vehicles")
        flash("An error occurred. Please try again.", "danger")
        return redirect("/vehicles/new")


@bp.route("/<int:vehicle_id>", methods=["GET"])
@login_required
def view_vehicle(vehicle_id):
    db = g.db
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        flash("Vehicle not found", "warning")
        return redirect("/vehicles")
    return render_template("vehicles/detail.html", vehicle=vehicle, active_page="vehicles")


@bp.route("/<int:vehicle_id>/edit", methods=["GET"])
@login_required
def edit_vehicle_form(vehicle_id):
    db = g.db
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return redirect("/vehicles")
    customers = db.query(Customer).order_by(Customer.name).all()
    return render_template("vehicles/form.html", vehicle=vehicle, customers=customers,
                           preselected_customer="", active_page="vehicles")


@bp.route("/<int:vehicle_id>/edit", methods=["POST"])
@login_required
def update_vehicle(vehicle_id):
    db = g.db
    try:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if v:
            v.customer_id = int(request.form["customer_id"])
            v.make = request.form.get("make", "")
            v.model = request.form.get("model", "")
            v.year = int(request.form.get("year", 0))
            v.vin = request.form.get("vin", "")
            v.license_plate = request.form.get("license_plate", "")
            v.engine_type = request.form.get("engine_type", "")
            v.notes = request.form.get("notes", "")
            db.commit()
            flash("Vehicle updated", "success")
        return redirect(f"/vehicles/{vehicle_id}")
    except Exception as e:
        db.rollback()
        logging.exception("Error in vehicles")
        flash("An error occurred. Please try again.", "danger")
        return redirect(f"/vehicles/{vehicle_id}/edit")


@bp.route("/<int:vehicle_id>/delete", methods=["POST"])
@login_required
def delete_vehicle(vehicle_id):
    db = g.db
    try:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if v:
            db.delete(v)
            db.commit()
            flash("Vehicle deleted", "success")
    except Exception:
        db.rollback()
        logging.exception("Delete vehicle failed")
        flash("Cannot delete: vehicle is linked to existing records", "danger")
    return redirect("/vehicles")
