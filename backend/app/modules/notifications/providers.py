from abc import ABC, abstractmethod

from sqlalchemy.orm import Session as DBSession

from app.modules.notifications.models import Notification, NotificationRecipientType


class MessagingProvider(ABC):
    """One outbound channel for a notification. InAppProvider is the only one wired up in phase 1;
    an SMS/WhatsApp provider can be added later behind the same interface."""

    @abstractmethod
    def send(
        self,
        db: DBSession,
        *,
        recipient_type: NotificationRecipientType,
        recipient_id: int,
        title: str,
        body: str,
        action_type: str | None = None,
        action_ref: int | None = None,
    ) -> Notification:
        raise NotImplementedError


class InAppProvider(MessagingProvider):
    def send(
        self,
        db: DBSession,
        *,
        recipient_type: NotificationRecipientType,
        recipient_id: int,
        title: str,
        body: str,
        action_type: str | None = None,
        action_ref: int | None = None,
    ) -> Notification:
        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            body=body,
            action_type=action_type,
            action_ref=action_ref,
        )
        db.add(notification)
        db.flush()
        return notification


in_app_provider = InAppProvider()
