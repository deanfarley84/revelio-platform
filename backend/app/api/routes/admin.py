"""admin.py — Admin-only routes for operator dashboard"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from app.core.database import get_db
from app.core.auth import require_admin, require_operator
from app.models.user import (
    Diagnostic, Organisation, User, ClientIntel, ClientIntelLog,
    Job, AuditLog, Notification
)

router = APIRouter()


@router.get("/overview")
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_operator),
):
    """Master dashboard stats."""
    org_count = (await db.execute(select(func.count(Organisation.id)).where(Organisation.is_active == True))).scalar()
    pending = (await db.execute(select(func.count(Diagnostic.id)).where(Diagnostic.status == "pending_review"))).scalar()
    processing = (await db.execute(select(func.count(Diagnostic.id)).where(Diagnostic.status.in_(["submitted", "validating", "processing", "ai_complete"])))).scalar()
    released = (await db.execute(select(func.count(Diagnostic.id)).where(Diagnostic.status == "released"))).scalar()

    # Total leakage across all released diagnostics. Aggregated in Python
    # because final_output.annual_leakage_estimate.mid is a JSONB-nested float
    # and the SQL cast was previously broken; volume is small enough that this
    # is fine until we have thousands of released diagnostics.
    released_result = await db.execute(
        select(Diagnostic.final_output).where(Diagnostic.status == "released")
    )
    total_leakage = 0.0
    for (final_output,) in released_result.all():
        if not final_output:
            continue
        mid = (final_output.get("annual_leakage_estimate") or {}).get("mid")
        if mid is not None:
            try:
                total_leakage += float(mid)
            except (TypeError, ValueError):
                pass

    # Low confidence flags
    low_conf = (await db.execute(
        select(func.count(Diagnostic.id)).where(
            Diagnostic.status == "pending_review",
            Diagnostic.ai_output.op("->>")("confidence_level") == "low"
        )
    )).scalar()

    # Recent pipeline
    pipeline_result = await db.execute(
        select(Diagnostic).order_by(desc(Diagnostic.updated_at)).limit(10)
    )
    pipeline = pipeline_result.scalars().all()

    # Top leakage opportunities
    top_result = await db.execute(
        select(Diagnostic, Organisation.name.label("org_name"))
        .join(Organisation, Diagnostic.org_id == Organisation.id)
        .where(Diagnostic.final_output.isnot(None))
        .order_by(desc(Diagnostic.updated_at))
        .limit(10)
    )
    top = top_result.all()

    return {
        "stats": {
            "active_clients": org_count,
            "pending_approval": pending,
            "processing": processing,
            "released": released,
            "low_confidence_flags": low_conf or 0,
            "total_leakage_identified": total_leakage,
        },
        "pipeline": [_fmt_diag(d) for d in pipeline],
        "top_opportunities": [
            {**_fmt_diag(d), "org_name": name}
            for d, name in top
        ],
    }


@router.get("/queue")
async def approval_queue(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_operator),
):
    """All diagnostics pending review."""
    result = await db.execute(
        select(Diagnostic, Organisation.name.label("org_name"))
        .join(Organisation, Diagnostic.org_id == Organisation.id)
        .where(Diagnostic.status == "pending_review")
        .order_by(Diagnostic.submitted_at.asc())
    )
    rows = result.all()
    return [
        {
            **_fmt_diag(d),
            "org_name": name,
            "ai_output": d.ai_output,
            "operator_notes": d.operator_notes,
            "override_enabled": d.override_enabled,
        }
        for d, name in rows
    ]


@router.get("/clients")
async def list_all_clients(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_operator),
):
    query = select(Organisation).where(Organisation.is_active == True)
    if tier:
        query = query.where(Organisation.tier == tier)
    result = await db.execute(query.order_by(Organisation.created_at.desc()))
    orgs = result.scalars().all()

    output = []
    for org in orgs:
        # Latest diagnostic
        latest_result = await db.execute(
            select(Diagnostic)
            .where(Diagnostic.org_id == org.id)
            .order_by(desc(Diagnostic.created_at))
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        # Intel
        intel_result = await db.execute(select(ClientIntel).where(ClientIntel.org_id == org.id))
        intel = intel_result.scalar_one_or_none()

        output.append({
            "id": str(org.id),
            "name": org.name,
            "website": org.website,
            "vertical": org.vertical,
            "tier": org.tier,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "latest_diagnostic": _fmt_diag(latest) if latest else None,
            "intel": _fmt_intel(intel) if intel else None,
        })

    return output


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_operator),
):
    query = select(Job)
    if status:
        query = query.where(Job.status == status)
    query = query.order_by(desc(Job.queued_at)).limit(50)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "diagnostic_id": str(j.diagnostic_id) if j.diagnostic_id else None,
            "job_type": j.job_type,
            "status": j.status,
            "retry_count": j.retry_count,
            "error_message": j.error_message,
            "queued_at": j.queued_at.isoformat() if j.queued_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@router.get("/audit-log")
async def audit_log(
    entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    query = query.order_by(desc(AuditLog.created_at)).limit(100)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "user_id": str(l.user_id) if l.user_id else None,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": str(l.entity_id) if l.entity_id else None,
            "old_value": l.old_value,
            "new_value": l.new_value,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


def _fmt_diag(d: Diagnostic) -> dict:
    if not d:
        return {}
    ai = d.ai_output or {}
    final = d.final_output or ai
    return {
        "id": str(d.id),
        "reference": d.reference,
        "org_id": str(d.org_id),
        "tier": d.tier,
        "status": d.status,
        "company_name": d.company_name,
        "vertical": d.vertical,
        "monthly_volume": float(d.monthly_volume) if d.monthly_volume else None,
        "confidence_level": ai.get("confidence_level"),
        "leakage_mid": final.get("annual_leakage_estimate", {}).get("mid") if final else None,
        "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


def _fmt_intel(i: ClientIntel) -> dict:
    return {
        "score": i.score,
        "opportunity_stage": i.opportunity_stage,
        "tags": i.tags,
        "follow_up_date": i.follow_up_date,
        "contract_renewal": i.contract_renewal,
        "total_leakage_identified": float(i.total_leakage_identified) if i.total_leakage_identified else None,
    }
