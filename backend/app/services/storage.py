"""
Storage Service
Supports both AWS S3 (production) and local filesystem (demo / free tier).

Mode selection (in order of precedence):
  1. USE_LOCAL_STORAGE=true env var forces local
  2. AWS_ACCESS_KEY_ID empty -> local (auto-fallback for free tier deploys)
  3. Otherwise -> S3
"""
import os
from pathlib import Path
from app.core.config import settings


def use_local() -> bool:
    if os.getenv("USE_LOCAL_STORAGE", "").lower() == "true":
        return True
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return True
    return False


def _local_path(key: str) -> Path:
    base = Path(os.getenv("LOCAL_STORAGE_PATH", "/tmp/vyre_files"))
    full = base / key.lstrip("/")
    full.parent.mkdir(parents=True, exist_ok=True)
    return full


async def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    if use_local():
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
    if use_local():
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
    if use_local():
        return f"/api/v1/files/local/{key}"
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
