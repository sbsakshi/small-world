from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, verify_password
from app.modules.org.models import City, Session as SessionRow
from app.modules.org.models import SessionRecipientType, Staff, StaffRole, Venue
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers.service import authenticate_volunteer


class InvalidCredentials(Exception):
    pass


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


def _ensure_city_access(user: CurrentUser, city_id: int | None) -> None:
    """City leads may only touch their own city; founders may touch any city."""
    if user.role == StaffRole.city_lead and city_id != user.city_id:
        raise Forbidden


def authenticate_staff(db: DBSession, login_identifier: str, password: str) -> Staff | None:
    staff = db.scalar(
        select(Staff).where(Staff.login_identifier == login_identifier, Staff.active.is_(True))
    )
    if staff is None or not verify_password(password, staff.password_hash):
        return None
    return staff


def login(db: DBSession, login_identifier: str, password: str) -> tuple[CurrentUser, str, datetime]:
    """Tries staff credentials, then volunteer credentials (separate tables, both

    checked because login_identifier is only unique within each table, not
    globally). Returns the shaped user, the raw session token, and its expiry.
    """
    staff = authenticate_staff(db, login_identifier, password)
    if staff is not None:
        user = CurrentUser(
            user_type=SessionRecipientType.staff,
            id=staff.id,
            name=staff.name,
            role=staff.role,
            city_id=staff.city_id,
        )
        token, expires_at = _create_session(db, SessionRecipientType.staff, staff.id)
        return user, token, expires_at

    volunteer = authenticate_volunteer(db, login_identifier, password)
    if volunteer is not None:
        user = CurrentUser(
            user_type=SessionRecipientType.volunteer,
            id=volunteer.id,
            name=volunteer.name,
            role=None,
            city_id=volunteer.city_id,
        )
        token, expires_at = _create_session(db, SessionRecipientType.volunteer, volunteer.id)
        return user, token, expires_at

    raise InvalidCredentials


def _create_session(
    db: DBSession, user_type: SessionRecipientType, user_id: int
) -> tuple[str, datetime]:
    token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(SessionRow(token=token, user_type=user_type, user_id=user_id, expires_at=expires_at))
    db.commit()
    return token, expires_at


def get_current_user(db: DBSession, token: str) -> CurrentUser | None:
    session = db.scalar(select(SessionRow).where(SessionRow.token == token))
    if session is None or session.expires_at < datetime.now(timezone.utc):
        return None

    if session.user_type == SessionRecipientType.staff:
        staff = db.get(Staff, session.user_id)
        if staff is None or not staff.active:
            return None
        return CurrentUser(
            user_type=SessionRecipientType.staff,
            id=staff.id,
            name=staff.name,
            role=staff.role,
            city_id=staff.city_id,
        )

    from app.modules.volunteers.service import get_active_volunteer

    volunteer = get_active_volunteer(db, session.user_id)
    if volunteer is None:
        return None
    return CurrentUser(
        user_type=SessionRecipientType.volunteer,
        id=volunteer.id,
        name=volunteer.name,
        role=None,
        city_id=volunteer.city_id,
    )


def logout(db: DBSession, token: str) -> None:
    session = db.scalar(select(SessionRow).where(SessionRow.token == token))
    if session is not None:
        db.delete(session)
        db.commit()


def create_staff(
    db: DBSession,
    *,
    name: str,
    phone: str,
    email: str | None,
    login_identifier: str,
    password: str,
    role: StaffRole,
    city_id: int | None,
) -> Staff:
    staff = Staff(
        name=name,
        phone=phone,
        email=email,
        login_identifier=login_identifier,
        password_hash=hash_password(password),
        role=role,
        city_id=city_id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


# --- Cities: founder-only. City leads can see their own city but not create/edit others. ---


def list_cities(db: DBSession, user: CurrentUser) -> list[City]:
    stmt = select(City)
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(City.id == user.city_id)
    return list(db.scalars(stmt))


def create_city(db: DBSession, user: CurrentUser, *, name: str, active: bool = True) -> City:
    if user.role != StaffRole.founder:
        raise Forbidden
    city = City(name=name, active=active)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


def update_city(
    db: DBSession, user: CurrentUser, city_id: int, *, name: str | None, active: bool | None
) -> City:
    if user.role != StaffRole.founder:
        raise Forbidden
    city = db.get(City, city_id)
    if city is None:
        raise NotFound
    if name is not None:
        city.name = name
    if active is not None:
        city.active = active
    db.commit()
    db.refresh(city)
    return city


# --- Venues: founder can touch any city; city lead only their own. ---


def list_venues(db: DBSession, user: CurrentUser) -> list[Venue]:
    stmt = select(Venue)
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(Venue.city_id == user.city_id)
    return list(db.scalars(stmt))


def create_venue(
    db: DBSession,
    user: CurrentUser,
    *,
    name: str,
    city_id: int,
    address: str,
    capacity: int,
    active: bool = True,
) -> Venue:
    _ensure_city_access(user, city_id)
    venue = Venue(name=name, city_id=city_id, address=address, capacity=capacity, active=active)
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


def update_venue(
    db: DBSession,
    user: CurrentUser,
    venue_id: int,
    *,
    name: str | None,
    address: str | None,
    capacity: int | None,
    active: bool | None,
) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFound
    _ensure_city_access(user, venue.city_id)
    if name is not None:
        venue.name = name
    if address is not None:
        venue.address = address
    if capacity is not None:
        venue.capacity = capacity
    if active is not None:
        venue.active = active
    db.commit()
    db.refresh(venue)
    return venue


# --- Staff: founder can touch any city and grant any role; city lead is confined to their own
# city and may only create/edit event_leads (never founders, never other cities' staff). ---


def list_staff(db: DBSession, user: CurrentUser) -> list[Staff]:
    stmt = select(Staff)
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(Staff.city_id == user.city_id)
    return list(db.scalars(stmt))


def create_staff_scoped(
    db: DBSession,
    actor: CurrentUser,
    *,
    name: str,
    phone: str,
    email: str | None,
    login_identifier: str,
    password: str,
    role: StaffRole,
    city_id: int | None,
) -> Staff:
    if actor.role == StaffRole.city_lead:
        if role != StaffRole.event_lead or city_id != actor.city_id:
            raise Forbidden
    return create_staff(
        db,
        name=name,
        phone=phone,
        email=email,
        login_identifier=login_identifier,
        password=password,
        role=role,
        city_id=city_id,
    )


def update_staff(
    db: DBSession,
    actor: CurrentUser,
    staff_id: int,
    *,
    name: str | None,
    phone: str | None,
    email: str | None,
    role: StaffRole | None,
    city_id: int | None,
    active: bool | None,
) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None:
        raise NotFound
    _ensure_city_access(actor, staff.city_id)
    if actor.role == StaffRole.city_lead:
        # City leads may not touch founders/other city leads, nor promote out of event_lead.
        if staff.role != StaffRole.event_lead:
            raise Forbidden
        if role is not None and role != StaffRole.event_lead:
            raise Forbidden
        if city_id is not None and city_id != actor.city_id:
            raise Forbidden
    if name is not None:
        staff.name = name
    if phone is not None:
        staff.phone = phone
    if email is not None:
        staff.email = email
    if role is not None:
        staff.role = role
    if city_id is not None:
        staff.city_id = city_id
    if active is not None:
        staff.active = active
    db.commit()
    db.refresh(staff)
    return staff
