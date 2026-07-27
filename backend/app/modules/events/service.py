from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.contacts.models import Booking, BookingStatus
from app.modules.events.models import Event, EventCategory, EventStatus
from app.modules.notifications import service as notifications_service
from app.modules.notifications.models import NotificationRecipientType
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers.models import AssignmentStatus, VolunteerAssignment


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


def get_event(db: DBSession, actor: CurrentUser, event_id: int) -> Event:
    """Staff use the normal event-access rules; an assigned+accepted volunteer can also read
    their own event (needed for the door check-in screen's title/venue/capacity)."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_door_access(db, actor, event)
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
    notifications_service.notify(
        db,
        recipient_type=NotificationRecipientType.staff,
        recipient_id=event.lead_id,
        title=f"You're leading {event.title}",
        body="A new event was created with you as lead — head over to assign volunteers.",
        action_type="event_created",
        action_ref=event.id,
    )
    db.commit()
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
    if event.status in (EventStatus.closed, EventStatus.cancelled):
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
    notifications_service.notify(
        db,
        recipient_type=NotificationRecipientType.staff,
        recipient_id=event.lead_id,
        title=f"{event.title} is published",
        body="It's live — make sure volunteers are assigned before the night of.",
        action_type="event_published",
        action_ref=event.id,
    )
    db.commit()
    return event


def cancel_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    """Cancels the event and cascades to every non-terminal booking, in one transaction."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    if event.status == EventStatus.cancelled:
        raise InvalidTransition
    if event.status == EventStatus.closed:
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


def mark_started(db: DBSession, event_id: int) -> Event | None:
    """First successful check-in flips a published event to started. No-ops past that point
    (repeat check-ins never re-trigger it) — called from contacts.service.check_in_booking."""
    event = db.get(Event, event_id)
    if event is None or event.status != EventStatus.published:
        return None
    event.status = EventStatus.started
    event.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


def _ensure_door_access(db: DBSession, actor: CurrentUser, event: Event) -> None:
    """Door actions (check-in, close-door): staff via the normal event-access rules, or the
    volunteer themself if they hold an accepted assignment for this event."""
    from app.modules.org.models import SessionRecipientType

    if actor.user_type == SessionRecipientType.staff:
        _ensure_event_access(actor, event)
        return
    assigned = db.scalar(
        select(VolunteerAssignment).where(
            VolunteerAssignment.event_id == event.id,
            VolunteerAssignment.volunteer_id == actor.id,
            VolunteerAssignment.status == AssignmentStatus.accepted,
        )
    )
    if assigned is None:
        raise Forbidden


def close_door(db: DBSession, actor: CurrentUser, event_id: int) -> Event:
    """Volunteer (or staff) signal that check-ins are done for the night. Does not do any
    bookkeeping — that only happens once the lead submits the event's autopsy."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_door_access(db, actor, event)
    if event.status not in (EventStatus.published, EventStatus.started):
        raise InvalidTransition
    event.status = EventStatus.awaiting_review
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
