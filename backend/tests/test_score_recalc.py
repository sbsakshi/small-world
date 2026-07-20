from datetime import datetime, timezone

import pytest

from app.jobs.tasks import recalc_volunteer_score
from app.modules.events.models import EventCategory
from app.modules.events.service import create_event
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.service import create_assignment, create_volunteer, respond_to_assignment


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000400", email=None,
        login_identifier="founder-recalc", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def world(db, founder):
    city = create_city(db, founder, name="Recalc City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000401", email=None,
        login_identifier="lead-recalc", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    volunteer = create_volunteer(
        db, name="Vol", phone="+919900000402", email=None,
        login_identifier="vol-recalc", password="pw", city_id=city.id, skills=[],
    )

    def make_event(title: str):
        return create_event(
            db, founder, title=title, category=EventCategory.art, city_id=city.id,
            venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
        )

    return {"founder": founder, "volunteer": volunteer, "make_event": make_event}


def test_score_is_share_of_honored_among_decided_assignments(db, patch_job_session, world):
    volunteer = world["volunteer"]
    for i, outcome in enumerate(["accept", "accept", "decline"]):
        event = world["make_event"](f"Event {i}")
        assignment = create_assignment(
            db, world["founder"], event_id=event.id, volunteer_id=volunteer.id, coordinator_note=None
        )
        respond_to_assignment(db, volunteer.id, assignment.id, accept=(outcome == "accept"))
    # A still-pending assignment must not count toward the denominator.
    pending_event = world["make_event"]("Pending Event")
    create_assignment(db, world["founder"], event_id=pending_event.id, volunteer_id=volunteer.id, coordinator_note=None)

    recalc_volunteer_score(volunteer.id)

    db.refresh(volunteer)
    assert volunteer.cached_score == round(100 * 2 / 3)


def test_score_untouched_when_no_decided_assignments(db, patch_job_session, world):
    volunteer = world["volunteer"]
    assert volunteer.cached_score == 100

    recalc_volunteer_score(volunteer.id)

    db.refresh(volunteer)
    assert volunteer.cached_score == 100


def test_score_recalc_is_a_no_op_for_nonexistent_volunteer(db, patch_job_session):
    recalc_volunteer_score(999999)
