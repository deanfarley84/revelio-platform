"""notifications.py"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import Notification, User

router = APIRouter()


@router.get("/")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(desc(Notification.created_at))
        .limit(50)
    )
    return [
        {
            "id": str(n.id), "type": n.type, "title": n.title,
            "body": n.body, "read": n.read, "metadata": n.metadata,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in result.scalars().all()
    ]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(read=True)
    )
    await db.commit()
    return {"status": "read"}


@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return {"status": "ok"}
