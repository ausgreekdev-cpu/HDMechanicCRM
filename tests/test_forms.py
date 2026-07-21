import pytest
from app.forms import (
    LoginForm, CustomerForm, VehicleForm, WorkOrderForm,
    PartForm, SettingsForm,
)


class FakePostData(dict):
    def getlist(self, key):
        v = self.get(key)
        return [v] if v is not None else []


def test_login_form_valid():
    form = LoginForm(data={"username": "admin", "password": "secret"})
    assert form.validate()


def test_login_form_missing_username():
    form = LoginForm(data={"username": "", "password": "secret"})
    assert not form.validate()
    assert "username" in form.errors


def test_login_form_missing_password():
    form = LoginForm(data={"username": "admin", "password": ""})
    assert not form.validate()
    assert "password" in form.errors


def test_customer_form_valid():
    form = CustomerForm(data={"name": "Test Customer"})
    assert form.validate()


def test_customer_form_missing_name():
    form = CustomerForm(data={"name": ""})
    assert not form.validate()
    assert "name" in form.errors


def test_customer_form_invalid_email():
    form = CustomerForm(data={"name": "Test", "email": "not-an-email"})
    assert not form.validate()
    assert "email" in form.errors


def test_customer_form_valid_email():
    form = CustomerForm(data={"name": "Test", "email": "user@example.com"})
    assert form.validate()


def test_vehicle_form_missing_customer():
    form = VehicleForm(data={"make": "Toyota"})
    assert not form.validate()
    assert "customer_id" in form.errors


def test_work_order_form_valid():
    form = WorkOrderForm(data={
        "customer_id": "1",
        "vehicle_id": "1",
        "title": "Brake Repair",
    })
    assert form.validate()


def test_work_order_form_missing_title():
    form = WorkOrderForm(data={
        "customer_id": "1",
        "vehicle_id": "1",
        "title": "",
    })
    assert not form.validate()
    assert "title" in form.errors


def test_part_form_valid():
    form = PartForm(data={"name": "Oil Filter"})
    assert form.validate()


def test_part_form_missing_name():
    form = PartForm(data={"name": ""})
    assert not form.validate()
    assert "name" in form.errors


def test_settings_form_optional_fields():
    form = SettingsForm(data={
        "display_name": "",
        "current_password": "",
        "new_password": "",
    })
    assert form.validate()


def test_settings_form_short_password():
    form = SettingsForm(data={
        "display_name": "Test",
        "current_password": "old",
        "new_password": "abc",
    })
    assert not form.validate()
    assert "new_password" in form.errors
