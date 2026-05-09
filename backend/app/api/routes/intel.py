"""intel.py — Client intelligence store routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import require_admin, require_operator
from app.models.user import ClientIntel, ClientIntelLog, Organisation

router = APIRouter()


@router.get("/")
async def list_intel(db: AsyncSession = Depends(get_db), current_user=Depends(require_operator)):
    result = await db.execute(
        select(ClientIntel, Organisation.name.label("org_name"))
        .join(Organisation, ClientIntel.org_id == Organisation.id)
        .order_by(desc(ClientIntel.updated_at))
    )
    rows = result.all()
    return [_fmt(i, name) for i, name in rows]


@router.get("/{org_id}")
async def get_intel(org_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_operator)):
    result = await db.execute(select(ClientIntel).where(ClientIntel.org_id == org_id))
    intel = result.scalar_one_or_none()
    if not intel:
        raise HTTPException(404, "No intel record for this organisation")
    log_result = await db.execute(
        select(ClientIntelLog).where(ClientIntelLog.org_id == org_id).order_by(desc(ClientIntelLog.created_at)).limit(50)
    )
    logs = log_result.scalars().all()
    return {**_fmt(intel, ""), "log": [{"id": str(l.id), "note": l.note, "type": l.note_type, "created_at": l.created_at.isoformat()} for l in logs]}


@router.put("/{org_id}")
async def upsert_intel(org_id: str, payload: dict, db: AsyncSession = Depends(get_db), current_user=Depends(require_operator)):
    result = await db.execute(select(ClientIntel).where(ClientIntel.org_id == org_id))
    intel = result.scalar_one_or_none()
    if not intel:
        intel = ClientIntel(org_id=org_id, created_by=current_user.id)
        db.add(intel)
    for field in ("opportunity_stage","score","notes","tags","key_contacts","contract_notes","contract_renewal","upsell_signals","follow_up_date"):
        if field in payload:
            setattr(intel, field, payload[field])
    intel.updated_by = current_user.id
    intel.last_activity_at = datetime.now(timezone.utc)
    if payload.get("log_note"):
        log = ClientIntelLog(org_id=org_id, note=payload["log_note"], note_type=payload.get("log_type","general"), created_by=current_user.id)
        db.add(log)
    await db.commit()
    return {"status": "saved"}


def _fmt(i: ClientIntel, org_name: str) -> dict:
    return {
        "id": str(i.id), "org_id": str(i.org_id), "org_name": org_name,
        "opportunity_stage": i.opportunity_stage, "score": i.score,
        "notes": i.notes, "tags": i.tags or [], "key_contacts": i.key_contacts,
        "contract_notes": i.contract_notes, "contract_renewal": i.contract_renewal,
        "upsell_signals": i.upsell_signals or [], "follow_up_date": i.follow_up_date,
        "total_leakage_identified": float(i.total_leakage_identified) if i.total_leakage_identified else None,
        "diagnostics_count": i.diagnostics_count, "last_activity_at": i.last_activity_at.isoformat() if i.last_activity_at else None,
    }
