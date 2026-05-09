"""auth.py — Authentication routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import verify_password, create_access_token, hash_password, get_current_user
from app.models.user import User, Organisation

router = APIRouter()


@router.post("/login")
async def login(payload: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.get("email")))
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


@router.post("/register-org")
async def register_org(payload: dict, db: AsyncSession = Depends(get_db)):
    """Register a new organisation and admin user."""
    # Check email unique
    result = await db.execute(select(User).where(User.email == payload.get("email")))
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
        email=payload.get("email"),
        full_name=payload.get("full_name", ""),
        role="client_admin",
        password_hash=hash_password(payload.get("password", "")),
    )
    db.add(user)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "org": str(org.id)})
    return {"access_token": token, "token_type": "bearer", "org_id": str(org.id)}
