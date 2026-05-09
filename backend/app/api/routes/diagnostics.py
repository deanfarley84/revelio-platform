"""
Diagnostics API Routes
CRUD + submission + approval workflow
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin, require_operator
from app.models.user import Diagnostic, User, Organisation, AuditLog, Notification
from app.services.inline_jobs import run_diagnostic_analysis_inline, send_notification_inline
from app.services.ai_service import classify_confidence

router = APIRouter()


def generate_reference(year: int, count: int) -> str:
    return f"RVL-{year}-{str(count).zfill(4)}"


@router.post("/", status_code=201)
async def create_diagnostic(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new diagnostic (draft)."""
    # Count existing to generate reference
    count_result = await db.execute(select(func.count(Diagnostic.id)))
    count = count_result.scalar() + 1
    year = datetime.now().year
    reference = generate_reference(year, count)

    diag = Diagnostic(
        reference=reference,
        org_id=current_user.org_id,
        submitted_by=current_user.id,
        tier=payload.get("tier", "core"),
        status="draft",
        company_name=payload.get("company_name", ""),
        website=payload.get("website"),
        vertical=payload.get("vertical", ""),
        monthly_volume=payload.get("monthly_volume"),
        monthly_transactions=payload.get("monthly_transactions"),
        avg_order_value=payload.get("avg_order_value"),
        cross_border_pct=payload.get("cross_border_pct"),
        psps_used=payload.get("psps_used", []),
        regions=payload.get("regions"),
        auth_rate=payload.get("auth_rate"),
        decline_rate=payload.get("decline_rate"),
        soft_decline_pct=payload.get("soft_decline_pct"),
        hard_decline_pct=payload.get("hard_decline_pct"),
        top_decline_reasons=payload.get("top_decline_reasons", []),
        chargeback_rate=payload.get("chargeback_rate"),
        refund_rate=payload.get("refund_rate"),
        payment_methods=payload.get("payment_methods", []),
        retry_enabled=payload.get("retry_enabled"),
        retry_notes=payload.get("retry_notes"),
        checkout_currencies=payload.get("checkout_currencies", []),
        settlement_currencies=payload.get("settlement_currencies", []),
        pricing_model=payload.get("pricing_model"),
        mdr=payload.get("mdr"),
        fx_fee_spread=payload.get("fx_fee_spread"),
        scheme_fee_visibility=payload.get("scheme_fee_visibility"),
        acquiring_setup=payload.get("acquiring_setup"),
        routing_setup=payload.get("routing_setup"),
        additional_context=payload.get("additional_context"),
    )
    db.add(diag)
    await db.commit()
    await db.refresh(diag)
    return {"id": str(diag.id), "reference": diag.reference, "status": diag.status}


