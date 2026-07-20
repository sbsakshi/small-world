from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.db import get_db
from app.modules.org import service
from app.modules.org.models import SessionRecipientType, StaffRole
from app.modules.org.schemas import CurrentUser


def get_current_user(
    db: DBSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> CurrentUser:
    if session_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user = service.get_current_user(db, session_token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalid or expired")
    return user


def require_staff(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.user_type != SessionRecipientType.staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff access only")
    return user


def require_volunteer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.user_type != SessionRecipientType.volunteer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Volunteer access only")
    return user


def require_roles(*roles: StaffRole):
    """Dependency factory: require_roles(StaffRole.founder, StaffRole.city_lead)."""

    def _check(user: CurrentUser = Depends(require_staff)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return _check
