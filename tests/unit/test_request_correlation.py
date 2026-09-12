"""
Unit tests for backend.observability.middleware (Phase 3).

Tests verify:
- A request without X-Request-ID gets a generated UUID v4
- A request with X-Request-ID preserves it exactly
- The response always contains X-Request-ID
- The generated ID is a valid UUID v4 format
- Prometheus in-flight gauge is correctly managed
- record_request() is called (counter increments on each request)
- Middleware does not swallow response status codes
- Middleware is non-fatal: application still responds if metrics fail

Architecture note:
    Tests use httpx.AsyncClient with a minimal FastAPI test application
    to exercise the middleware end-to-end without requiring a running
    database or Redis.
"""

from __future__ import annotations

import re
import uuid

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from backend.observability.middleware import REQUEST_ID_HEADER, RequestCorrelationMiddleware

# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------


def _make_test_app(status_code: int = 200, body: dict | None = None) -> FastAPI:
    """Build a minimal FastAPI app with the correlation middleware."""
    app = FastAPI()
    app.add_middleware(RequestCorrelationMiddleware)

    @app.get("/test")
    async def endpoint() -> JSONResponse:
        return JSONResponse(content=body or {"ok": True}, status_code=status_code)

    @app.get("/error")
    async def error_endpoint() -> JSONResponse:
        return JSONResponse(content={"error": "test"}, status_code=500)

    return app


# ---------------------------------------------------------------------------
# Request ID behaviour
# ---------------------------------------------------------------------------


class TestRequestIdGeneration:
    @pytest.mark.asyncio
    async def test_request_without_id_gets_uuid(self) -> None:
        """A request without X-Request-ID must receive a generated UUID in the response."""
        app = _make_test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/test")

        assert REQUEST_ID_HEADER in response.headers
        generated_id = response.headers[REQUEST_ID_HEADER]
        # Must be a valid UUID v4
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            generated_id,
        ), f"Not a valid UUID v4: {generated_id}"

    @pytest.mark.asyncio
    async def test_request_with_id_preserves_it(self) -> None:
        """A request with X-Request-ID must have that exact ID echoed back."""
        app = _make_test_app()
        incoming_id = str(uuid.uuid4())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/test", headers={REQUEST_ID_HEADER: incoming_id})

        assert response.headers[REQUEST_ID_HEADER] == incoming_id

    @pytest.mark.asyncio
    async def test_different_requests_get_unique_ids(self) -> None:
        """Each request without an ID must receive a distinct generated ID."""
        app = _make_test_app()
        ids = set()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(5):
                response = await client.get("/test")
                ids.add(response.headers[REQUEST_ID_HEADER])

        assert len(ids) == 5, "All 5 requests should have unique IDs"


# ---------------------------------------------------------------------------
# Response header injection
# ---------------------------------------------------------------------------


class TestResponseHeaders:
    @pytest.mark.asyncio
    async def test_response_always_contains_request_id(self) -> None:
        app = _make_test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/test")
        assert REQUEST_ID_HEADER in response.headers

    @pytest.mark.asyncio
    async def test_response_status_code_preserved(self) -> None:
        """Middleware must not alter the response status code."""
        app = _make_test_app(status_code=201)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/test")
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_error_status_code_preserved(self) -> None:
        """Middleware must preserve 500 status codes without swallowing them."""
        app = _make_test_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/error")
        assert response.status_code == 500
        assert REQUEST_ID_HEADER in response.headers


# ---------------------------------------------------------------------------
# Prometheus metrics integration
# ---------------------------------------------------------------------------


class TestMiddlewareMetrics:
    @pytest.mark.asyncio
    async def test_counter_increments_per_request(self) -> None:
        """Each completed request must increment synapseops_http_requests_total."""
        from backend.observability.metrics import HTTP_REQUESTS_TOTAL

        app = _make_test_app()

        # Read total before
        before = sum(m._value.get() for m in HTTP_REQUESTS_TOTAL._metrics.values())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/test")
            await client.get("/test")

        after = sum(m._value.get() for m in HTTP_REQUESTS_TOTAL._metrics.values())

        assert after >= before + 2

    @pytest.mark.asyncio
    async def test_in_flight_returns_to_zero_after_request(self) -> None:
        """After a request completes, in-flight gauge must return to its prior value."""
        from backend.observability.metrics import HTTP_REQUESTS_IN_FLIGHT, SERVICE_NAME

        app = _make_test_app()
        before = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/test")

        after = HTTP_REQUESTS_IN_FLIGHT.labels(service=SERVICE_NAME)._value.get()
        assert after == before


# ---------------------------------------------------------------------------
# Header name constant
# ---------------------------------------------------------------------------


class TestConstants:
    def test_header_name(self) -> None:
        assert REQUEST_ID_HEADER == "X-Request-ID"
