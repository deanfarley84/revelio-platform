"""HTTP middleware: request ID, structured access logging, latency timing."""
from __future__ import annotations
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("vyre.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Adds an X-Request-ID header (echoes one supplied by the client, otherwise
    generates one) and emits a single-line structured log per request with
    method, path, status code and latency. Cheap enough to run on every
    request; useful for correlating logs to a specific call.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "request_failed rid=%s method=%s path=%s ms=%d",
                request_id, request.method, request.url.path, elapsed_ms,
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        # Liveness probes are noisy; log them at debug.
        level = logging.DEBUG if request.url.path in ("/health", "/ready") else logging.INFO
        logger.log(
            level,
            "rid=%s %s %s -> %d in %dms",
            request_id, request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response
