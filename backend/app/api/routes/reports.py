"""reports.py — Report generation and download"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import boto3

from app.core.database import get_db
from app.core.auth import get_current_user, require_operator
from app.core.config import settings
from app.models.user import Diagnostic, ReportExport, User
from app.workers.tasks import generate_report

router = APIRouter()


@router.post("/{diagnostic_id}/generate")
async def trigger_report_generation(
    diagnostic_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Diagnostic not found")

    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    is_internal = payload.get("internal", False) and is_admin
    export_type = payload.get("type", "pdf")

    if not is_admin and diag.status != "released":
        raise HTTPException(403, "Report not yet released")

    generate_report.delay(diagnostic_id, export_type, str(current_user.id), is_internal)
    return {"status": "generating", "type": export_type}


@router.get("/{diagnostic_id}/exports")
async def list_exports(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReportExport)
        .where(ReportExport.diagnostic_id == diagnostic_id)
        .order_by(desc(ReportExport.generated_at))
    )
    exports = result.scalars().all()
    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    return [
        {
            "id": str(e.id),
            "export_type": e.export_type,
            "is_internal": e.is_internal,
            "generated_at": e.generated_at.isoformat() if e.generated_at else None,
        }
        for e in exports
        if is_admin or not e.is_internal
    ]


@router.get("/{diagnostic_id}/exports/{export_id}/download")
async def download_export(
    diagnostic_id: str,
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    export = await db.get(ReportExport, export_id)
    if not export or str(export.diagnostic_id) != diagnostic_id:
        raise HTTPException(404, "Export not found")

    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    if export.is_internal and not is_admin:
        raise HTTPException(403, "Access denied")

    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        obj = s3.get_object(Bucket=settings.AWS_S3_BUCKET, Key=export.storage_key)
        content = obj["Body"].read()
        media_type = "application/pdf" if export.export_type == "pdf" else "text/csv"
        filename = f"revelio_{export.export_type}.{export.export_type}"
        return Response(content=content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(500, f"Download failed: {str(e)}")
