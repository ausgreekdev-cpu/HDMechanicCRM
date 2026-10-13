from datetime import datetime, timezone


def utcnow():
    """Return current UTC time (naive, for backwards compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def strftime_sql(fmt, column):
    """Dialect-aware SQL date formatting.

    SQLite supports strftime(); PostgreSQL needs to_char() with
    translated format codes. Falls back to strftime() for other
    dialects (MySQL et al. are not currently supported by the app).
    """
    from sqlalchemy import func
    from app.database import engine

    if engine.dialect.name == "postgresql":
        pg_fmt = fmt.replace("%Y", "YYYY").replace("%m", "MM").replace("%d", "DD")
        return func.to_char(column, pg_fmt)
    return func.strftime(fmt, column)
