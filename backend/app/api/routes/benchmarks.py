"""benchmarks.py"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import require_admin, require_operator, get_current_user
from app.models.user import BenchmarkConfig, AuditLog

router = APIRouter()


@router.get("/")
async def list_benchmarks(db: AsyncSession = Depends(get_db), current_user=Depends(require_operator)):
    result = await db.execute(select(BenchmarkConfig).order_by(BenchmarkConfig.category, BenchmarkConfig.key))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id), "category": r.category, "key": r.key, "label": r.label,
            "value_low": float(r.value_low), "value_high": float(r.value_high),
            "value_default": float(r.value_default), "unit": r.unit,
            "vertical": r.vertical, "notes": r.notes,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.patch("/{benchmark_id}")
async def update_benchmark(
    benchmark_id: str, payload: dict,
    db: AsyncSession = Depends(get_db), current_user=Depends(require_admin),
):
    bm = await db.get(BenchmarkConfig, benchmark_id)
    if not bm:
        raise HTTPException(404, "Benchmark not found")
    old = {"low": float(bm.value_low), "high": float(bm.value_high), "default": float(bm.value_default)}
    if "value_low" in payload: bm.value_low = payload["value_low"]
    if "value_high" in payload: bm.value_high = payload["value_high"]
    if "value_default" in payload: bm.value_default = payload["value_default"]
    if "notes" in payload: bm.notes = payload["notes"]
    bm.updated_by = current_user.id
    bm.updated_at = datetime.now(timezone.utc)
    audit = AuditLog(
        user_id=current_user.id, action="benchmark_updated", entity_type="benchmark",
        entity_id=bm.id, old_value=old,
        new_value={"low": float(bm.value_low), "high": float(bm.value_high), "default": float(bm.value_default)},
    )
    db.add(audit)
    await db.commit()
    return {"status": "updated", "id": benchmark_id}


@router.post("/bulk-update")
async def bulk_update_benchmarks(
    payload: dict,
    db: AsyncSession = Depends(get_db), current_user=Depends(require_admin),
):
    """Update multiple benchmarks at once from admin panel."""
    updates = payload.get("updates", [])
    for update in updates:
        bm = await db.get(BenchmarkConfig, update.get("id"))
        if bm:
            if "value_default" in update: bm.value_default = update["value_default"]
            if "value_low" in update: bm.value_low = update["value_low"]
            if "value_high" in update: bm.value_high = update["value_high"]
            bm.updated_by = current_user.id
            bm.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated", "count": len(updates)}
