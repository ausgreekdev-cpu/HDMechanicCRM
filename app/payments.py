"""Backwards-compatibility shim — Stripe has been replaced by Square."""
from app.payments_square import (  # noqa: F401
    square_enabled as stripe_enabled,
    get_square_config,
    create_payment_link,
    create_subscription,
    cancel_subscription,
    verify_webhook_signature,
)
