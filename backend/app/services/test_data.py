"""
Demo / test-data seeding.

Builds three demo merchant organisations across the tier model with
hand-crafted financial_breakdown JSON so the operator and customer
views are populated end to end without burning Anthropic credits.
Phase 1 of TEST_MODE_BRIEF.md.

Idempotent: refuses if any non-demo client organisation exists, so
real client data cannot be clobbered. Wipes any prior demo orgs in
place and rebuilds clean. Pair with wipe_test_data() to reset.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.models.user import (
    Organisation,
    User,
    Diagnostic,
    UploadedFile,
    ClientIntel,
    ClientIntelLog,
    Job,
    AuditLog,
    Notification,
    ReportExport,
)


DEMO_PASSWORD = "Demo1234!"


# ─── Demo dataset ────────────────────────────────────────────


def _acme_ai_output() -> dict[str, Any]:
    """Mid-market UK retailer, released. Drives the ROI calculator."""
    breakdown = [
        {
            "category": "Authorisation loss",
            "estimated_loss": 480000,
            "estimated_loss_low": 380000, "estimated_loss_mid": 480000, "estimated_loss_high": 560000,
            "confidence": "medium",
            "basis": "Issuer-side declines on observed monthly volume; benchmarked against UK retail peers.",
        },
        {
            "category": "Cross-border performance",
            "estimated_loss": 180000,
            "estimated_loss_low": 130000, "estimated_loss_mid": 180000, "estimated_loss_high": 240000,
            "confidence": "medium",
            "basis": "EU and US transactions routed via UK acquirer; 18 percent cross-border share.",
        },
        {
            "category": "FX leakage",
            "estimated_loss": 220000,
            "estimated_loss_low": 175000, "estimated_loss_mid": 220000, "estimated_loss_high": 270000,
            "confidence": "high",
            "basis": "Settlement currency mismatch on EUR and USD volumes; observed FX spread above market.",
        },
        {
            "category": "Retry logic",
            "estimated_loss": 95000,
            "estimated_loss_low": 65000, "estimated_loss_mid": 95000, "estimated_loss_high": 130000,
            "confidence": "high",
            "basis": "No second-attempt logic on soft declines; opportunity from network token enrolment.",
        },
    ]
    return {
        "confidence_level": "medium",
        "executive_summary": (
            "Acme Retail is leaving roughly £975k a year on the table, almost evenly split between "
            "issuer-side authorisation declines and a cross-border / FX setup that has not kept pace "
            "with the international share of volume. The recoverable revenue is meaningful at the "
            "Core tier and most fixes are configuration changes or vendor conversations rather than "
            "a build."
        ),
        "annual_leakage_estimate": {"low": 620000, "mid": 975000, "high": 1320000},
        "revenue_impact_pct": {"low": 1.0, "mid": 1.6, "high": 2.2},
        "primary_drivers": [
            {
                "rank": 1,
                "driver": "Issuer authorisation rate trailing peers",
                "estimated_impact_low": 380000,
                "estimated_impact_high": 560000,
                "confidence": "medium",
                "basis": "EU-issued card declines above peer benchmark",
            },
            {
                "rank": 2,
                "driver": "Single-acquirer footprint on international volume",
                "estimated_impact_low": 130000,
                "estimated_impact_high": 240000,
                "confidence": "medium",
                "basis": "No failover; cross-border routed via UK only",
            },
            {
                "rank": 3,
                "driver": "FX spread above market on EUR and USD settlement",
                "estimated_impact_low": 175000,
                "estimated_impact_high": 270000,
                "confidence": "high",
                "basis": "Observed 35-45 bps over interbank mid",
            },
            {
                "rank": 4,
                "driver": "No retry strategy on soft declines",
                "estimated_impact_low": 65000,
                "estimated_impact_high": 130000,
                "confidence": "high",
                "basis": "Network tokens not enrolled, no second-attempt logic",
            },
        ],
        "financial_breakdown": breakdown,
        "recommended_fix_priorities": {
            "immediate": [
                {"action": "Enrol in network tokens with the existing acquirer.", "estimated_recovery": "£40k-£90k/yr"},
                {"action": "Enable second-attempt retry on a curated set of soft-decline reasons."},
            ],
            "mid_term": [
                {"action": "Add a secondary EU acquirer for cross-border routing, no orchestration needed."},
                {"action": "Renegotiate FX spread on EUR settlement, benchmarked at 25 bps."},
            ],
            "structural": [
                {"action": "Reassess routing once a second acquirer is in place; orchestration optional."},
            ],
        },
        "data_gaps": [
            "Auth-rate breakdown by issuing country was not provided; figures use peer benchmarks.",
        ],
    }


def _globex_ai_output() -> dict[str, Any]:
    """Enterprise travel marketplace, pending_review."""
    breakdown = [
        {
            "category": "Cross-border performance",
            "estimated_loss": 1200000,
            "estimated_loss_low": 950000, "estimated_loss_mid": 1200000, "estimated_loss_high": 1500000,
            "confidence": "high",
            "basis": "Heavy international volume on a UK-only acquiring footprint.",
        },
        {
            "category": "Routing inefficiency",
            "estimated_loss": 680000,
            "estimated_loss_low": 480000, "estimated_loss_mid": 680000, "estimated_loss_high": 880000,
            "confidence": "medium",
            "basis": "Single-PSP dependency with no failover; observed acquirer-side outages monthly.",
        },
        {
            "category": "Payment method gaps",
            "estimated_loss": 540000,
            "estimated_loss_low": 380000, "estimated_loss_mid": 540000, "estimated_loss_high": 700000,
            "confidence": "medium",
            "basis": "No iDEAL, Bancontact or Klarna in DACH and Nordics; conversion drag visible.",
        },
        {
            "category": "FX leakage",
            "estimated_loss": 310000,
            "estimated_loss_low": 240000, "estimated_loss_mid": 310000, "estimated_loss_high": 380000,
            "confidence": "high",
            "basis": "Settlement currency mismatch on EUR, SEK and CHF volumes.",
        },
        {
            "category": "Chargeback admin",
            "estimated_loss": 180000,
            "estimated_loss_low": 130000, "estimated_loss_mid": 180000, "estimated_loss_high": 230000,
            "confidence": "low",
            "basis": "Operational overhead on disputes; partial visibility into vendor cost.",
        },
    ]
    return {
        "confidence_level": "medium",
        "executive_summary": (
            "Globex is operating an enterprise travel marketplace on infrastructure that fits a UK "
            "DTC business. The big numbers are cross-border performance and routing: roughly £1.9m "
            "of the £2.91m mid case sits on those two lines and they share a root cause, the single-"
            "acquirer footprint. Worth flagging to the operator review before release."
        ),
        "annual_leakage_estimate": {"low": 2100000, "mid": 2910000, "high": 3850000},
        "revenue_impact_pct": {"low": 1.4, "mid": 1.9, "high": 2.5},
        "primary_drivers": [
            {
                "rank": 1,
                "driver": "Single UK acquirer carrying all international volume",
                "estimated_impact_low": 950000,
                "estimated_impact_high": 1500000,
                "confidence": "high",
                "basis": "Heavy cross-border volume on UK-only acquiring footprint",
            },
            {
                "rank": 2,
                "driver": "Routing inefficiency, no failover",
                "estimated_impact_low": 480000,
                "estimated_impact_high": 880000,
                "confidence": "medium",
                "basis": "Single-PSP dependency; observed monthly outages",
            },
            {
                "rank": 3,
                "driver": "Local payment method gaps in DACH and Nordics",
                "estimated_impact_low": 380000,
                "estimated_impact_high": 700000,
                "confidence": "medium",
                "basis": "No iDEAL, Bancontact, Klarna in target markets",
            },
            {
                "rank": 4,
                "driver": "FX spread on EUR, SEK, CHF settlement",
                "estimated_impact_low": 240000,
                "estimated_impact_high": 380000,
                "confidence": "high",
                "basis": "Observed mismatch between checkout and settlement currencies",
            },
        ],
        "financial_breakdown": breakdown,
        "recommended_fix_priorities": {
            "immediate": [
                {"action": "Add a second EU acquirer for cross-border failover.", "estimated_recovery": "£300k-£600k/yr"},
                {"action": "Quote local payment method coverage for DACH and Nordics."},
            ],
            "mid_term": [
                {"action": "Adopt orchestration for dynamic routing once the second acquirer is live."},
                {"action": "Renegotiate FX spread on settlement currencies, target 30 bps."},
            ],
            "structural": [
                {"action": "Bring chargeback management in-house or onto a dedicated platform."},
            ],
        },
        "data_gaps": [
            "Vendor cost on chargeback management was estimated rather than measured.",
        ],
    }


_DEMO_ORGS = [
    {
        "slug": "acme-retail",
        "name": "Acme Retail (demo)",
        "vertical": "retail",
        "tier": "core",
        "website": "https://acme-retail.demo",
        "diagnostic": {
            "reference": "RVL-DEMO-001",
            "status": "released",
            "company_name": "Acme Retail Ltd",
            "vertical": "retail",
            "monthly_volume": 5000000,
            "monthly_transactions": 120000,
            "avg_order_value": 41.67,
            "cross_border_pct": 18.0,
            "psps_used": ["Adyen"],
            "regions": {"primary": "GB", "secondary": ["EU", "US"]},
            "auth_rate": 87.4,
            "decline_rate": 12.6,
            "soft_decline_pct": 4.8,
            "hard_decline_pct": 7.8,
            "payment_methods": ["card", "apple_pay", "google_pay"],
            "retry_enabled": False,
            "checkout_currencies": ["GBP", "EUR", "USD"],
            "settlement_currencies": ["GBP"],
            "ai_output_fn": _acme_ai_output,
            "release": True,
        },
    },
    {
        "slug": "globex-travel",
        "name": "Globex Travel (demo)",
        "vertical": "travel",
        "tier": "enterprise",
        "website": "https://globex-travel.demo",
        "diagnostic": {
            "reference": "RVL-DEMO-002",
            "status": "pending_review",
            "company_name": "Globex Travel Group",
            "vertical": "travel",
            "monthly_volume": 12500000,
            "monthly_transactions": 32000,
            "avg_order_value": 390.62,
            "cross_border_pct": 64.0,
            "psps_used": ["Worldpay"],
            "regions": {"primary": "GB", "secondary": ["EU", "US", "MEA"]},
            "auth_rate": 84.1,
            "decline_rate": 15.9,
            "soft_decline_pct": 6.2,
            "hard_decline_pct": 9.7,
            "payment_methods": ["card", "apple_pay"],
            "retry_enabled": False,
            "checkout_currencies": ["GBP", "EUR", "USD", "SEK", "CHF"],
            "settlement_currencies": ["GBP"],
            "ai_output_fn": _globex_ai_output,
            "release": False,
        },
    },
    {
        "slug": "tinker-goods",
        "name": "Tinker Goods (demo)",
        "vertical": "dtc",
        "tier": "lite",
        "website": "https://tinker-goods.demo",
        "diagnostic": {
            "reference": "RVL-DEMO-003",
            "status": "draft",
            "company_name": "Tinker Goods",
            "vertical": "dtc",
            "monthly_volume": 280000,
            "monthly_transactions": 4200,
            "avg_order_value": 66.67,
            "cross_border_pct": 8.0,
            "psps_used": ["Stripe"],
            "regions": {"primary": "GB"},
            "auth_rate": None,
            "decline_rate": None,
            "soft_decline_pct": None,
            "hard_decline_pct": None,
            "payment_methods": ["card", "apple_pay", "klarna"],
            "retry_enabled": True,
            "checkout_currencies": ["GBP"],
            "settlement_currencies": ["GBP"],
            "ai_output_fn": None,
            "release": False,
        },
    },
]


# ─── Public API ──────────────────────────────────────────────


async def has_real_client_orgs(db: AsyncSession) -> bool:
    """True if any non-demo org has a client_admin or client_viewer user.
    Kept for diagnostics / future use; no longer gates seed_test_data
    because the seed only ever creates and wipes is_demo rows so cannot
    collide with real client data."""
    q = (
        select(func.count(distinct(User.org_id)))
        .join(Organisation, Organisation.id == User.org_id)
        .where(User.role.in_(("client_admin", "client_viewer")))
        .where(Organisation.is_demo.is_(False))
    )
    return ((await db.execute(q)).scalar() or 0) > 0


async def seed_test_data(db: AsyncSession, super_admin_id: str) -> dict[str, Any]:
    """
    Build three demo merchant orgs end to end. Idempotent: wipes prior
    demo data first then rebuilds. Touches only is_demo=True rows, so
    real client orgs are never affected.
    """
    # Clean re-seed: remove any existing demo orgs so the run is idempotent.
    wipe_summary = await wipe_test_data(db)

    now = datetime.now(timezone.utc)
    created = {"orgs": [], "users": [], "diagnostics": [], "report_exports": 0}

    pwd_hash = hash_password(DEMO_PASSWORD)

    for spec in _DEMO_ORGS:
        org = Organisation(
            name=spec["name"],
            website=spec["website"],
            vertical=spec["vertical"],
            tier=spec["tier"],
            is_active=True,
            is_demo=True,
        )
        db.add(org)
        await db.flush()
        created["orgs"].append({"id": str(org.id), "name": org.name, "tier": org.tier})

        admin = User(
            org_id=org.id,
            email=f"admin@{spec['slug']}.demo",
            full_name=f"{spec['name'].replace(' (demo)', '')} Admin",
            role="client_admin",
            password_hash=pwd_hash,
            is_active=True,
        )
        viewer = User(
            org_id=org.id,
            email=f"viewer@{spec['slug']}.demo",
            full_name=f"{spec['name'].replace(' (demo)', '')} Viewer",
            role="client_viewer",
            password_hash=pwd_hash,
            is_active=True,
        )
        db.add_all([admin, viewer])
        await db.flush()
        created["users"].extend([
            {"email": admin.email, "role": admin.role},
            {"email": viewer.email, "role": viewer.role},
        ])

        d_spec = spec["diagnostic"]
        ai_out = d_spec["ai_output_fn"]() if d_spec["ai_output_fn"] else None

        diag = Diagnostic(
            reference=d_spec["reference"],
            org_id=org.id,
            submitted_by=admin.id,
            tier=spec["tier"],
            status=d_spec["status"],
            is_demo=True,
            company_name=d_spec["company_name"],
            website=spec["website"],
            vertical=d_spec["vertical"],
            monthly_volume=d_spec["monthly_volume"],
            monthly_transactions=d_spec["monthly_transactions"],
            avg_order_value=d_spec["avg_order_value"],
            cross_border_pct=d_spec["cross_border_pct"],
            psps_used=d_spec["psps_used"],
            regions=d_spec["regions"],
            auth_rate=d_spec["auth_rate"],
            decline_rate=d_spec["decline_rate"],
            soft_decline_pct=d_spec["soft_decline_pct"],
            hard_decline_pct=d_spec["hard_decline_pct"],
            payment_methods=d_spec["payment_methods"],
            retry_enabled=d_spec["retry_enabled"],
            checkout_currencies=d_spec["checkout_currencies"],
            settlement_currencies=d_spec["settlement_currencies"],
            ai_output=ai_out,
            ai_model="seed-fixture",
            ai_prompt_version="seed-v1",
            ai_run_at=now - timedelta(days=2) if ai_out else None,
            submitted_at=now - timedelta(days=3) if d_spec["status"] != "draft" else None,
        )
        if d_spec["status"] == "released":
            diag.final_output = ai_out
            diag.approved_by = super_admin_id
            diag.approved_at = now - timedelta(days=1)
            diag.released_at = now - timedelta(hours=20)
        db.add(diag)
        await db.flush()
        created["diagnostics"].append({
            "id": str(diag.id),
            "reference": diag.reference,
            "status": diag.status,
            "org": org.name,
        })

        # Pre-generate the PDF for the released diagnostic so the client
        # download flow works end to end without a re-render.
        if d_spec["release"]:
            try:
                from app.services.inline_jobs import generate_report_inline
                gen = await generate_report_inline(
                    db, str(diag.id), "pdf", super_admin_id, is_internal=False
                )
                if gen.get("storage_key"):
                    created["report_exports"] += 1
            except Exception as e:  # noqa: BLE001 - best effort, don't fail the whole seed
                created.setdefault("warnings", []).append(
                    f"PDF pre-generation failed for {diag.reference}: {e}"
                )

    await db.commit()
    return {
        "status": "seeded",
        "wiped_first": wipe_summary.get("removed_orgs", 0) > 0,
        "credentials": {
            "password": DEMO_PASSWORD,
            "users": [u["email"] for u in created["users"]],
        },
        "created": created,
    }


async def wipe_test_data(db: AsyncSession) -> dict[str, Any]:
    """Delete every is_demo=True org and the rows that hang off them.

    Order matters: dependents first so we don't trip foreign-key constraints
    that lack ON DELETE CASCADE.
    """
    demo_orgs = (await db.execute(
        select(Organisation).where(Organisation.is_demo.is_(True))
    )).scalars().all()
    if not demo_orgs:
        return {"removed_orgs": 0}

    org_ids = [o.id for o in demo_orgs]
    user_ids = list((await db.execute(
        select(User.id).where(User.org_id.in_(org_ids))
    )).scalars().all())
    diag_ids = list((await db.execute(
        select(Diagnostic.id).where(Diagnostic.org_id.in_(org_ids))
    )).scalars().all())

    # Notifications hang off user_id only (no org_id column).
    if user_ids:
        await db.execute(
            Notification.__table__.delete().where(Notification.user_id.in_(user_ids))
        )
    # Audit log can reference user or org.
    await db.execute(
        AuditLog.__table__.delete().where(AuditLog.org_id.in_(org_ids))
    )
    if user_ids:
        await db.execute(
            AuditLog.__table__.delete().where(AuditLog.user_id.in_(user_ids))
        )

    if diag_ids:
        await db.execute(
            ReportExport.__table__.delete().where(ReportExport.diagnostic_id.in_(diag_ids))
        )
        await db.execute(
            Job.__table__.delete().where(Job.diagnostic_id.in_(diag_ids))
        )
        # UploadedFile has ON DELETE CASCADE on diagnostic_id but be explicit
        # in case the cascade is not active for any reason.
        await db.execute(
            UploadedFile.__table__.delete().where(UploadedFile.diagnostic_id.in_(diag_ids))
        )
        await db.execute(
            Diagnostic.__table__.delete().where(Diagnostic.id.in_(diag_ids))
        )

    await db.execute(
        ClientIntelLog.__table__.delete().where(ClientIntelLog.org_id.in_(org_ids))
    )
    await db.execute(
        ClientIntel.__table__.delete().where(ClientIntel.org_id.in_(org_ids))
    )
    await db.execute(
        User.__table__.delete().where(User.org_id.in_(org_ids))
    )
    await db.execute(
        Organisation.__table__.delete().where(Organisation.id.in_(org_ids))
    )
    await db.commit()
    return {
        "removed_orgs": len(org_ids),
        "removed_diagnostics": len(diag_ids),
        "removed_users": len(user_ids),
    }
