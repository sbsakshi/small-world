from datetime import datetime, timezone

import pytest

from app.modules.contacts.service import check_in_booking, create_manual_booking
from app.modules.events.models import EventCategory, EventStatus
from app.modules.events.service import (
    Forbidden,
    InvalidTransition,
    close_door,
    create_event,
    mark_started,
    publish_event,
)
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.service import create_assignment, create_volunteer, respond_to_assignment


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000700", email=None,
        login_identifier="founder-lifecycle", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def world(db, founder):
    city = create_city(db, founder, name="Lifecycle City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000701", email=None,
        login_identifier="lead-lifecycle", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    volunteer = create_volunteer(
        db, name="Vol", phone="+919900000702", email=None,
        login_identifier="vol-lifecycle", password="pw", city_id=city.id, skills=[],
    )
    other_volunteer = create_volunteer(
        db, name="Other Vol", phone="+919900000703", email=None,
        login_identifier="other-vol-lifecycle", password="pw", city_id=city.id, skills=[],
    )
    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
    )
    return {
        "volunteer": volunteer,
        "volunteer_user": CurrentUser(user_type="volunteer", id=volunteer.id, name=volunteer.name, role=None, city_id=None),
        "other_volunteer_user": CurrentUser(
            user_type="volunteer", id=other_volunteer.id, name=other_volunteer.name, role=None, city_id=None
        ),
        "event": event,
    }


def test_mark_started_noops_once_already_started(db, founder, world):
    publish_event(db, founder, world["event"].id)
    started = mark_started(db, world["event"].id)
    assert started.status == EventStatus.started
    assert started.started_at is not None

    again = mark_started(db, world["event"].id)
    assert again is None
    db.refresh(started)
    assert started.status == EventStatus.started


def test_check_in_flips_event_to_started_once(db, founder, world):
    event = publish_event(db, founder, world["event"].id)
    b1 = create_manual_booking(db, event_id=event.id, phone="9876500001", name="A", email=None, amount=0)
    b2 = create_manual_booking(db, event_id=event.id, phone="9876500002", name="B", email=None, amount=0)

    check_in_booking(db, founder, event_id=event.id, booking_id=b1.id)
    db.refresh(event)
    first_started_at = event.started_at
    assert event.status == EventStatus.started
    assert first_started_at is not None

    check_in_booking(db, founder, event_id=event.id, booking_id=b2.id)
    db.refresh(event)
    assert event.started_at == first_started_at


def test_close_door_invalid_from_draft_and_closed(db, founder, world):
    with pytest.raises(InvalidTransition):
        close_door(db, founder, world["event"].id)

    event = publish_event(db, founder, world["event"].id)
    closed = close_door(db, founder, event.id)
    assert closed.status == EventStatus.awaiting_review

    with pytest.raises(InvalidTransition):
        close_door(db, founder, event.id)


def test_close_door_by_assigned_accepted_volunteer(db, founder, world):
    event = publish_event(db, founder, world["event"].id)
    assignment = create_assignment(
        db, founder, event_id=event.id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)

    closed = close_door(db, world["volunteer_user"], event.id)
    assert closed.status == EventStatus.awaiting_review


def test_close_door_forbidden_for_unassigned_volunteer(db, founder, world):
    event = publish_event(db, founder, world["event"].id)
    with pytest.raises(Forbidden):
        close_door(db, world["other_volunteer_user"], event.id)


def test_checkin_forbidden_for_unassigned_volunteer(db, founder, world):
    event = publish_event(db, founder, world["event"].id)
    booking = create_manual_booking(db, event_id=event.id, phone="9876500003", name="C", email=None, amount=0)
    from app.modules.contacts.service import Forbidden as ContactsForbidden

    with pytest.raises(ContactsForbidden):
        check_in_booking(db, world["other_volunteer_user"], event_id=event.id, booking_id=booking.id)
