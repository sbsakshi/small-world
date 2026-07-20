from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.models import NotificationRecipientType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_type: NotificationRecipientType
    recipient_id: int
    title: str
    body: str
    action_type: str | None
    action_ref: int | None
    read_at: datetime | None
    created_at: datetime
