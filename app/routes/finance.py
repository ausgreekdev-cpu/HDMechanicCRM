"""Finance blueprint: shared object plus feature submodules.

Views live in the fin_* modules and register on the single `bp` object
below, so URLs and `finance.*` endpoint names are unchanged.
"""
from flask import Blueprint

bp = Blueprint("finance", __name__, url_prefix="/finance")

from app.routes import (  # noqa: E402,F401
    fin_bank,
    fin_compliance,
    fin_expenses,
    fin_receivables,
    fin_reporting,
)
