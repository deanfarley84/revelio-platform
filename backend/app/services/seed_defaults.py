"""
Idempotent default-data seeding.

Runs from the lifespan on boot. Only inserts rows that aren't already present,
so it's safe to run on every startup. Currently seeds the benchmark_config
table with sensible payment-industry baselines used by the AI prompt.
"""
from __future__ import annotations
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import BenchmarkConfig

logger = logging.getLogger("vyre.seed")


# Payment-industry baselines. Each row is keyed on (category, key, vertical).
# `value_default` is what the AI uses when no operator override exists; low/high
# bound the plausible range. Operators can edit these in /admin/benchmarks.
DEFAULT_BENCHMARKS = [
    # ── Authorisation rates by vertical ─────────────────────────
    {"category": "auth_rate", "key": "auth_rate_retail", "label": "Retail auth rate",
     "value_low": 86.0, "value_high": 94.0, "value_default": 90.0,
     "unit": "percent", "vertical": "retail",
     "notes": "Card-not-present retail benchmark across major PSPs."},
    {"category": "auth_rate", "key": "auth_rate_subscription", "label": "Subscription auth rate",
     "value_low": 84.0, "value_high": 92.0, "value_default": 88.0,
     "unit": "percent", "vertical": "subscription",
     "notes": "Subscription billing typically runs 1-2pp below retail due to recurring decline density."},
    {"category": "auth_rate", "key": "auth_rate_marketplace", "label": "Marketplace auth rate",
     "value_low": 85.0, "value_high": 93.0, "value_default": 89.0,
     "unit": "percent", "vertical": "marketplace",
     "notes": "Marketplaces vary widely by buyer profile; mid value is conservative."},
    {"category": "auth_rate", "key": "auth_rate_travel", "label": "Travel auth rate",
     "value_low": 80.0, "value_high": 90.0, "value_default": 85.0,
     "unit": "percent", "vertical": "travel",
     "notes": "Travel runs lower due to high AOV and issuer scrutiny."},
    {"category": "auth_rate", "key": "auth_rate_general", "label": "General auth rate",
     "value_low": 84.0, "value_high": 93.0, "value_default": 89.0,
     "unit": "percent", "vertical": "all",
     "notes": "Fallback when vertical is unknown."},

    # ── Decline composition ─────────────────────────────────────
    {"category": "decline_mix", "key": "soft_decline_share", "label": "Soft decline share of declines",
     "value_low": 50.0, "value_high": 75.0, "value_default": 65.0,
     "unit": "percent", "vertical": "all",
     "notes": "Of all declines, the share that are recoverable via retry."},
    {"category": "retry", "key": "retry_recovery_uplift", "label": "Retry recovery uplift",
     "value_low": 1.4, "value_high": 3.2, "value_default": 2.1,
     "unit": "percent_of_volume", "vertical": "all",
     "notes": "Volume recovered when a properly configured retry sequence is enabled."},

    # ── Cross-border ────────────────────────────────────────────
    {"category": "cross_border", "key": "cross_border_decline_penalty", "label": "Cross-border decline penalty",
     "value_low": 2.0, "value_high": 5.0, "value_default": 3.2,
     "unit": "percent_points", "vertical": "all",
     "notes": "Auth rate drag on cross-border volume routed through a non-local acquirer."},

    # ── Chargebacks ─────────────────────────────────────────────
    {"category": "chargeback", "key": "chargeback_rate_retail", "label": "Retail chargeback rate",
     "value_low": 0.30, "value_high": 0.80, "value_default": 0.50,
     "unit": "percent", "vertical": "retail",
     "notes": "Healthy CNP retail chargeback ratio. Above 1.0% triggers scheme programs."},
    {"category": "chargeback", "key": "chargeback_admin_cost", "label": "Chargeback admin cost",
     "value_low": 1.50, "value_high": 3.50, "value_default": 2.20,
     "unit": "ratio", "vertical": "all",
     "notes": "GBP of admin/operational cost per GBP of chargeback value."},

    # ── FX ──────────────────────────────────────────────────────
    {"category": "fx", "key": "fx_spread_benchmark", "label": "FX spread benchmark",
     "value_low": 1.2, "value_high": 2.5, "value_default": 1.8,
     "unit": "percent", "vertical": "all",
     "notes": "Typical FX spread negotiated by mid-market merchants. Above 2.5% indicates leakage."},

    # ── Pricing / fees ──────────────────────────────────────────
    {"category": "pricing", "key": "mdr_blended_benchmark", "label": "Blended MDR benchmark",
     "value_low": 1.40, "value_high": 2.80, "value_default": 2.10,
     "unit": "percent", "vertical": "all",
     "notes": "Blended merchant discount rate for mid-market online merchants."},

    # ── Refunds ─────────────────────────────────────────────────
    {"category": "refund", "key": "refund_rate_retail", "label": "Retail refund rate",
     "value_low": 4.0, "value_high": 12.0, "value_default": 7.0,
     "unit": "percent", "vertical": "retail",
     "notes": "Retail refund rate; outliers above 15% suggest product or fulfilment issues."},
]


async def seed_default_benchmarks(db: AsyncSession) -> int:
    """Insert benchmark rows that don't already exist by (category, key, vertical)."""
    inserted = 0
    for row in DEFAULT_BENCHMARKS:
        existing = await db.execute(
            select(BenchmarkConfig.id).where(
                BenchmarkConfig.category == row["category"],
                BenchmarkConfig.key == row["key"],
                BenchmarkConfig.vertical == row["vertical"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(BenchmarkConfig(**row))
        inserted += 1
    if inserted:
        await db.commit()
        logger.info("Seeded %d default benchmarks", inserted)
    return inserted


async def seed_all(db: AsyncSession) -> dict:
    """Top-level entrypoint. Add other defaults here as the system grows."""
    benchmark_count = await seed_default_benchmarks(db)
    return {"benchmarks_inserted": benchmark_count}
