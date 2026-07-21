import os
import pytest

os.environ["CRM_SECRET_KEY"] = "test-secret-key-for-testing-only-1234567890abcdef"

from app import create_app
from app.database import Base, engine, SessionLocal


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        yield app
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        session = SessionLocal()
        yield session
        session.rollback()
        session.close()
