"""
Background Task Definitions
All async jobs run through these Celery tasks.
"""
import asyncio
from datetime import datetime, timezone
from app.workers.celery_app import celery_app


def run_async(coro):
    """Run async code inside a Celery sync task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="file_parsing")
def parse_uploaded_file(self, file_id: str):
    """
    Parse an uploaded file and extract payment fields.
    Updates the uploaded_files record with parsed_fields.
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.user import UploadedFile, Diagnostic
        from app.services.file_parser import parse_file, merge_parsed_fields
        from app.services.storage import download_file
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
            file_rec = result.scalar_one_or_none()
            if not file_rec:
                return {"error": "File record not found"}

            # Update status to parsing
            file_rec.status = "parsing"
            await db.commit()

            try:
                # Download from S3
                file_bytes = await download_file(file_rec.storage_key)

                # Parse
                parse_result = parse_file(file_bytes, file_rec.file_type)
                parse_result["file_name"] = file_rec.file_name

                # Update record
                file_rec.parsed_fields = parse_result.get("fields", {})
                file_rec.parse_confidence = parse_result.get("confidence", 0.0)
                file_rec.parse_notes = parse_result.get("notes", "")
                file_rec.status = "parsed" if not parse_result.get("error") else "parse_failed"
                file_rec.parsed_at = datetime.now(timezone.utc)

                # Merge all file fields into diagnostic.parsed_data
                diag_result = await db.execute(
                    select(UploadedFile).where(
                        UploadedFile.diagnostic_id == file_rec.diagnostic_id,
                        UploadedFile.status == "parsed"
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
                raise self.retry(exc=e)

    return run_async(_run())


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, queue="ai_analysis")
def run_diagnostic_analysis(self, diagnostic_id: str):
    """
    Run the full AI analysis pipeline for a diagnostic.
    Flow: validate -> get benchmarks -> call Claude -> store output -> notify admin
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.user import Diagnostic, Job
        from app.services.ai_service import run_ai_analysis, classify_confidence
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            diag = await db.get(Diagnostic, diagnostic_id)
            if not diag:
                return {"error": "Diagnostic not found"}

            # Update status
            diag.status = "processing"
            await db.commit()

            try:
                # Pre-classify confidence
                pre_confidence = classify_confidence(diag)

                # Run AI analysis
                ai_output, benchmarks_used = await run_ai_analysis(diag, db)

                # Store results
                diag.ai_output = ai_output
                diag.ai_model = ai_output.get("_meta", {}).get("model", "")
                diag.ai_prompt_version = ai_output.get("_meta", {}).get("prompt_version", "")
                diag.ai_tokens_used = (
                    ai_output.get("_meta", {}).get("input_tokens", 0) +
                    ai_output.get("_meta", {}).get("output_tokens", 0)
                )
                diag.ai_run_at = datetime.now(timezone.utc)
                diag.benchmarks_snapshot = benchmarks_used
                diag.status = "ai_complete"

                await db.commit()

                # Queue notification to admin
                send_notification.delay(
                    notification_type="draft_ready",
                    context={
                        "diagnostic_id": diagnostic_id,
                        "reference": diag.reference,
                        "company": diag.company_name,
                        "confidence": ai_output.get("confidence_level", pre_confidence),
                    }
                )

                # Auto-move to pending_review
                diag.status = "pending_review"
                await db.commit()

                return {
                    "status": "complete",
                    "confidence": ai_output.get("confidence_level"),
                    "leakage_mid": ai_output.get("annual_leakage_estimate", {}).get("mid"),
                }

            except Exception as e:
                diag.status = "ai_complete"  # Keep in queue so operator can see error
                diag.operator_notes = f"AI analysis error: {str(e)}"
                await db.commit()
                raise self.retry(exc=e)

    return run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="report_generation")
def generate_report(self, diagnostic_id: str, export_type: str, user_id: str, is_internal: bool = False):
    """Generate PDF or CSV report and store in S3."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.user import Diagnostic, ReportExport
        from app.services.report_generator import generate_pdf, generate_csv
        from app.services.storage import upload_file
        import uuid

        async with AsyncSessionLocal() as db:
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

    return run_async(_run())


@celery_app.task(queue="default")
def send_notification(notification_type: str, context: dict):
    """Create in-app notifications for relevant users."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.user import Notification, User
        from sqlalchemy import select

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

        tmpl = templates.get(notification_type, {})
        if not tmpl:
            return

        async with AsyncSessionLocal() as db:
            if tmpl["target_role"] == "admin":
                result = await db.execute(
                    select(User).where(User.role.in_(["super_admin", "operator_admin"]), User.is_active == True)
                )
                users = result.scalars().all()
            else:
                org_id = context.get("org_id")
                if not org_id:
                    return
                result = await db.execute(
                    select(User).where(User.org_id == org_id, User.is_active == True)
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

    return run_async(_run())
