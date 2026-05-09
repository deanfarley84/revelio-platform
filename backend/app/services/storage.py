"""
Storage Service
Supports both AWS S3 (production) and local filesystem (demo mode).
Set USE_LOCAL_STORAGE=true to bypass S3 entirely.
"""
import os
from pathlib import Path
from app.core.config import settings


def _use_local() -> bool:
    return os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"


def _local_path(key: str) -> Path:
    base = Path(os.getenv("LOCAL_STORAGE_PATH", "/tmp/revelio_files"))
    full = base / key.lstrip("/")
    full.parent.mkdir(parents=True, exist_ok=True)
    return full


async def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    if _use_local():
        _local_path(key).write_bytes(data)
        return key
    import boto3
    boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    ).put_object(
        Bucket=settings.AWS_S3_BUCKET, Key=key, Body=data,
        ContentType=content_type, ServerSideEncryption="AES256",
    )
    return key


async def download_file(key: str) -> bytes:
    if _use_local():
        p = _local_path(key)
        return p.read_bytes() if p.exists() else b""
    import boto3
    obj = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    ).get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
    return obj["Body"].read()


def get_presigned_url(key: str, expires: int = 3600) -> str:
    if _use_local():
        return f"/api/v1/demo/files/{key}"
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    ).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
