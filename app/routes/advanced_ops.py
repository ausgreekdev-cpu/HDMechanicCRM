"""Advanced ops blueprint: shared object plus feature submodules.

Views live in the ops_* modules and register on the single `bp` object
below, so URLs and `advanced_ops.*` endpoint names are unchanged.
"""
from flask import Blueprint

bp = Blueprint("advanced_ops", __name__, url_prefix="/ops")

from app.routes import (  # noqa: E402,F401
    ops_companies,
    ops_estimates,
    ops_fleet,
    ops_parts,
    ops_vendors,
    ops_warranty,
)
