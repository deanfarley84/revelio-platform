"""
Inline job functions.

Why this module exists:
  Render's free tier doesn't support background workers, so for early-stage
  deployments we run jobs synchronously inside API requests. These functions
  are the same logic that Celery tasks would run — just callable directly
  from a route handler.

  When upgrading to a paid plan with Celery enabled, the Celery tasks in
  app/workers/tasks.py simply wrap calls to the functions defined here, so
  no business logic changes — only the call site.

Trade-off:
  POST /diagnostics/{id}/submit will block for 10–30s while Claude runs.
  Acceptable for early demo traffic. Replace with .delay() when workers are
  available again.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ─── File parsing ─────────────────────────────────────────────
async def parse_uploaded_file_inline(db: AsyncSession, file_id: str) -> dict:
    """Parse an uploaded file, update DB, merge into diagnostic.parsed_data."""
    from app.models.user import UploadedFile, Diagnostic
    from app.services.file_parser import parse_file, merge_parsed_fields
    from app.services.storage import download_file

    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
    file_rec = result.scalar_one_or_none()
    if not file_rec:
        return {"error": "File record not found"}

    file_rec.status = "parsing"
    await db.commit()

    try:
        file_bytes = await download_file(file_rec.storage_key)
        parse_result = parse_file(file_bytes, file_rec.file_type)
        parse_result["file_name"] = file_rec.file_name

        file_rec.parsed_fields = parse_result.get("fields", {})
        file_rec.parse_confidence = parse_result.get("confidence", 0.0)
        file_rec.parse_notes = parse_result.get("notes", "")
        file_rec.status = "parsed" if not parse_result.get("error") else "parse_failed"
        file_rec.parsed_at = datetime.now(timezone.utc)

        diag_result = await db.execute(
            select(UploadedFile).where(
                UploadedFile.diagnostic_id == file_rec.diagnostic_id,
                UploadedFile.status == "parsed",
            )
        )
        all_parsed = [{"fields": f.parsed_fields or {}, "file_name": f.file_name}
                      for f in diag_result.scalars().all()]
        all_parsed.append(parse_result)
        merged = merge_parsed_fields(all_parsed)

        diag = await db.get(Diagnostic, file_rec.diagnostic_id)
        if diag:
            diag.parsed_data = merged

        await db.commit()
        return {"status": "parsed", "fields_found": len(file_rec.parsed_fields or {})}

    except Exception as e:
        file_rec.status = "parse_failed"
        file_rec.parse_notes = str(e)
        await db.commit()
        return {"error": str(e)}


# ─── AI analysis ──────────────────────────────────────────────
async def run_diagnostic_analysis_inline(db: AsyncSession, diagnostic_id: str) -> dict:
    """Run AI analysis pipeline and move diagnostic into pending_review."""
    from app.models.user import Diagnostic
    from app.services.ai_service import run_ai_analysis, classify_confidence

    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        return {"error": "Diagnostic not found"}

    diag.status = "processing"
    await db.commit()

    try:
        pre_confidence = classify_confidence(diag)
        ai_output, benchmarks_used = await run_ai_analysis(diag, db)

        diag.ai_output = ai_output
        diag.ai_model = ai_output.get("_meta", {}).get("model", "")
        diag.ai_prompt_version = ai_output.get("_meta", {}).get("prompt_version", "")
        diag.ai_tokens_used = (
            ai_output.get("_meta", {}).get("input_tokens", 0)
            + ai_output.get("_meta", {}).get("output_tokens", 0)
        )
        diag.ai_run_at = datetime.now(timezone.utc)
        diag.benchmarks_snapshot = benchmarks_used
        diag.status = "ai_complete"
        await db.commit()

        await send_notification_inline(
            db,
            notification_type="draft_ready",
            context={
                "diagnostic_id": diagnostic_id,
                "reference": diag.reference,
                "company": diag.company_name,
                "confidence": ai_output.get("confidence_level", pre_confidence),
            },
        )

        diag.status = "pending_review"
        await db.commit()

        return {
            "status": "complete",
            "confidence": ai_output.get("confidence_level"),
            "leakage_mid": ai_output.get("annual_leakage_estimate", {}).get("mid"),
        }

    except Exception as e:
        diag.status = "ai_complete"
        diag.operator_notes = f"AI analysis error: {str(e)}"
        await db.commit()
        return {"error": str(e)}


# ─── Report generation ────────────────────────────────────────
async def generate_report_inline(
    db: AsyncSession,
    diagnostic_id: str,
    export_type: str,
    user_id: str,
    is_internal: bool = False,
) -> dict:
    """Generate PDF or CSV report and store in S3 (or local fallback)."""
    from app.models.user import Diagnostic, ReportExport
    from app.services.report_generator import generate_pdf, generate_csv
    from app.services.storage import upload_file

    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        return {"error": "Diagnostic not found"}

    output = diag.final_output or diag.ai_output

    if export_type == "pdf":
        file_bytes, mime = await generate_pdf(diag, output, is_internal)
        ext = "pdf"
    elif export_type == "csv":
        file_bytes, mime = await generate_csv(diag, output)
        ext = "csv"
    else:
        return {"error": f"Unknown export type: {export_type}"}

    storage_key = f"reports/{diag.org_id}/{diagnostic_id}/{export_type}{'_internal' if is_internal else ''}.{ext}"
    await upload_file(storage_key, file_bytes, mime)

    export = ReportExport(
        diagnostic_id=diagnostic_id,
        org_id=diag.org_id,
        export_type=export_type,
        storage_key=storage_key,
        generated_by=user_id,
        is_internal=is_internal,
    )
    db.add(export)
    await db.commit()

    return {"status": "generated", "storage_key": storage_key}


# ─── Notifications ────────────────────────────────────────────
async def send_notification_inline(
    db: AsyncSession,
    notification_type: str,
    context: dict,
) -> None:
    """Create in-app notifications for the relevant users."""
    from app.models.user import Notification, User

    templates = {
        "submission_received": {
            "title": "Diagnostic submitted",
            "body": "Your diagnostic has been received and is being processed.",
            "target_role": "client",
        },
        "report_ready": {
            "title": "Your report is ready",
            "body": "Your diagnostic report has been approved and is ready to view.",
            "target_role": "client",
        },
        "data_required": {
            "title": "Additional data required",
            "body": "Your operator has requested additional information for your diagnostic.",
            "target_role": "client",
        },
        "draft_ready": {
            "title": f"Draft ready: {context.get('reference', '')}",
            "body": f"{context.get('company', '')} diagnostic complete. Confidence: {context.get('confidence', 'unknown')}.",
            "target_role": "admin",
        },
        "low_confidence": {
            "title": f"Low confidence: {context.get('reference', '')}",
            "body": f"{context.get('company', '')} has insufficient data for reliable analysis.",
            "target_role": "admin",
        },
    }

    tmpl = templates.get(notification_type)
    if not tmpl:
        return

    if tmpl["target_role"] == "admin":
        result = await db.execute(
            select(User).where(
                User.role.in_(["super_admin", "operator_admin"]),
                User.is_active == True,  # noqa: E712
            )
        )
        users = result.scalars().all()
    else:
        org_id = context.get("org_id")
        if not org_id:
            return
        result = await db.execute(
            select(User).where(User.org_id == org_id, User.is_active == True)  # noqa: E712
        )
        users = result.scalars().all()

    for user in users:
        notif = Notification(
            user_id=user.id,
            type=notification_type,
            title=tmpl["title"],
            body=tmpl["body"],
            extra_metadata=context,
        )
        db.add(notif)

    await db.commit()