@router.post("/{diagnostic_id}/submit")
async def submit_diagnostic(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit diagnostic for analysis — triggers background pipeline."""
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Diagnostic not found")
    if str(diag.org_id) != str(current_user.org_id) and current_user.role not in ("super_admin", "operator_admin"):
        raise HTTPException(403, "Access denied")
    if diag.status not in ("draft", "revision_requested"):
        raise HTTPException(400, f"Cannot submit diagnostic in status: {diag.status}")

    # Validate minimum inputs
    if not diag.monthly_volume or not diag.vertical:
        raise HTTPException(400, "Monthly volume and vertical are required")

    diag.status = "submitted"
    diag.submitted_at = datetime.now(timezone.utc)

    # Pre-check confidence
    confidence = classify_confidence(diag)

    await db.commit()

    # Notify client (inline)
    await send_notification_inline(
        db,
        notification_type="submission_received",
        context={"org_id": str(diag.org_id), "reference": diag.reference},
    )

    # Flag admin if low confidence (inline)
    if confidence == "low":
        await send_notification_inline(
            db,
            notification_type="low_confidence",
            context={"diagnostic_id": str(diag.id), "reference": diag.reference, "company": diag.company_name},
        )

    # Run AI analysis inline (workers disabled on free tier — blocks the request 10–30s)
    await run_diagnostic_analysis_inline(db, str(diag.id))

    return {"status": "submitted", "reference": diag.reference, "confidence_pre_check": confidence}


@router.get("/")
async def list_diagnostics(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List diagnostics — scoped to org for clients, all for admin."""
    query = select(Diagnostic)
    if current_user.role in ("client_admin", "client_viewer"):
        query = query.where(Diagnostic.org_id == current_user.org_id)
        # Clients only see approved/released
        query = query.where(Diagnostic.status.in_(["approved", "released"]))
    if status:
        query = query.where(Diagnostic.status == status)
    query = query.order_by(Diagnostic.created_at.desc())
    result = await db.execute(query)
    diagnostics = result.scalars().all()
    return [_serialise_diagnostic(d, current_user) for d in diagnostics]


@router.get("/{diagnostic_id}")
async def get_diagnostic(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Not found")
    if current_user.role in ("client_admin", "client_viewer"):
        if str(diag.org_id) != str(current_user.org_id):
            raise HTTPException(403, "Access denied")
        if diag.status not in ("approved", "released"):
            raise HTTPException(404, "Report not yet available")
    return _serialise_diagnostic(diag, current_user)


@router.post("/{diagnostic_id}/approve")
async def approve_diagnostic(
    diagnostic_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Approve and release diagnostic to client."""
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Not found")
    if diag.status != "pending_review":
        raise HTTPException(400, f"Cannot approve diagnostic in status: {diag.status}")

    # Apply any operator overrides
    if payload.get("override_enabled"):
        diag.override_enabled = True
        diag.override_low = payload.get("override_low")
        diag.override_mid = payload.get("override_mid")
        diag.override_high = payload.get("override_high")
        diag.override_confidence = payload.get("override_confidence")
        diag.override_reason = payload.get("override_reason")
        diag.override_by = current_user.id
        diag.override_at = datetime.now(timezone.utc)

    if payload.get("operator_notes"):
        diag.operator_notes = payload["operator_notes"]

    # Build final output (override takes precedence over AI)
    ai_out = diag.ai_output or {}
    final = dict(ai_out)
    if diag.override_enabled:
        final["annual_leakage_estimate"] = {
            "low": float(diag.override_low or 0),
            "mid": float(diag.override_mid or 0),
            "high": float(diag.override_high or 0),
            "currency": "GBP",
        }
        if diag.override_confidence:
            final["confidence_level"] = diag.override_confidence

    diag.final_output = final
    diag.approved_by = current_user.id
    diag.approved_at = datetime.now(timezone.utc)
    diag.released_at = datetime.now(timezone.utc)
    diag.status = "released"

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        org_id=diag.org_id,
        action="diagnostic_approved",
        entity_type="diagnostic",
        entity_id=diag.id,
        new_value={"override_enabled": diag.override_enabled, "status": "released"},
    )
    db.add(audit)

    await db.commit()

    # Notify client
    await send_notification_inline(
        db,
        notification_type="report_ready",
        context={"org_id": str(diag.org_id), "reference": diag.reference},
    )

    return {"status": "released", "reference": diag.reference}


@router.post("/{diagnostic_id}/reject")
async def reject_diagnostic(
    diagnostic_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Not found")

    diag.status = "revision_requested"
    diag.rejection_reason = payload.get("reason", "")
    diag.operator_notes = payload.get("notes", "")
    await db.commit()

    await send_notification_inline(
        db,
        notification_type="data_required",
        context={"org_id": str(diag.org_id), "reference": diag.reference},
    )
    return {"status": "revision_requested"}


def _serialise_diagnostic(d: Diagnostic, user: User) -> dict:
    is_admin = user.role in ("super_admin", "operator_admin", "analyst")
    output = d.final_output or d.ai_output or {}
    return {
        "id": str(d.id),
        "reference": d.reference,
        "org_id": str(d.org_id),
        "tier": d.tier,
        "status": d.status,
        "company_name": d.company_name,
        "vertical": d.vertical,
        "monthly_volume": float(d.monthly_volume) if d.monthly_volume else None,
        "auth_rate": float(d.auth_rate) if d.auth_rate else None,
        "chargeback_rate": float(d.chargeback_rate) if d.chargeback_rate else None,
        "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        "released_at": d.released_at.isoformat() if d.released_at else None,
        "output": output,
        # Admin-only fields
        **({"operator_notes": d.operator_notes, "ai_output": d.ai_output, "override_enabled": d.override_enabled} if is_admin else {}),
    }
