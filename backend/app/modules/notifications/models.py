import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class NotificationRecipientType(str, enum.Enum):
    staff = "staff"
    volunteer = "volunteer"


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_type: Mapped[NotificationRecipientType] = mapped_column(
        SAEnum(NotificationRecipientType, name="notification_recipient_type")
    )
    recipient_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    # e.g. "assignment_response" — tells the inbox UI which action buttons to render.
    action_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Timestamp, not a boolean: preserves *when* it was read, not just that it was.
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
