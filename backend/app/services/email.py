"""
Email transport.

Env-driven SMTP wrapper. When SMTP_HOST is unset (e.g. before a
provider is wired up) `send_email` no-ops gracefully and logs the
attempted send so callers do not crash. Once a real provider is
configured the same call becomes a real outbound email with no code
changes.

Deliberately uses Python's stdlib smtplib to avoid pulling in a heavier
provider SDK before we have picked one. Move to SendGrid / Postmark /
AWS SES later if we need higher throughput, templating, or reputation
management; the public surface (`send_email`, `is_email_enabled`) does
not need to change.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional

from app.core.config import settings

logger = logging.getLogger("vyre.email")


def is_email_enabled() -> bool:
    """True when an SMTP host is configured. Callers can use this to
    decide whether to surface an "email sent" message vs an
    "email transport not configured, here is the raw link" message."""
    return bool(settings.SMTP_HOST)


def _build_message(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    cc: Optional[Iterable[str]] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    return msg


def _send_blocking(msg: EmailMessage) -> None:
    """Synchronous SMTP send. Run via asyncio.to_thread from async callers."""
    if settings.SMTP_USE_TLS:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            if settings.SMTP_USERNAME:
                s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.ehlo()
            if settings.SMTP_USERNAME:
                s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)


async def send_email(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    cc: Optional[Iterable[str]] = None,
) -> dict:
    """Send an email. No-ops when SMTP_HOST is unset.

    Returns a dict {"sent": bool, "reason": str | None} so callers can
    surface a sensible message to the user without raising.
    """
    if not is_email_enabled():
        logger.info(
            "email_skip to=%s subject=%r reason=transport_not_configured",
            to, subject,
        )
        return {"sent": False, "reason": "transport_not_configured"}

    try:
        msg = _build_message(
            to=to, subject=subject, body_text=body_text, body_html=body_html, cc=cc
        )
        await asyncio.to_thread(_send_blocking, msg)
        logger.info("email_sent to=%s subject=%r", to, subject)
        return {"sent": True, "reason": None}
    except Exception as e:  # noqa: BLE001 - we never want to fail a request
        logger.warning("email_failed to=%s subject=%r err=%s", to, subject, e)
        return {"sent": False, "reason": f"send_failed: {e}"}
