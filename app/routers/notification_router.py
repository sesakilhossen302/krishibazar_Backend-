import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db
from app.models.notification_model import Notification
from app.models.user_model import User
from app.schemas.notification_schema import NotificationResponse, NotificationCreate

router = APIRouter(prefix="/notifications", tags=["Notifications (বিজ্ঞপ্তি)"])


def resolve_user_id(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> str:
    """
    Resolve user ID from Bearer Token or Query param (flexible for mobile app).
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_uid = payload.get("sub")
            if token_uid:
                return token_uid
        except JWTError:
            pass

    if user_id and user_id.strip():
        return user_id.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="ব্যবহারকারী শনাক্ত করা যায়নি (Token or user_id required)."
    )


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    resolved_uid: str = Depends(resolve_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all notifications for the user ordered by newest first.
    """
    return db.query(Notification).filter(
        Notification.user_id == resolved_uid
    ).order_by(Notification.created_at.desc(), Notification.id.desc()).all()


@router.get("/unread-count")
def get_unread_count(
    resolved_uid: str = Depends(resolve_user_id),
    db: Session = Depends(get_db)
):
    """
    Get number of unread notifications for badge icon.
    """
    count = db.query(Notification).filter(
        Notification.user_id == resolved_uid,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="বিজ্ঞপ্তি পাওয়া যায়নি।")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.patch("/mark-all-read")
def mark_all_as_read(
    resolved_uid: str = Depends(resolve_user_id),
    db: Session = Depends(get_db)
):
    """
    Mark all unread notifications as read for current user.
    """
    db.query(Notification).filter(
        Notification.user_id == resolved_uid,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "সকল বিজ্ঞপ্তি পঠিত হিসেবে চিহ্নিত করা হয়েছে।"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a notification.
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="বিজ্ঞপ্তি পাওয়া যায়নি।")
    db.delete(notif)
    db.commit()
    return {"success": True, "message": "বিজ্ঞপ্তি মুছে ফেলা হয়েছে।"}


@router.delete("/clear-all")
def clear_all_notifications(
    resolved_uid: str = Depends(resolve_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete all notifications for the user.
    """
    db.query(Notification).filter(Notification.user_id == resolved_uid).delete()
    db.commit()
    return {"success": True, "message": "সকল বিজ্ঞপ্তি মুছে ফেলা হয়েছে।"}


def send_in_app_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    related_id: str = ""
) -> Notification:
    """
    Utility helper to insert a notification for an event.
    """
    new_id = f"notif_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
    notif = Notification(
        id=new_id,
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id,
        is_read=False,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

