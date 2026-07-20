from datetime import datetime, timezone

import pytest

from app.modules.events.models import EventCategory
from app.modules.events.service import create_event
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.models import AssignmentStatus
from app.modules.volunteers.service import (
    create_assignment,
    create_volunteer,
    expire_assignment,
    respond_to_assignment,
)
from app.modules.volunteers.service import InvalidTransition, NotFound


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000000", email=None,
        login_identifier="founder-test", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def world(db, founder):
    city = create_city(db, founder, name="Testville")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000010", email=None,
        login_identifier="lead-test", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    volunteer = create_volunteer(
        db, name="Vol", phone="+919900000020", email=None,
        login_identifier="vol-test", password="pw", city_id=city.id, skills=[EventCategory.art],
    )
    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
    )
    return {"founder": founder, "city": city, "venue": venue, "lead": lead, "volunteer": volunteer, "event": event}


def test_new_assignment_starts_pending(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    assert assignment.status == AssignmentStatus.pending
    assert assignment.responded_at is None


def test_accept_transitions_to_accepted(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    accepted = respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)
    assert accepted.status == AssignmentStatus.accepted
    assert accepted.responded_at is not None


def test_decline_transitions_to_declined(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    declined = respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=False)
    assert declined.status == AssignmentStatus.declined


def test_cannot_respond_twice(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)
    with pytest.raises(InvalidTransition):
        respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=False)


def test_wrong_volunteer_cannot_respond(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    with pytest.raises(NotFound):
        respond_to_assignment(db, volunteer_id=world["volunteer"].id + 999, assignment_id=assignment.id, accept=True)


def test_expire_only_touches_pending(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)
    # Already accepted — the escalation job firing late must be a no-op, not an overwrite.
    result = expire_assignment(db, assignment.id)
    assert result is None


def test_expire_pending_assignment(db, world):
    assignment = create_assignment(
        db, world["founder"], event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    expired = expire_assignment(db, assignment.id)
    assert expired.status == AssignmentStatus.expired
    assert expired.responded_at is not None
