"""
SynapseOps Observability -- Request Correlation Middleware (Phase 3).

Provides a Starlette middleware that:

1. Request ID correlation
   - Reads X-Request-ID from the incoming request.
   - Generates a UUID v4 if the header is absent.
   - Binds the request_id to the structlog context (visible in all log
     lines emitted during this request).
   - Returns X-Request-ID in the response headers.

2. Prometheus metrics recording
   - Tracks HTTP_REQUESTS_IN_FLIGHT gauge (incremented on entry, decremented
     on exit, regardless of success or failure).
   - On completion, calls record_request() to increment the counter and
     record a histogram observation.

3. Structured request logging
   - Logs request start and completion with: method, path, status_code,
     duration_ms, request_id, trace_id (from active OTel span).
   - Sensitive headers (Authorization, Cookie, X-API-Key) are never logged.

Design:
   The route template (e.g. "/health/{item}") rather than the raw path
   is used as the `route` label for Prometheus to keep cardinality bounded.
   Falls back to the raw path when the route template is unavailable.

   All failure modes are caught: a broken metrics subsystem must never
   crash the application.
"""

from __future__ import annotations

import time
import uuid

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request  # noqa: TC002
from starlette.responses import Response  # noqa: TC002
from starlette.routing import Match

from backend.observability.metrics import (
    HTTP_REQUESTS_IN_FLIGHT,
    SERVICE_NAME,
    record_request,
)

logger = structlog.get_logger("observability.middleware")

# Header name for request correlation
REQUEST_ID_HEADER = "X-Request-ID"


def _get_route_template(request: Request) -> str:
    """Return the matched route template or the raw path as fallback.

    Using the template (e.g. "/api/v1/simulation/failures/{target}")
    instead of the raw URL keeps Prometheus label cardinality bounded.
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


def _get_trace_id() -> str:
    """Return the current OTel trace ID or empty string."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return ""


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for request correlation, metrics, and structured logging.

    Register on the FastAPI app with::

        app.add_middleware(RequestCorrelationMiddleware)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ------------------------------------------------------------------ #
        # 1. Resolve / generate request ID
        # ------------------------------------------------------------------ #
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # ------------------------------------------------------------------ #
        # 2. Bind to structlog context for the duration of this request
        # ------------------------------------------------------------------ #
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # ------------------------------------------------------------------ #
        # 3. Track in-flight requests
        # ------------------------------------------------------------------ #
        import contextlib

        with contextlib.suppress(Exception):
            HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).inc()

        start = time.perf_counter()
        status_code = 500

        try:
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
            )

            response: Response = await call_next(request)
            status_code = response.status_code

        except Exception as exc:
            logger.exception("request_unhandled_error", exc_info=exc)
            raise
        finally:
            duration = time.perf_counter() - start
            route = _get_route_template(request)
            trace_id = _get_trace_id()

            # ------------------------------------------------------------------ #
            # 4. Record Prometheus metrics
            # ------------------------------------------------------------------ #
            try:
                record_request(
                    method=request.method,
                    route=route,
                    status_code=status_code,
                    duration_seconds=duration,
                )
                HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME).dec()
            except Exception:
                pass

            # ------------------------------------------------------------------ #
            # 5. Structured log: request complete
            # ------------------------------------------------------------------ #
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                route=route,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
                trace_id=trace_id or None,
            )

        # ------------------------------------------------------------------ #
        # 6. Return request ID in response headers
        # ------------------------------------------------------------------ #
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
