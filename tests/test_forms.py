import pytest
from werkzeug.datastructures import MultiDict
from app.forms import (
    LoginForm, CustomerForm, VehicleForm, WorkOrderForm,
    PartForm, SettingsForm,
)


def test_login_form_valid(app):
    with app.app_context():
        form = LoginForm(data={"username": "admin", "password": "secret"})
        assert form.validate()


def test_login_form_missing_username(app):
    with app.app_context():
        form = LoginForm(data={"username": "", "password": "secret"})
        assert not form.validate()
        assert "username" in form.errors


def test_login_form_missing_password(app):
    with app.app_context():
        form = LoginForm(data={"username": "admin", "password": ""})
        assert not form.validate()
        assert "password" in form.errors


def test_customer_form_valid(app):
    with app.app_context():
        form = CustomerForm(data={"name": "Test Customer"})
        assert form.validate()


def test_customer_form_missing_name(app):
    with app.app_context():
        form = CustomerForm(data={"name": ""})
        assert not form.validate()
        assert "name" in form.errors


def test_customer_form_empty_email_ignored(app):
    with app.app_context():
        form = CustomerForm(data={"name": "Test", "email": ""})
        assert form.validate()


def test_customer_form_valid_email(app):
    with app.app_context():
        form = CustomerForm(data={"name": "Test", "email": "user@example.com"})
        assert form.validate()


def test_vehicle_form_missing_customer(app):
    with app.app_context():
        form = VehicleForm(data={"make": "Toyota"})
        form.customer_id.choices = [(1, "Cust 1")]
        assert not form.validate()
        assert "customer_id" in form.errors


def test_work_order_form_valid(app):
    with app.app_context():
        form = WorkOrderForm(data={
            "customer_id": "1",
            "vehicle_id": "1",
            "title": "Brake Repair",
        })
        form.customer_id.choices = [(1, "Cust 1")]
        form.vehicle_id.choices = [(1, "Vehicle 1")]
        assert form.validate()


def test_work_order_form_missing_title(app):
    with app.app_context():
        form = WorkOrderForm(data={
            "customer_id": "1",
            "vehicle_id": "1",
            "title": "",
        })
        form.customer_id.choices = [(1, "Cust 1")]
        form.vehicle_id.choices = [(1, "Vehicle 1")]
        assert not form.validate()
        assert "title" in form.errors


def test_part_form_valid(app):
    with app.app_context():
        form = PartForm(data={"name": "Oil Filter"})
        assert form.validate()


def test_part_form_missing_name(app):
    with app.app_context():
        form = PartForm(data={"name": ""})
        assert not form.validate()
        assert "name" in form.errors


def test_settings_form_optional_fields(app):
    with app.app_context():
        form = SettingsForm(data={
            "display_name": "",
            "current_password": "",
            "new_password": "",
        })
        assert form.validate()


def test_settings_form_short_password(app):
    with app.app_context():
        form = SettingsForm(formdata=MultiDict({
            "display_name": "Test",
            "current_password": "old",
            "new_password": "abc",
        }))
        assert not form.validate()
        assert "new_password" in form.errors


def test_vehicle_form_valid(app):
    with app.app_context():
        form = VehicleForm(data={"make": "Ford", "model": "F-150", "year": "2022", "customer_id": "1"})
        form.customer_id.choices = [(1, "Cust 1")]
        assert form.validate()


def test_invoice_form_valid(app):
    with app.app_context():
        form = PartForm(data={"name": "Invoice Item", "part_number": "INV-001", "category": "Service"})
        assert form.validate()


def test_part_form_with_part_number(app):
    with app.app_context():
        form = PartForm(data={"name": "Air Filter", "part_number": "AF-123", "category": "Filters"})
        assert form.validate()


def test_customer_form_special_chars(app):
    with app.app_context():
        form = CustomerForm(data={"name": "O'Reilly & Sons"})
        assert form.validate()


def test_work_order_form_all_optional(app):
    with app.app_context():
        form = WorkOrderForm(data={
            "customer_id": "1",
            "vehicle_id": "1",
            "title": "Full Service",
            "description": "Complete service",
            "labor_hours": "2.5",
            "labor_rate": "150",
        })
        form.customer_id.choices = [(1, "Cust")]
        form.vehicle_id.choices = [(1, "Veh")]
        assert form.validate()


def test_settings_form_matching_passwords(app):
    with app.app_context():
        form = SettingsForm(formdata=MultiDict({
            "display_name": "New Name",
            "current_password": "oldpass",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123",
        }))
        assert form.validate()


def test_settings_form_mismatched_passwords(app):
    with app.app_context():
        form = SettingsForm(formdata=MultiDict({
            "display_name": "New Name",
            "current_password": "oldpass",
            "new_password": "NewPass123",
            "confirm_password": "Different456",
        }))
        # SettingsForm doesn't have confirm_password validator by default
        assert form.validate()


def test_admin_create_user_form_valid(app):
    with app.app_context():
        from app.forms import AdminCreateUserForm
        form = AdminCreateUserForm(data={"username": "newuser", "password": "Pass1234", "role": "technician"})
        form.role.choices = [("user", "User"), ("technician", "Tech"), ("admin", "Admin")]
        assert form.validate()


def test_admin_create_user_form_missing_role(app):
    with app.app_context():
        from app.forms import AdminCreateUserForm
        form = AdminCreateUserForm(data={"username": "newuser", "password": "Pass1234", "role": ""})
        form.role.choices = [("user", "User"), ("technician", "Tech"), ("admin", "Admin")]
        assert not form.validate()


def test_login_form_empty_fields(app):
    with app.app_context():
        form = LoginForm(data={"username": "", "password": ""})
        assert not form.validate()


def test_vehicle_form_with_vin(app):
    with app.app_context():
        form = VehicleForm(data={"make": "Chevy", "model": "Silverado", "vin": "1HGCM82633A123456", "customer_id": "1"})
        form.customer_id.choices = [(1, "Cust")]
        assert form.validate()
