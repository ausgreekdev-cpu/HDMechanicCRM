from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, IntegerField, FloatField,
    SelectField, DateField, BooleanField, SubmitField,
)
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired("Username is required")])
    password = PasswordField("Password", validators=[DataRequired("Password is required")])


class SettingsForm(FlaskForm):
    display_name = StringField("Display Name", validators=[Optional(), Length(max=200)])
    current_password = PasswordField("Current Password", validators=[Optional()])
    new_password = PasswordField("New Password", validators=[Optional(), Length(min=6, message="Password must be at least 6 characters")])


class AdminCreateUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired("Username is required"), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired("Password is required")])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=200)])
    role = SelectField("Role", choices=[("user", "User"), ("admin", "Admin")], default="user")


class CustomerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired("Customer name is required"), Length(max=200)])
    company = StringField("Company", validators=[Optional(), Length(max=200)])
    phone = StringField("Phone", validators=[Optional(), Length(max=50)])
    email = StringField("Email", validators=[Optional(), Email("Please enter a valid email address"), Length(max=200)])
    address = TextAreaField("Address", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])


class VehicleForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired("Customer is required")])
    make = StringField("Make", validators=[Optional(), Length(max=100)])
    model = StringField("Model", validators=[Optional(), Length(max=100)])
    year = IntegerField("Year", validators=[Optional(), NumberRange(min=1900, max=2100, message="Enter a valid year")])
    vin = StringField("VIN", validators=[Optional(), Length(max=50)])
    license_plate = StringField("License Plate", validators=[Optional(), Length(max=30)])
    engine_type = StringField("Engine Type", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("Notes", validators=[Optional()])


class WorkOrderForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired("Customer is required")])
    vehicle_id = SelectField("Vehicle", coerce=int, validators=[DataRequired("Vehicle is required")])
    title = StringField("Title", validators=[DataRequired("Title is required"), Length(max=300)])
    description = TextAreaField("Description", validators=[Optional()])
    diagnosis = TextAreaField("Diagnosis", validators=[Optional()])
    status = SelectField("Status", choices=[
        ("New", "New"), ("Diagnosing", "Diagnosing"), ("Waiting Parts", "Waiting Parts"),
        ("In Progress", "In Progress"), ("Completed", "Completed"), ("Invoiced", "Invoiced"),
        ("Cancelled", "Cancelled"),
    ], default="New")
    labor_hours = FloatField("Labor Hours", validators=[Optional(), NumberRange(min=0)])
    labor_rate = FloatField("Labor Rate", validators=[Optional(), NumberRange(min=0)])
    odometer = IntegerField("Odometer", validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField("Notes", validators=[Optional()])


class PartForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired("Part name is required"), Length(max=300)])
    part_number = StringField("Part Number", validators=[Optional(), Length(max=100)])
    barcode = StringField("Barcode", validators=[Optional(), Length(max=100)])
    category = StringField("Category", validators=[Optional(), Length(max=100)])
    supplier = StringField("Supplier", validators=[Optional(), Length(max=200)])
    supplier_part_number = StringField("Supplier Part #", validators=[Optional(), Length(max=100)])
    cost_price = FloatField("Cost Price", validators=[Optional(), NumberRange(min=0)])
    selling_price = FloatField("Selling Price", validators=[Optional(), NumberRange(min=0)])
    quantity_on_hand = IntegerField("Qty On Hand", validators=[Optional(), NumberRange(min=0)])
    min_quantity = IntegerField("Min Quantity", validators=[Optional(), NumberRange(min=0)])
    max_quantity = IntegerField("Max Quantity", validators=[Optional(), NumberRange(min=0)])
    location = StringField("Location", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("Notes", validators=[Optional()])


class ServiceReminderForm(FlaskForm):
    vehicle_id = SelectField("Vehicle", coerce=int, validators=[DataRequired("Vehicle is required")])
    service_type = StringField("Service Type", validators=[DataRequired("Service type is required"), Length(max=100)])
    interval_miles = IntegerField("Interval (Miles)", validators=[Optional(), NumberRange(min=0)])
    interval_days = IntegerField("Interval (Days)", validators=[Optional(), NumberRange(min=0)])
    last_odometer = IntegerField("Last Odometer", validators=[Optional(), NumberRange(min=0)])
    last_service_date = DateField("Last Service Date", validators=[Optional()], format="%Y-%m-%d")
    next_due_miles = IntegerField("Next Due (Miles)", validators=[Optional(), NumberRange(min=0)])
    next_due_date = DateField("Next Due Date", validators=[Optional()], format="%Y-%m-%d")
    notes = TextAreaField("Notes", validators=[Optional()])


class RecurringWOForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired("Customer is required")])
    vehicle_id = SelectField("Vehicle", coerce=int, validators=[DataRequired("Vehicle is required")])
    title = StringField("Title", validators=[DataRequired("Title is required"), Length(max=300)])
    description = TextAreaField("Description", validators=[Optional()])
    interval_days = IntegerField("Interval (Days)", validators=[Optional(), NumberRange(min=1)])
    interval_miles = IntegerField("Interval (Miles)", validators=[Optional(), NumberRange(min=0)])
    labor_hours = FloatField("Labor Hours", validators=[Optional(), NumberRange(min=0)])
    labor_rate = FloatField("Labor Rate", validators=[Optional(), NumberRange(min=0)])
    next_due_date = DateField("Next Due Date", validators=[Optional()], format="%Y-%m-%d")
    notes = TextAreaField("Notes", validators=[Optional()])
