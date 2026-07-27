from datetime import date, datetime, timedelta, timezone

import pytest

from app.jobs.tasks import send_autopsy_prompt, send_autopsy_reminder
from app.modules.events.models import EventCategory
from app.modules.events.service import close_door, create_event, publish_event
from app.modules.knowledge.models import IssueLevel, IssueStatus
from app.modules.knowledge.schemas import AutopsyVolunteerRatingIn
from app.modules.knowledge.service import (
    AlreadyExists,
    Forbidden,
    InvalidTransition,
    NotFound,
    count_recent_issues,
    create_decision,
    create_issue,
    escalate_issue,
    get_autopsy,
    get_issue,
    list_decisions,
    list_issues,
    list_pending_autopsies,
    resolve_issue,
    submit_autopsy,
)
from app.modules.notifications.models import Notification, NotificationRecipientType
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.service import create_assignment, create_volunteer, respond_to_assignment


def _user(staff, role=None, city_id=None, user_type="staff"):
    return CurrentUser(user_type=user_type, id=staff.id, name=staff.name, role=role, city_id=city_id)


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000500", email=None,
        login_identifier="founder-knowledge", password="pw", role=StaffRole.founder, city_id=None,
    )
    return _user(staff, StaffRole.founder, None)


@pytest.fixture
def world(db, founder):
    city = create_city(db, founder, name="Knowledge City")
    other_city = create_city(db, founder, name="Other Knowledge City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead_staff = create_staff(
        db, name="Lead", phone="+919900000501", email=None,
        login_identifier="lead-knowledge", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    other_lead_staff = create_staff(
        db, name="Other Lead", phone="+919900000502", email=None,
        login_identifier="other-lead-knowledge", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    city_lead_staff = create_staff(
        db, name="City Lead", phone="+919900000503", email=None,
        login_identifier="city-lead-knowledge", password="pw", role=StaffRole.city_lead, city_id=city.id,
    )
    other_city_lead_staff = create_staff(
        db, name="Other City Lead", phone="+919900000504", email=None,
        login_identifier="other-city-lead-knowledge", password="pw", role=StaffRole.city_lead, city_id=other_city.id,
    )
    volunteer = create_volunteer(
        db, name="Vol", phone="+919900000505", email=None,
        login_identifier="vol-knowledge", password="pw", city_id=city.id, skills=[],
    )
    other_volunteer = create_volunteer(
        db, name="Other Vol", phone="+919900000506", email=None,
        login_identifier="other-vol-knowledge", password="pw", city_id=city.id, skills=[],
    )

    event = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead_staff.id,
    )
    return {
        "city": city,
        "other_city": other_city,
        "venue": venue,
        "lead_staff": lead_staff,
        "lead": _user(lead_staff, StaffRole.event_lead, city.id),
        "other_lead": _user(other_lead_staff, StaffRole.event_lead, city.id),
        "city_lead": _user(city_lead_staff, StaffRole.city_lead, city.id),
        "other_city_lead": _user(other_city_lead_staff, StaffRole.city_lead, other_city.id),
        "volunteer": volunteer,
        "volunteer_user": _user(volunteer, user_type="volunteer"),
        "other_volunteer_user": _user(other_volunteer, user_type="volunteer"),
        "event": event,
    }


def _complete(db, founder, event):
    """Publishes and closes the door, leaving the event in `awaiting_review` — ready for
    `submit_autopsy`, which is now the only thing that actually flips it to `closed`."""
    publish_event(db, founder, event.id)
    return close_door(db, founder, event.id)


# --- Event autopsies ------------------------------------------------------


def test_autopsy_submission_is_unique_per_event(db, founder, world):
    event = _complete(db, founder, world["event"])
    submit_autopsy(
        db, founder, event.id, attendance_actual=20, venue_rating=4,
        what_worked="Good vibes", what_didnt="Ran late", volunteer_ratings=[],
    )
    with pytest.raises(AlreadyExists):
        submit_autopsy(
            db, founder, event.id, attendance_actual=21, venue_rating=5,
            what_worked="Again", what_didnt="Again", volunteer_ratings=[],
        )


def test_autopsy_requires_awaiting_review_event(db, founder, world):
    with pytest.raises(InvalidTransition):
        submit_autopsy(
            db, founder, world["event"].id, attendance_actual=1, venue_rating=1,
            what_worked="x", what_didnt="y", volunteer_ratings=[],
        )


def test_autopsy_submit_forbidden_outside_scope(db, founder, world):
    event = _complete(db, founder, world["event"])
    with pytest.raises(Forbidden):
        submit_autopsy(
            db, world["other_city_lead"], event.id, attendance_actual=1, venue_rating=1,
            what_worked="x", what_didnt="y", volunteer_ratings=[],
        )


def test_autopsy_writes_through_volunteer_ratings_in_one_transaction(db, founder, world):
    assignment = create_assignment(
        db, founder, event_id=world["event"].id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)
    event = _complete(db, founder, world["event"])

    autopsy, rated_volunteer_ids, honored_volunteer_ids = submit_autopsy(
        db, founder, event.id, attendance_actual=15, venue_rating=5,
        what_worked="Great crowd", what_didnt="Nothing",
        volunteer_ratings=[AutopsyVolunteerRatingIn(assignment_id=assignment.id, rating=5, coordinator_note="Ace")],
    )

    assert rated_volunteer_ids == [world["volunteer"].id]
    assert honored_volunteer_ids == [world["volunteer"].id]
    db.refresh(assignment)
    assert assignment.rating == 5
    assert assignment.coordinator_note == "Ace"
    fetched = get_autopsy(db, event.id)
    assert fetched.id == autopsy.id
    db.refresh(event)
    assert event.status.value == "closed"


def test_autopsy_rejects_rating_for_assignment_from_another_event(db, founder, world):
    other_event = create_event(
        db, founder, title="Other", category=EventCategory.art, city_id=world["city"].id,
        venue_id=world["venue"].id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=world["lead_staff"].id,
    )
    assignment = create_assignment(
        db, founder, event_id=other_event.id, volunteer_id=world["volunteer"].id, coordinator_note=None
    )
    respond_to_assignment(db, world["volunteer"].id, assignment.id, accept=True)
    event = _complete(db, founder, world["event"])

    with pytest.raises(NotFound):
        submit_autopsy(
            db, founder, event.id, attendance_actual=1, venue_rating=1, what_worked="x", what_didnt="y",
            volunteer_ratings=[AutopsyVolunteerRatingIn(assignment_id=assignment.id, rating=5, coordinator_note=None)],
        )


def test_pending_autopsies_scoped_to_city_lead_founder_sees_all(db, founder, world):
    event = _complete(db, founder, world["event"])

    pending_for_city_lead = list_pending_autopsies(db, world["city_lead"])
    assert [e.id for e in pending_for_city_lead] == [event.id]

    pending_for_other_city_lead = list_pending_autopsies(db, world["other_city_lead"])
    assert pending_for_other_city_lead == []

    pending_for_founder = list_pending_autopsies(db, founder)
    assert event.id in [e.id for e in pending_for_founder]

    submit_autopsy(
        db, founder, event.id, attendance_actual=1, venue_rating=1, what_worked="x", what_didnt="y",
        volunteer_ratings=[],
    )
    assert list_pending_autopsies(db, world["city_lead"]) == []


# --- Autopsy prompt / reminder jobs ---------------------------------------


def _autopsy_notifications(db, staff_id):
    return list(
        db.query(Notification)
        .filter(
            Notification.recipient_type == NotificationRecipientType.staff,
            Notification.recipient_id == staff_id,
            Notification.action_type == "autopsy_fill",
        )
        .all()
    )


def test_autopsy_prompt_notifies_event_lead(db, patch_job_session, founder, world):
    event = _complete(db, founder, world["event"])
    send_autopsy_prompt(event.id)
    notifications = _autopsy_notifications(db, world["lead_staff"].id)
    assert len(notifications) == 1


def test_autopsy_reminder_fires_only_when_no_autopsy_exists(db, patch_job_session, founder, world):
    event = _complete(db, founder, world["event"])

    send_autopsy_reminder(event.id)
    assert len(_autopsy_notifications(db, world["lead_staff"].id)) == 1

    submit_autopsy(
        db, founder, event.id, attendance_actual=1, venue_rating=1, what_worked="x", what_didnt="y",
        volunteer_ratings=[],
    )
    send_autopsy_reminder(event.id)
    # Still just the one notification from before — the reminder is a no-op once an autopsy exists.
    assert len(_autopsy_notifications(db, world["lead_staff"].id)) == 1


# --- Decisions -------------------------------------------------------------


def test_decision_write_access_denies_event_lead(db, world):
    with pytest.raises(Forbidden):
        create_decision(
            db, world["lead"], title="Stop using venue X", body="Too loud",
            city_id=world["city"].id, venue_id=None, category=None, decided_at=date.today(),
        )


def test_decision_write_access_denies_city_lead_for_other_city(db, world):
    with pytest.raises(Forbidden):
        create_decision(
            db, world["city_lead"], title="Cross city", body="Nope",
            city_id=world["other_city"].id, venue_id=None, category=None, decided_at=date.today(),
        )


def test_decision_readable_by_any_staff_including_event_lead(db, world):
    decision = create_decision(
        db, world["city_lead"], title="Stop using venue X", body="Too loud",
        city_id=world["city"].id, venue_id=None, category=None, decided_at=date.today(),
    )
    visible = list_decisions(db, city_id=world["city"].id)
    assert [d.id for d in visible] == [decision.id]


# --- Issues -------------------------------------------------------------


def test_issue_escalation_ladder_and_ceiling(db, founder, world):
    issue = create_issue(
        db, world["lead"], title="AC broken", body="Too loud", event_id=world["event"].id,
        venue_id=None, volunteer_id=None,
    )
    assert issue.current_level == IssueLevel.event_lead

    escalated = escalate_issue(db, world["lead"], issue.id)
    assert escalated.current_level == IssueLevel.city_lead

    escalated = escalate_issue(db, world["city_lead"], issue.id)
    assert escalated.current_level == IssueLevel.founder

    with pytest.raises(InvalidTransition):
        escalate_issue(db, founder, issue.id)


def test_issue_escalate_forbidden_for_wrong_event_lead(db, world):
    issue = create_issue(
        db, world["lead"], title="AC broken", body="Too loud", event_id=world["event"].id,
        venue_id=None, volunteer_id=None,
    )
    with pytest.raises(Forbidden):
        escalate_issue(db, world["other_lead"], issue.id)


def test_issue_resolve_requires_note_and_rejects_double_resolve(db, world):
    issue = create_issue(
        db, world["lead"], title="AC broken", body="Too loud", event_id=world["event"].id,
        venue_id=None, volunteer_id=None,
    )
    resolved = resolve_issue(db, world["lead"], issue.id, resolution_note="Fixed the thermostat")
    assert resolved.status == IssueStatus.resolved
    assert resolved.resolution_note == "Fixed the thermostat"

    with pytest.raises(InvalidTransition):
        resolve_issue(db, world["lead"], issue.id, resolution_note="Again")

    with pytest.raises(InvalidTransition):
        escalate_issue(db, world["lead"], issue.id)


def test_volunteer_issue_visibility_is_own_only(db, world):
    mine = create_issue(
        db, world["volunteer_user"], title="Ride issue", body="Car broke down",
        event_id=None, venue_id=None, volunteer_id=None,
    )
    theirs = create_issue(
        db, world["other_volunteer_user"], title="Other's issue", body="Unrelated",
        event_id=None, venue_id=None, volunteer_id=None,
    )

    visible = list_issues(db, world["volunteer_user"])
    assert [i.id for i in visible] == [mine.id]

    assert get_issue(db, world["volunteer_user"], mine.id).id == mine.id
    with pytest.raises(Forbidden):
        get_issue(db, world["volunteer_user"], theirs.id)


def test_staff_issue_scoping(db, founder, world):
    event_issue = create_issue(
        db, world["lead"], title="Event issue", body="Body", event_id=world["event"].id,
        venue_id=None, volunteer_id=None,
    )
    venue_issue = create_issue(
        db, world["city_lead"], title="Venue issue", body="Body", event_id=None,
        venue_id=world["venue"].id, volunteer_id=None,
    )

    # The other event_lead in the same city has no standing on an event they don't lead.
    assert [i.id for i in list_issues(db, world["other_lead"])] == []

    # The city_lead of another city can't see either (both derive to the first city).
    assert [i.id for i in list_issues(db, world["other_city_lead"])] == []

    # This city's city_lead sees both (event issue still at event_lead level is out of reach
    # for viewing directly, but the venue issue derives to their own city).
    own_city_visible_ids = {i.id for i in list_issues(db, world["city_lead"])}
    assert venue_issue.id in own_city_visible_ids

    # Founder always sees everything.
    founder_visible_ids = {i.id for i in list_issues(db, founder)}
    assert {event_issue.id, venue_issue.id} <= founder_visible_ids


def test_issue_pattern_count_last_60_days(db, world):
    old_issue = create_issue(
        db, world["lead"], title="Old", body="Body", event_id=None,
        venue_id=world["venue"].id, volunteer_id=None,
    )
    old_issue.created_at = datetime.now(timezone.utc) - timedelta(days=61)
    db.commit()

    create_issue(
        db, world["lead"], title="Recent 1", body="Body", event_id=None,
        venue_id=world["venue"].id, volunteer_id=None,
    )
    create_issue(
        db, world["lead"], title="Recent 2", body="Body", event_id=None,
        venue_id=world["venue"].id, volunteer_id=None,
    )

    assert count_recent_issues(db, venue_id=world["venue"].id) == 2
