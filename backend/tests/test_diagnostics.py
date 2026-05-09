"""
Core diagnostic API tests.
Run with: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_diagnostic_payload():
    return {
        "company_name": "Test Corp",
        "website": "testcorp.com",
        "vertical": "retail",
        "tier": "core",
        "monthly_volume": 1000000,
        "monthly_transactions": 20000,
        "avg_order_value": 50.0,
        "cross_border_pct": 25.0,
        "psps_used": ["Stripe"],
        "auth_rate": 87.5,
        "decline_rate": 12.5,
        "chargeback_rate": 0.75,
        "retry_enabled": False,
        "payment_methods": ["Visa", "Mastercard"],
    }


def test_health():
    import requests
    # Basic sanity — app imports cleanly
    from app.main import app
    assert app is not None


def test_prompt_builder():
    from app.prompts.diagnostic_prompts import build_prompt
    system, user = build_prompt("lite", {"company_name": "Test", "monthly_volume_gbp": 1000000}, {})
    assert "leakage" in user.lower()
    assert "JSON" in user


def test_prompt_builder_core():
    from app.prompts.diagnostic_prompts import build_prompt
    system, user = build_prompt("core", {"company_name": "Test", "monthly_volume_gbp": 5000000, "auth_rate_pct": 86.0}, {"auth_rate_retail": {"default": 90}})
    assert "authorisation" in user.lower()
    assert "annual_leakage_estimate" in user


def test_prompt_builder_enterprise():
    from app.prompts.diagnostic_prompts import build_prompt
    system, user = build_prompt("enterprise", {"company_name": "Test", "monthly_volume_gbp": 10000000}, {})
    assert "margin_compression" in user
    assert "routing_analysis" in user


def test_file_parser_csv():
    from app.services.file_parser import parse_file
    csv_content = b"total_volume,auth_rate,decline_rate,chargeback_rate\n4700000,86.2,13.8,0.82"
    result = parse_file(csv_content, "csv")
    assert "fields" in result
    assert result["confidence"] > 0


def test_file_parser_empty():
    from app.services.file_parser import parse_file
    result = parse_file(b"", "csv")
    assert "error" in result or result.get("confidence", 0) == 0.0


def test_confidence_classifier():
    from app.services.ai_service import classify_confidence
    from app.models.user import Diagnostic

    d = Diagnostic()
    d.monthly_volume = 1000000
    d.auth_rate = 86.0
    d.decline_rate = 14.0
    d.cross_border_pct = 30.0
    d.psps_used = ["Stripe"]
    d.chargeback_rate = 0.8
    d.payment_methods = ["Visa", "Mastercard"]
    d.retry_enabled = False
    assert classify_confidence(d) == "high"


def test_confidence_classifier_low():
    from app.services.ai_service import classify_confidence
    from app.models.user import Diagnostic

    d = Diagnostic()
    d.monthly_volume = 500000
    # Most fields missing
    assert classify_confidence(d) == "low"


def test_merge_parsed_fields():
    from app.services.file_parser import merge_parsed_fields
    results = [
        {"fields": {"monthly_volume": 1000000, "auth_rate": 86.0}, "file_name": "file1.csv"},
        {"fields": {"chargeback_rate": 0.8, "auth_rate": 87.0}, "file_name": "file2.csv"},
    ]
    merged = merge_parsed_fields(results)
    assert merged["fields"]["monthly_volume"] == 1000000
    assert merged["fields"]["auth_rate"] == 87.0  # later file wins
    assert merged["fields"]["chargeback_rate"] == 0.8
