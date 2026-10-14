"""CRM advanced blueprint: shared object plus feature submodules.

Views live in the crm_* modules and register on the single `bp` object
below, so URLs and `crm_advanced.*` endpoint names are unchanged.
"""
from flask import Blueprint

bp = Blueprint("crm_advanced", __name__, url_prefix="/crm")

from app.routes import (  # noqa: E402,F401
    crm_engagement,
    crm_hr,
    crm_messaging,
    crm_shop,
    crm_workspace,
)
