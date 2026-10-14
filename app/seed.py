"""Seeding entry points (kept stable for main.py and tests).

Implementation lives in seed_demo.py (fake shop data) and
seed_catalog.py (marketplace plans/templates); shared lookup data
lives in seed_data.py.
"""
from app.seed_demo import seed_demo_data  # noqa: F401
from app.seed_catalog import seed_template_data  # noqa: F401
