from datetime import datetime, timezone

import pytest

from app.modules.events.models import EventCategory
from app.modules.events.service import complete_event, create_event, publish_event
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.reports.models import DecisionStatus, IssuePriority, IssueStatus
from app.modules.reports.service import (
    AlreadyExists,
    Forbidden,
    InvalidTransition,
    create_decision,
    create_issue,
    create_report,
    decide_decision,
    get_report,
    list_decisions,
    resolve_issue,
    update_report,
)


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000100", email=None,
        login_identifier="founder-reports", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def city_lead(db, founder):
    city = create_city(db, founder, name="Reports City")
    staff = create_staff(
        db, name="Lead", phone="+919900000101", email=None,
        login_identifier="lead-reports", password="pw", role=StaffRole.city_lead, city_id=city.id,
    )
    user = CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.city_lead, city_id=city.id)
    return city, user


def test_decision_scoped_to_own_city(db, founder, city_lead):
    city, lead_user = city_lead
    other_city = create_city(db, founder, name="Other City")

    with pytest.raises(Forbidden):
        create_decision(
            db, lead_user, city_id=other_city.id, venue_id=None, text="Not my city", note=None, staff_only=False
        )

    decision = create_decision(
        db, lead_user, city_id=city.id, venue_id=None, text="Buy easels?", note=None, staff_only=False
    )
    assert decision.status == DecisionStatus.open

    decided = decide_decision(db, lead_user, decision.id)
    assert decided.status == DecisionStatus.decided
    assert decided.decided_by_id == lead_user.id

    with pytest.raises(InvalidTransition):
        decide_decision(db, lead_user, decision.id)

    visible = list_decisions(db, lead_user)
    assert [d.id for d in visible] == [decision.id]


def test_issue_resolve_lifecycle(db, city_lead):
    city, lead_user = city_lead
    issue = create_issue(
        db, lead_user, city_id=city.id, venue_id=None, text="AC too loud",
        priority=IssuePriority.low, due_date=None,
    )
    assert issue.status == IssueStatus.open

    resolved = resolve_issue(db, lead_user, issue.id)
    assert resolved.status == IssueStatus.resolved
    assert resolved.resolved_by_id == lead_user.id
    assert resolved.resolved_at is not None

    with pytest.raises(InvalidTransition):
        resolve_issue(db, lead_user, issue.id)


def test_event_report_requires_completed_event_and_is_singular(db, founder, city_lead):
    city, lead_user = city_lead
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead_user.id,
    )

    with pytest.raises(InvalidTransition):
        create_report(db, lead_user, event.id, note="too early", tags=None)

    publish_event(db, founder, event.id)
    complete_event(db, founder, event.id)

    report = create_report(
        db, lead_user, event.id, note="Great night", tags=[{"tone": "good", "label": "On time"}]
    )
    assert report.event_id == event.id

    with pytest.raises(AlreadyExists):
        create_report(db, lead_user, event.id, note="Duplicate", tags=None)

    updated = update_report(db, lead_user, event.id, note="Updated note", tags=None)
    assert updated.note == "Updated note"

    fetched = get_report(db, founder, event.id)
    assert fetched.id == report.id
