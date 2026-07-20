from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.notifications.models import Notification, NotificationRecipientType
from app.modules.notifications.providers import in_app_provider


class NotFound(Exception):
    pass


def notify(
    db: DBSession,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
    title: str,
    body: str,
    action_type: str | None = None,
    action_ref: int | None = None,
) -> Notification:
    return in_app_provider.send(
        db,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title=title,
        body=body,
        action_type=action_type,
        action_ref=action_ref,
    )


def list_inbox(
    db: DBSession, *, recipient_type: NotificationRecipientType, recipient_id: int, unread_only: bool = False
) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.recipient_type == recipient_type, Notification.recipient_id == recipient_id
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list(db.scalars(stmt.order_by(Notification.created_at.desc())))


def mark_read(db: DBSession, *, recipient_type: NotificationRecipientType, recipient_id: int, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if (
        notification is None
        or notification.recipient_type != recipient_type
        or notification.recipient_id != recipient_id
    ):
        raise NotFound
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
