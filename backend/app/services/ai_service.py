"""
AI Analysis Service
Calls Claude API, handles tier-based prompting, parses structured output.
"""
import json
import anthropic
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user import Diagnostic, BenchmarkConfig
from app.prompts.diagnostic_prompts import build_prompt

# AsyncAnthropic so /diagnostics/{id}/submit doesn't block the event loop while
# Claude is responding. Inline jobs are running on the request thread on free
# tier and a sync call would block all other requests for 10-30s.
client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def get_benchmarks(db: AsyncSession, vertical: Optional[str] = None) -> dict:
    """Fetch current benchmark config from DB for injection into prompts."""
    result = await db.execute(select(BenchmarkConfig))
    rows = result.scalars().all()

    benchmarks = {}
    for row in rows:
        # Prefer vertical-specific over 'all'
        if row.vertical == "all" or row.vertical == vertical:
            benchmarks[row.key] = {
                "label": row.label,
                "low": float(row.value_low),
                "high": float(row.value_high),
                "default": float(row.value_default),
                "unit": row.unit,
                "vertical": row.vertical,
            }
    return benchmarks


def build_merchant_data(diagnostic: Diagnostic) -> dict:
    """Serialise diagnostic fields into merchant data dict for prompt injection."""
    return {
        "company_name": diagnostic.company_name,
        "website": diagnostic.website,
        "vertical": diagnostic.vertical,
        "tier": diagnostic.tier,
        "monthly_volume_gbp": float(diagnostic.monthly_volume) if diagnostic.monthly_volume else None,
        "annual_volume_gbp": float(diagnostic.monthly_volume) * 12 if diagnostic.monthly_volume else None,
        "monthly_transactions": diagnostic.monthly_transactions,
        "avg_order_value_gbp": float(diagnostic.avg_order_value) if diagnostic.avg_order_value else None,
        "cross_border_pct": float(diagnostic.cross_border_pct) if diagnostic.cross_border_pct else None,
        "psps_used": diagnostic.psps_used,
        "regions": diagnostic.regions,
        "auth_rate_pct": float(diagnostic.auth_rate) if diagnostic.auth_rate else None,
        "decline_rate_pct": float(diagnostic.decline_rate) if diagnostic.decline_rate else None,
        "soft_decline_pct": float(diagnostic.soft_decline_pct) if diagnostic.soft_decline_pct else None,
        "hard_decline_pct": float(diagnostic.hard_decline_pct) if diagnostic.hard_decline_pct else None,
        "top_decline_reasons": diagnostic.top_decline_reasons,
        "chargeback_rate_pct": float(diagnostic.chargeback_rate) if diagnostic.chargeback_rate else None,
        "refund_rate_pct": float(diagnostic.refund_rate) if diagnostic.refund_rate else None,
        "payment_methods": diagnostic.payment_methods,
        "retry_enabled": diagnostic.retry_enabled,
        "retry_notes": diagnostic.retry_notes,
        "checkout_currencies": diagnostic.checkout_currencies,
        "settlement_currencies": diagnostic.settlement_currencies,
        "pricing_model": diagnostic.pricing_model,
        "mdr_pct": float(diagnostic.mdr) if diagnostic.mdr else None,
        "fx_fee_spread_pct": float(diagnostic.fx_fee_spread) if diagnostic.fx_fee_spread else None,
        "scheme_fee_visibility": diagnostic.scheme_fee_visibility,
        "acquiring_setup": diagnostic.acquiring_setup,
        "routing_setup": diagnostic.routing_setup,
        "additional_context": diagnostic.additional_context,
        "parsed_data": diagnostic.parsed_data,
    }


async def run_ai_analysis(diagnostic: Diagnostic, db: AsyncSession) -> Tuple[dict, dict]:
    """
    Main entry point: run Claude analysis for a diagnostic.
    Returns (parsed AI output dict, benchmarks snapshot used).
    """
    benchmarks = await get_benchmarks(db, vertical=diagnostic.vertical)
    merchant_data = build_merchant_data(diagnostic)

    system_prompt, user_prompt = build_prompt(
        tier=diagnostic.tier,
        merchant_data=merchant_data,
        benchmarks=benchmarks,
    )

    response = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    try:
        ai_output = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}\nRaw: {raw_text[:500]}")

    # Store token usage
    ai_output["_meta"] = {
        "model": settings.ANTHROPIC_MODEL,
        "prompt_version": settings.AI_PROMPT_VERSION,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "benchmarks_used": list(benchmarks.keys()),
    }

    return ai_output, benchmarks


def classify_confidence(diagnostic: Diagnostic) -> str:
    """Pre-classify confidence before AI runs, used to flag low-quality submissions."""
    score = 0
    if diagnostic.monthly_volume: score += 2
    if diagnostic.auth_rate: score += 2
    if diagnostic.decline_rate: score += 1
    if diagnostic.cross_border_pct: score += 1
    if diagnostic.psps_used: score += 1
    if diagnostic.chargeback_rate: score += 1
    if diagnostic.payment_methods: score += 1
    if diagnostic.retry_enabled is not None: score += 1

    if score >= 7: return "high"
    if score >= 4: return "medium"
    return "low"
