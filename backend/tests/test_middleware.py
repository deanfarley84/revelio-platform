"""Smoke test for RequestContextMiddleware - confirms it sets X-Request-ID."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_request_id_header():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in {k.lower() for k in res.headers}


@pytest.mark.asyncio
async def test_supplied_request_id_is_echoed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/health", headers={"X-Request-ID": "test-rid-123"})
    assert res.headers.get("X-Request-ID") == "test-rid-123"
