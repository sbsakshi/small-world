import csv
import io
import re

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.contacts.models import Booking, BookingSource, BookingStatus, Contact
from app.modules.events.models import Event, EventStatus


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


def check_in_booking(db: DBSession, *, event_id: int, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.event_id != event_id:
        raise NotFound
    if booking.status != BookingStatus.confirmed:
        raise InvalidTransition
    booking.status = BookingStatus.checked_in
    db.commit()
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
