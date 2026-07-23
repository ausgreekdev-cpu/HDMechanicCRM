import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_database_url():
    env_url = os.environ.get("CRM_DATABASE_URL", "")
    if env_url:
        return env_url

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "crm.db")
    return f"sqlite:///{db_path}"


DATABASE_URL = _get_database_url()
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs = {
    "echo": os.environ.get("CRM_DB_ECHO", "0") == "1",
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = int(os.environ.get("CRM_DB_POOL_SIZE", "10"))
    _engine_kwargs["max_overflow"] = int(os.environ.get("CRM_DB_MAX_OVERFLOW", "20"))
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = int(os.environ.get("CRM_DB_POOL_RECYCLE", "3600"))

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import Base
    Base.metadata.create_all(bind=engine)
