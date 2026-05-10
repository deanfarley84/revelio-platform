"""
In-memory rate limiter shared across the FastAPI app.

Single-instance is fine on the current Render free / Starter plans.
When we move to multi-instance we should swap the storage URI to the
existing Redis instance via REDIS_URL.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Default key: client IP. Endpoint-specific limits are applied via
# @limiter.limit decorators on the route handler.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
