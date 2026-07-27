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
