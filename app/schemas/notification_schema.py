from pydantic import BaseModel
from typing import Optional

class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    notification_type: str = "info"
    related_id: Optional[str] = ""

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    related_id: Optional[str] = ""
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True
