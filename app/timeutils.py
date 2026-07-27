from datetime import datetime, timezone


def utcnow():
    """Return current UTC time (naive, for backwards compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
