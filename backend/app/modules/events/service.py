from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.contacts.models import Booking, BookingStatus
from app.modules.events.models import Event, EventCategory, EventStatus
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidTransition(Exception):
    pass


def _ensure_city_access(user: CurrentUser, city_id: int) -> None:
    if user.role == StaffRole.city_lead and city_id != user.city_id:
        raise Forbidden


def _ensure_event_access(user: CurrentUser, event: Event) -> None:
    """Founder: any event. City lead: events in their city. Event lead: only events they lead."""
    if user.role == StaffRole.founder:
        return
    if user.role == StaffRole.city_lead:
        if event.city_id != user.city_id:
            raise Forbidden
        return
    if user.role == StaffRole.event_lead:
        if event.lead_id != user.id:
            raise Forbidden
        return
    raise Forbidden


def list_events(
    db: DBSession,
    user: CurrentUser,
    *,
    city_id: int | None = None,
    venue_id: int | None = None,
    status: EventStatus | None = None,
) -> list[Event]:
    stmt = select(Event)
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(Event.city_id == user.city_id)
    elif user.role == StaffRole.event_lead:
        stmt = stmt.where(Event.lead_id == user.id)
    if city_id is not None:
        stmt = stmt.where(Event.city_id == city_id)
    if venue_id is not None:
        stmt = stmt.where(Event.venue_id == venue_id)
    if status is not None:
        stmt = stmt.where(Event.status == status)
    return list(db.scalars(stmt.order_by(Event.starts_at)))


def get_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    return event


def create_event(
    db: DBSession,
    user: CurrentUser,
    *,
    title: str,
    category: EventCategory,
    city_id: int,
    venue_id: int,
    starts_at: datetime,
    capacity: int,
    lead_id: int,
) -> Event:
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    _ensure_city_access(user, city_id)
    event = Event(
        title=title,
        category=category,
        city_id=city_id,
        venue_id=venue_id,
        starts_at=starts_at,
        capacity=capacity,
        lead_id=lead_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(
    db: DBSession,
    user: CurrentUser,
    event_id: int,
    *,
    title: str | None,
    category: EventCategory | None,
    venue_id: int | None,
    starts_at: datetime | None,
    capacity: int | None,
    lead_id: int | None,
) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    if event.status in (EventStatus.completed, EventStatus.cancelled):
        raise InvalidTransition
    if title is not None:
        event.title = title
    if category is not None:
        event.category = category
    if venue_id is not None:
        event.venue_id = venue_id
    if starts_at is not None:
        event.starts_at = starts_at
    if capacity is not None:
        event.capacity = capacity
    if lead_id is not None:
        event.lead_id = lead_id
    db.commit()
    db.refresh(event)
    return event


def publish_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    if event.status != EventStatus.draft:
        raise InvalidTransition
    event.status = EventStatus.published
    db.commit()
    db.refresh(event)
    return event


def cancel_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    """Cancels the event and cascades to every non-terminal booking, in one transaction."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    if event.status == EventStatus.cancelled:
        raise InvalidTransition
    if event.status == EventStatus.completed:
        raise InvalidTransition
    event.status = EventStatus.cancelled
    non_terminal = (
        BookingStatus.initiated,
        BookingStatus.confirmed,
    )
    for booking in db.scalars(
        select(Booking).where(Booking.event_id == event_id, Booking.status.in_(non_terminal))
    ):
        booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(event)
    return event


def complete_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    """Closes out a live event: confirmed-but-not-checked-in bookings become no-shows."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    if event.status != EventStatus.published:
        raise InvalidTransition
    event.status = EventStatus.completed
    for booking in db.scalars(
        select(Booking).where(Booking.event_id == event_id, Booking.status == BookingStatus.confirmed)
    ):
        booking.status = BookingStatus.no_show
    db.commit()
    db.refresh(event)
    return event


def duplicate_event(db: DBSession, user: CurrentUser, event_id: int, *, starts_at: datetime) -> Event:
    source = db.get(Event, event_id)
    if source is None:
        raise NotFound
    _ensure_event_access(user, source)
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    clone = Event(
        title=source.title,
        category=source.category,
        city_id=source.city_id,
        venue_id=source.venue_id,
        starts_at=starts_at,
        capacity=source.capacity,
        lead_id=source.lead_id,
        status=EventStatus.draft,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone
