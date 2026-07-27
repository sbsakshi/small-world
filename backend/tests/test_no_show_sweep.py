from datetime import datetime, timezone

import pytest

from app.jobs.tasks import sweep_no_shows
from app.modules.contacts.models import BookingStatus
from app.modules.contacts.service import create_manual_booking
from app.modules.events.models import EventCategory, EventStatus
from app.modules.events.service import create_event, publish_event
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000300", email=None,
        login_identifier="founder-sweep", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def published_event(db, founder):
    city = create_city(db, founder, name="Sweep City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000301", email=None,
        login_identifier="lead-sweep", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
    )
    return publish_event(db, founder, event.id)


def test_sweep_marks_confirmed_bookings_as_no_show(db, patch_job_session, published_event):
    booking = create_manual_booking(
        db, event_id=published_event.id, phone="9876543210", name="Attendee", email=None, amount=0
    )
    assert booking.status == BookingStatus.confirmed

    sweep_no_shows(published_event.id)

    db.refresh(booking)
    assert booking.status == BookingStatus.no_show


def test_sweep_does_not_touch_checked_in_bookings(db, patch_job_session, published_event, founder):
    from app.modules.contacts.service import check_in_booking

    booking = create_manual_booking(
        db, event_id=published_event.id, phone="9876543211", name="Attendee", email=None, amount=0
    )
    checked_in = check_in_booking(db, founder, event_id=published_event.id, booking_id=booking.id)
    assert checked_in.status == BookingStatus.checked_in

    sweep_no_shows(published_event.id)

    db.refresh(checked_in)
    assert checked_in.status == BookingStatus.checked_in


def test_sweep_is_a_no_op_once_the_door_is_closed(db, patch_job_session, published_event, founder):
    from app.modules.events.service import close_door

    booking = create_manual_booking(
        db, event_id=published_event.id, phone="9876543212", name="Attendee", email=None, amount=0
    )
    closed = close_door(db, founder, published_event.id)
    assert closed.status == EventStatus.awaiting_review
    # The sweep only ever acts on `published` events; once the door is closed (and bookkeeping
    # deferred to the eventual autopsy submission), a late-firing sweep must not touch anything.
    sweep_no_shows(published_event.id)

    db.refresh(booking)
    assert booking.status == BookingStatus.confirmed


def test_sweep_is_a_no_op_for_nonexistent_event(db, patch_job_session):
    sweep_no_shows(999999)
