"""invitations.py — invite team members into a client org.

Designed to work with or without an email transport configured.

When SMTP_HOST is set the create endpoint sends the invitation by
email. Either way the response carries a copyable accept_url so the
inviter can paste it into Slack / iMessage / WhatsApp manually.

Lifecycle:
  POST   /invitations            create (requires client_admin or higher)
  GET    /invitations            list pending for the caller's org
  GET    /invitations/{token}    public, read invitation summary
  POST   /invitations/{token}/accept   public-with-payload, sets password
  DELETE /invitations/{id}       revoke (requires client_admin or higher)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, hash_password
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import Invitation, Organisation, User
from app.services.email import is_email_enabled, send_email

router = APIRouter()


_INVITE_TTL_DAYS = 14
_VALID_ROLES = {"client_admin", "client_viewer"}


def _is_org_admin(user: User) -> bool:
    """Roles that may invite into an org."""
    return user.role in ("super_admin", "operator_admin", "analyst", "client_admin")


def _accept_url(token: str) -> str:
    base = (settings.PUBLIC_APP_URL or "").rstrip("/")
    return f"{base}/invite/{token}"


def _serialise(inv: Invitation) -> dict:
    return {
        "id": str(inv.id),
        "org_id": str(inv.org_id),
        "email": inv.email,
        "role": inv.role,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@router.post("", status_code=201)
@limiter.limit("30/hour")
async def create_invitation(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an invitation for the caller's org. Returns the accept_url
    for manual sharing and, if email is configured, also sends it."""
    if not _is_org_admin(current_user):
        raise HTTPException(403, "Only org admins can invite team members")

    email = (payload.get("email") or "").strip().lower()
    role = (payload.get("role") or "client_viewer").strip()
    if not email:
        raise HTTPException(400, "email is required")
    if role not in _VALID_ROLES:
        raise HTTPException(400, f"role must be one of {sorted(_VALID_ROLES)}")

    # Operator-tier roles can target a different org; clients only their own.
    target_org_id = current_user.org_id
    if current_user.role in ("super_admin", "operator_admin", "analyst") and payload.get("org_id"):
        target_org_id = payload["org_id"]
    if not target_org_id:
        raise HTTPException(400, "Inviter has no org and no org_id was supplied")

    org = await db.get(Organisation, target_org_id)
    if not org:
        raise HTTPException(404, "Target organisation not found")

    # Block invites for an email that already has a user in this org.
    existing = await db.execute(
        select(User).where(User.email == email, User.org_id == target_org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "A user with that email already exists in this org")

    token = secrets.token_urlsafe(32)
    inv = Invitation(
        org_id=target_org_id,
        email=email,
        role=role,
        token=token,
        invited_by=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_INVITE_TTL_DAYS),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    accept_url = _accept_url(token)
    email_status = await send_email(
        to=email,
        subject=f"You have been invited to {org.name} on Revion",
        body_text=(
            f"{current_user.full_name} has invited you to join {org.name} on Revion.\n\n"
            f"Accept the invitation and set your password here:\n{accept_url}\n\n"
            f"This link expires in {_INVITE_TTL_DAYS} days. If you did not expect this email "
            "you can safely ignore it."
        ),
    )

    return {
        "invitation": _serialise(inv),
        "accept_url": accept_url,
        "email_sent": email_status["sent"],
        "email_reason": email_status["reason"],
        "email_enabled": is_email_enabled(),
    }


@router.get("")
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_org_admin(current_user):
        raise HTTPException(403, "Only org admins can list invitations")
    q = select(Invitation).where(Invitation.org_id == current_user.org_id)
    if current_user.role in ("super_admin", "operator_admin", "analyst"):
        # Operator-tier sees all open invitations across orgs.
        q = select(Invitation)
    q = q.order_by(Invitation.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [_serialise(i) for i in rows]


@router.delete("/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = await db.get(Invitation, invitation_id)
    if not inv:
        raise HTTPException(404, "Invitation not found")
    if not _is_org_admin(current_user):
        raise HTTPException(403, "Only org admins can revoke invitations")
    is_op = current_user.role in ("super_admin", "operator_admin", "analyst")
    if not is_op and str(inv.org_id) != str(current_user.org_id):
        raise HTTPException(403, "Cannot revoke an invitation for a different org")
    if inv.accepted_at:
        raise HTTPException(409, "Invitation already accepted")
    await db.delete(inv)
    await db.commit()
    return {"status": "revoked"}


@router.get("/{token}/preview")
async def preview_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public read of an invitation by token, used by the accept page to
    show the org name and email before the user sets a password."""
    inv = (await db.execute(
        select(Invitation).where(Invitation.token == token)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invitation not found")
    if inv.accepted_at:
        raise HTTPException(409, "Invitation already accepted")
    if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "Invitation has expired")

    org = await db.get(Organisation, inv.org_id)
    return {
        "email": inv.email,
        "role": inv.role,
        "org_name": org.name if org else None,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
    }


@router.post("/{token}/accept")
@limiter.limit("10/hour")
async def accept_invitation(
    request: Request,
    token: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Accept invitation by setting password. Creates the user and returns
    a fresh JWT so the client can drop straight into the app."""
    from app.core.auth import create_access_token

    inv = (await db.execute(
        select(Invitation).where(Invitation.token == token)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invitation not found")
    if inv.accepted_at:
        raise HTTPException(409, "Invitation already accepted")
    if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "Invitation has expired")

    full_name = (payload.get("full_name") or "").strip()
    password = payload.get("password") or ""
    if not full_name:
        raise HTTPException(400, "full_name is required")
    if len(password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")

    # Email already covered by Invitation; reject if a user has been
    # created independently in the meantime.
    dup = await db.execute(select(User).where(User.email == inv.email))
    if dup.scalar_one_or_none():
        raise HTTPException(409, "A user with this email already exists")

    user = User(
        org_id=inv.org_id,
        email=inv.email,
        full_name=full_name,
        role=inv.role,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    inv.accepted_at = datetime.now(timezone.utc)
    inv.accepted_user_id = user.id
    await db.commit()
    await db.refresh(user)

    token_jwt = create_access_token({"sub": str(user.id), "role": user.role, "org": str(user.org_id)})
    return {
        "access_token": token_jwt,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id),
        },
    }
