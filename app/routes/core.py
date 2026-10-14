"""Core blueprint: shared object plus feature submodules.

Views live in the core_* modules and register on the single `bp` object
below, so URLs and `core.*` endpoint names are unchanged.
"""
from flask import Blueprint

bp = Blueprint("core", __name__)

from app.routes import (  # noqa: E402,F401
    core_admin,
    core_alerts,
    core_auth,
    core_exports,
    core_reports,
    core_system,
)
