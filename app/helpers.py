import os
import logging
import json
import redis
from math import ceil
from functools import wraps
from app import USE_REDIS, cache

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("CRM_REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            logger.info("Redis connection established at %s", redis_url)
        except Exception as e:
            logger.warning("Redis unavailable at %s, falling back to in-memory: %s", redis_url, e)
            _redis_client = None
    return _redis_client


def cached_query(key_prefix, timeout=60):
    """Decorator to cache query results."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not USE_REDIS:
                return f(*args, **kwargs)
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        return wrapped
    return decorator


def cache_get(key):
    """Get a cached value by key. Returns None if not found or expired."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            val = redis_client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning("Redis cache_get error for key %s: %s", key, e)
            return None
    return None


def cache_set(key, value, ttl=60):
    """Set a cached value with TTL in seconds."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning("Redis cache_set error for key %s: %s", key, e)
            return False
    return False


def cache_delete(key):
    """Delete a cached value by key."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning("Redis cache_delete error for key %s: %s", key, e)
            return False
    return False


def send_email(to_email, subject, body_html, body_text=None):
    api_key = os.environ.get("CRM_SENDGRID_API_KEY", "")
    from_email = os.environ.get("CRM_FROM_EMAIL", "noreply@hdmechaniccrm.com")
    from_name = os.environ.get("CRM_FROM_NAME", "HD Mechanic CRM")

    if not api_key:
        logger.info("SendGrid not configured — email logged: To=%s Subject=%s", to_email, subject)
        return None

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Content

        content = Content("text/html", body_html)
        message = Mail(from_email=f"{from_name} <{from_email}>", to_emails=to_email, subject=subject, html_content=content)
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info("Email sent: To=%s Status=%s", to_email, response.status_code)
        return response
    except ImportError:
        logger.warning("sendgrid package not installed — pip install sendgrid")
        return None
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return None


def paginate(query, page, per_page=50):
    page = max(1, page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, ceil(total / per_page))
    return {
        "rows": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }