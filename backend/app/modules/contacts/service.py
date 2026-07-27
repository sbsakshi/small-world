import csv
import io
import re

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.contacts.models import Booking, BookingSource, BookingStatus, Contact
from app.modules.events import service as events_service
from app.modules.events.models import Event, EventStatus
from app.modules.org.schemas import CurrentUser


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidPhone(Exception):
    pass


class InvalidTransition(Exception):
    pass


def normalize_phone(raw: str) -> str:
    """Normalizes any Indian phone number format to +91XXXXXXXXXX.

    Strips all non-digits, then takes the last 10 digits (dropping a leading
    country code / trunk 0 if present). Raises InvalidPhone if what's left
    isn't a plausible 10-digit mobile number.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) > 10:
        digits = digits[-10:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise InvalidPhone(raw)
    return f"+91{digits}"


def get_or_create_contact(
    db: DBSession, *, phone: str, name: str, email: str | None = None, city_id: int | None = None
) -> Contact:
    normalized = normalize_phone(phone)
    contact = db.scalar(select(Contact).where(Contact.phone == normalized))
    if contact is not None:
        return contact
    contact = Contact(phone=normalized, name=name, email=email, city_id=city_id)
    db.add(contact)
    db.flush()
    return contact


def list_contacts(db: DBSession, *, city_id: int | None = None) -> list[Contact]:
    stmt = select(Contact)
    if city_id is not None:
        stmt = stmt.where(Contact.city_id == city_id)
    return list(db.scalars(stmt))


def get_contact(db: DBSession, contact_id: int) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise NotFound
    return contact


def update_contact(
    db: DBSession,
    contact_id: int,
    *,
    name: str | None,
    email: str | None,
    city_id: int | None,
    opted_out: bool | None,
) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise NotFound
    if name is not None:
        contact.name = name
    if email is not None:
        contact.email = email
    if city_id is not None:
        contact.city_id = city_id
    if opted_out is not None:
        contact.opted_out = opted_out
    db.commit()
    db.refresh(contact)
    return contact


def create_manual_booking(
    db: DBSession, *, event_id: int, phone: str, name: str, email: str | None, amount: int
) -> Booking:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    if event.status != EventStatus.published:
        raise InvalidTransition
    contact = get_or_create_contact(db, phone=phone, name=name, email=email, city_id=event.city_id)
    booking = Booking(
        contact_id=contact.id,
        event_id=event_id,
        status=BookingStatus.confirmed,
        source=BookingSource.manual,
        amount=amount,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def list_bookings(db: DBSession, *, event_id: int | None = None, contact_id: int | None = None) -> list[Booking]:
    stmt = select(Booking)
    if event_id is not None:
        stmt = stmt.where(Booking.event_id == event_id)
    if contact_id is not None:
        stmt = stmt.where(Booking.contact_id == contact_id)
    return list(db.scalars(stmt))


def list_bookings_for(
    db: DBSession, actor: CurrentUser, *, event_id: int | None = None, contact_id: int | None = None
) -> list[Booking]:
    """Staff: unrestricted, same as `list_bookings`. Volunteers: must scope to a single event
    they hold an accepted assignment for (the guest list at their own door), else Forbidden."""
    from app.modules.org.models import SessionRecipientType

    if actor.user_type == SessionRecipientType.volunteer:
        if event_id is None:
            raise Forbidden
        event = db.get(Event, event_id)
        if event is None:
            raise NotFound
        try:
            events_service._ensure_door_access(db, actor, event)
        except events_service.Forbidden:
            raise Forbidden
    return list_bookings(db, event_id=event_id, contact_id=contact_id)


def list_door_roster(db: DBSession, actor: CurrentUser, *, event_id: int) -> list[dict]:
    """Guest list for the door, with the contact name/phone denormalized onto each row — a
    scoped alternative to the staff-only `/contacts` directory, so a volunteer can see who
    they're checking in without being handed the full contact list."""
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    try:
        events_service._ensure_door_access(db, actor, event)
    except events_service.Forbidden:
        raise Forbidden
    rows = db.execute(
        select(Booking.id, Contact.name, Contact.phone, Booking.status)
        .join(Contact, Booking.contact_id == Contact.id)
        .where(Booking.event_id == event_id)
    ).all()
    return [{"booking_id": r[0], "name": r[1], "phone": r[2], "status": r[3]} for r in rows]


def check_in_booking(db: DBSession, actor: CurrentUser, *, event_id: int, booking_id: int) -> Booking:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    try:
        events_service._ensure_door_access(db, actor, event)
    except events_service.Forbidden:
        raise Forbidden
    booking = db.get(Booking, booking_id)
    if booking is None or booking.event_id != event_id:
        raise NotFound
    if booking.status != BookingStatus.confirmed:
        raise InvalidTransition
    booking.status = BookingStatus.checked_in
    db.commit()
    events_service.mark_started(db, event_id)
    db.refresh(booking)
    return booking


def import_csv(db: DBSession, *, event_id: int, content: bytes) -> tuple[int, int, list[tuple[int, str]]]:
    """Imports a CSV of `phone,name,email` rows as bookings against one event.

    Idempotent: re-importing the same file is a no-op, keyed on
    (source=csv, external_id=f"{normalized_phone}:{event_id}") so a repeat
    upload never creates duplicate bookings.
    """
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound

    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created = 0
    skipped = 0
    errors: list[tuple[int, str]] = []

    for i, row in enumerate(reader, start=2):
        phone = (row.get("phone") or "").strip()
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip() or None
        if not phone or not name:
            errors.append((i, "missing phone or name"))
            continue
        try:
            normalized = normalize_phone(phone)
        except InvalidPhone:
            errors.append((i, f"invalid phone: {phone}"))
            continue

        external_id = f"{normalized}:{event_id}"
        existing = db.scalar(
            select(Booking).where(
                Booking.source == BookingSource.csv, Booking.external_id == external_id
            )
        )
        if existing is not None:
            skipped += 1
            continue

        contact = get_or_create_contact(db, phone=normalized, name=name, email=email, city_id=event.city_id)
        db.add(
            Booking(
                contact_id=contact.id,
                event_id=event_id,
                status=BookingStatus.confirmed,
                source=BookingSource.csv,
                amount=0,
                external_id=external_id,
            )
        )
        created += 1

    db.commit()
    return created, skipped, errors
