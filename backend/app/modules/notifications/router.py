from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.modules.notifications import service
from app.modules.notifications.models import NotificationRecipientType
from app.modules.notifications.schemas import NotificationOut
from app.modules.org.deps import get_current_user
from app.modules.org.models import SessionRecipientType
from app.modules.org.schemas import CurrentUser

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)])


def _recipient_type(user: CurrentUser) -> NotificationRecipientType:
    return (
        NotificationRecipientType.staff
        if user.user_type == SessionRecipientType.staff
        else NotificationRecipientType.volunteer
    )


@router.get("", response_model=list[NotificationOut])
def inbox(
    unread_only: bool = False, user: CurrentUser = Depends(get_current_user), db: DBSession = Depends(get_db)
) -> list[NotificationOut]:
    return service.list_inbox(
        db, recipient_type=_recipient_type(user), recipient_id=user.id, unread_only=unread_only
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int, user: CurrentUser = Depends(get_current_user), db: DBSession = Depends(get_db)
) -> NotificationOut:
    try:
        return service.mark_read(
            db, recipient_type=_recipient_type(user), recipient_id=user.id, notification_id=notification_id
        )
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
