"""auth.py — Authentication routes"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import verify_password, create_access_token, hash_password, get_current_user
from app.core.rate_limit import limiter
from app.models.user import User, Organisation

router = APIRouter()


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    # Normalise email so browser autofill that capitalises the first letter
    # does not 401 a legitimate user. Bootstrap and register-org both
    # lowercase on write so this is purely defensive on the read side.
    email = (payload.get("email") or "").strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.get("password", ""), user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.role, "org": str(user.org_id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id) if user.org_id else None,
        },
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "org_id": str(current_user.org_id) if current_user.org_id else None,
    }


@router.patch("/me")
async def update_me(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the caller's profile: full_name, email, password.
    Email change requires the new value to be unused. Password change
    requires the current password to be supplied for verification."""
    changed: list[str] = []

    if "full_name" in payload:
        full_name = (payload.get("full_name") or "").strip()
        if not full_name:
            raise HTTPException(400, "full_name cannot be empty")
        if full_name != current_user.full_name:
            current_user.full_name = full_name
            changed.append("full_name")

    if "email" in payload:
        new_email = (payload.get("email") or "").strip().lower()
        if not new_email:
            raise HTTPException(400, "email cannot be empty")
        if new_email != current_user.email:
            dup = await db.execute(select(User).where(User.email == new_email))
            if dup.scalar_one_or_none():
                raise HTTPException(409, "Email already in use")
            current_user.email = new_email
            changed.append("email")

    if "new_password" in payload:
        new_password = payload.get("new_password") or ""
        current_password = payload.get("current_password") or ""
        if not current_password or not verify_password(current_password, current_user.password_hash):
            raise HTTPException(403, "Current password is incorrect")
        if len(new_password) < 8:
            raise HTTPException(400, "New password must be at least 8 characters")
        current_user.password_hash = hash_password(new_password)
        changed.append("password")

    if changed:
        await db.commit()
        await db.refresh(current_user)

    return {
        "changed": changed,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "org_id": str(current_user.org_id) if current_user.org_id else None,
        },
    }


@router.post("/bootstrap")
@limiter.limit("5/minute")
async def bootstrap(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Create the first super_admin and an internal Outturn organisation.
    Refuses if any super_admin already exists. Used once per fresh deploy
    to get a real account into an empty database.
    """
    existing = await db.execute(
        select(func.count(User.id)).where(User.role == "super_admin")
    )
    if (existing.scalar() or 0) > 0:
        raise HTTPException(409, "A super_admin already exists; use /auth/login")

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = payload.get("full_name") or ""
    if not email or not password or len(password) < 8 or not full_name:
        raise HTTPException(400, "email, full_name and a password of at least 8 chars are required")

    org = Organisation(
        name=payload.get("org_name") or "Outturn Operator",
        tier="enterprise",
        is_active=True,
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        email=email,
        full_name=full_name,
        role="super_admin",
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "org": str(org.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "role": user.role, "org_id": str(org.id)},
    }


@router.post("/register-org")
@limiter.limit("5/minute")
async def register_org(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    """Register a new organisation and admin user."""
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    org = Organisation(
        name=payload.get("org_name", ""),
        website=payload.get("website"),
        vertical=payload.get("vertical"),
        tier=payload.get("tier", "lite"),
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        email=email,
        full_name=payload.get("full_name", ""),
        role="client_admin",
        password_hash=hash_password(payload.get("password", "")),
    )
    db.add(user)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "org": str(org.id)})
    return {"access_token": token, "token_type": "bearer", "org_id": str(org.id)}
