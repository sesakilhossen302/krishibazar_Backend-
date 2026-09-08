import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification_model import Notification
from app.models.user_model import User
from app.schemas.notification_schema import NotificationResponse, NotificationCreate
from app.utils import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all notifications for the authenticated user (Farmer or Buyer).
    """
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.id.desc()).all()


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


def send_in_app_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    related_id: str = ""
):
    """
    Utility helper to insert a notification for an event.
    """
    new_id = f"notif_{uuid.uuid4().hex[:10]}"
    notif = Notification(
        id=new_id,
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id,
        is_read=False,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(notif)
    db.commit()
