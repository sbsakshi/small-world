from datetime import datetime, timezone

import pytest

from app.modules.contacts.models import BookingStatus
from app.modules.contacts.service import create_manual_booking
from app.modules.events.models import EventCategory, EventStatus
from app.modules.events.service import cancel_event, create_event, publish_event
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000000", email=None,
        login_identifier="founder-cascade", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


def test_cancel_cascades_to_non_terminal_bookings(db, founder):
    city = create_city(db, founder, name="Cascade City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000011", email=None,
        login_identifier="lead-cascade", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
    )
    publish_event(db, founder, event.id)

    booking = create_manual_booking(
        db, event_id=event.id, phone="9876543211", name="Attendee", email=None, amount=0
    )
    assert booking.status == BookingStatus.confirmed

    cancelled = cancel_event(db, founder, event.id)
    assert cancelled.status == EventStatus.cancelled

    db.refresh(booking)
    assert booking.status == BookingStatus.cancelled
