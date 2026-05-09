"""files.py — File upload and management routes"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid, boto3
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import settings
from app.models.user import UploadedFile, Diagnostic, User
from app.workers.tasks import parse_uploaded_file

router = APIRouter()

ALLOWED_TYPES = {
    "text/csv": "csv",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/pdf": "pdf",
    "text/plain": "txt",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def get_s3():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


@router.post("/{diagnostic_id}/upload")
async def upload_file(
    diagnostic_id: str,
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Diagnostic not found")
    if str(diag.org_id) != str(current_user.org_id) and current_user.role not in ("super_admin", "operator_admin"):
        raise HTTPException(403, "Access denied")

    # Validate type
    file_type = ALLOWED_TYPES.get(file.content_type)
    if not file_type:
        # Fallback: check extension
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext in ("csv", "xlsx", "xls", "pdf", "txt"):
            file_type = ext
        else:
            raise HTTPException(400, f"File type not supported: {file.content_type}")

    # Read bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File exceeds 20MB limit")

    # Upload to S3
    storage_key = f"uploads/{diag.org_id}/{diagnostic_id}/{uuid.uuid4()}/{file.filename}"
    try:
        s3 = get_s3()
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=storage_key,
            Body=file_bytes,
            ContentType=file.content_type or "application/octet-stream",
            ServerSideEncryption="AES256",
        )
    except Exception as e:
        if settings.ENVIRONMENT == "development":
            # In dev, skip S3 and store locally if needed
            storage_key = f"local/{storage_key}"
        else:
            raise HTTPException(500, f"Upload failed: {str(e)}")

    # Create DB record
    file_rec = UploadedFile(
        diagnostic_id=diagnostic_id,
        org_id=diag.org_id,
        file_name=file.filename,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        storage_key=storage_key,
        status="uploaded",
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(file_rec)
    await db.commit()
    await db.refresh(file_rec)

    # Queue parsing job
    parse_uploaded_file.delay(str(file_rec.id))

    return {
        "id": str(file_rec.id),
        "file_name": file_rec.file_name,
        "file_type": file_rec.file_type,
        "size_bytes": file_rec.file_size_bytes,
        "status": "parsing",
    }


@router.get("/{diagnostic_id}/files")
async def list_files(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Diagnostic not found")

    result = await db.execute(
        select(UploadedFile).where(UploadedFile.diagnostic_id == diagnostic_id)
    )
    files = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "file_name": f.file_name,
            "file_type": f.file_type,
            "size_bytes": f.file_size_bytes,
            "status": f.status,
            "parse_confidence": float(f.parse_confidence) if f.parse_confidence else None,
            "parsed_fields": f.parsed_fields,
            "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
        }
        for f in files
    ]


@router.get("/{diagnostic_id}/files/{file_id}/parsed-data")
async def get_parsed_data(
    diagnostic_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_rec = await db.get(UploadedFile, file_id)
    if not file_rec or str(file_rec.diagnostic_id) != diagnostic_id:
        raise HTTPException(404, "File not found")
    return {"parsed_fields": file_rec.parsed_fields, "confidence": float(file_rec.parse_confidence or 0)}
