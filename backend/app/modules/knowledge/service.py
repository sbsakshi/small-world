from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession

from app.modules.contacts.models import Booking, BookingStatus
from app.modules.events.models import Event, EventCategory, EventStatus
from app.modules.knowledge.models import Decision, EventAutopsy, Issue, IssueLevel, IssueStatus, RaisedByType
from app.modules.notifications import service as notifications_service
from app.modules.notifications.models import NotificationRecipientType
from app.modules.org.models import SessionRecipientType, Staff, StaffRole, Venue
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers.models import AssignmentStatus, Volunteer, VolunteerAssignment


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidTransition(Exception):
    pass


class AlreadyExists(Exception):
    pass


# --- Event autopsies ------------------------------------------------------


def _ensure_autopsy_submit_access(user: CurrentUser, event: Event) -> None:
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


def get_autopsy(db: DBSession, event_id: int) -> EventAutopsy:
    """Read access is unscoped: any staff member can view any event's autopsy."""
    autopsy = db.scalar(select(EventAutopsy).where(EventAutopsy.event_id == event_id))
    if autopsy is None:
        raise NotFound
    return autopsy


def submit_autopsy(
    db: DBSession,
    user: CurrentUser,
    event_id: int,
    *,
    attendance_actual: int,
    venue_rating: int,
    what_worked: str,
    what_didnt: str,
    volunteer_ratings: list,
) -> tuple[EventAutopsy, list[int], list[int]]:
    """Creates the autopsy, writes ratings onto matching assignments, and closes the event out —
    all in one transaction. This is the one moment of truth for event completion: no-shows are
    marked, the event flips to `closed`, and every accepted volunteer gets their `events_done`
    bump here, regardless of whether `awaiting_review` was reached via a door-close or a staff
    override (see `events.service.close_door`).

    Returns the autopsy, the distinct volunteer ids that were rated, and the volunteer ids with
    an accepted (honored) assignment, so the router can enqueue score-recalc/events-done jobs the
    same way every other job-scheduling call site does.
    """
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_autopsy_submit_access(user, event)
    if db.scalar(select(EventAutopsy).where(EventAutopsy.event_id == event_id)) is not None:
        raise AlreadyExists
    if event.status != EventStatus.awaiting_review:
        raise InvalidTransition

    autopsy = EventAutopsy(
        event_id=event_id,
        submitted_by=user.id,
        attendance_actual=attendance_actual,
        venue_rating=venue_rating,
        what_worked=what_worked,
        what_didnt=what_didnt,
    )
    db.add(autopsy)

    rated_volunteer_ids: list[int] = []
    for entry in volunteer_ratings:
        assignment = db.get(VolunteerAssignment, entry.assignment_id)
        if (
            assignment is None
            or assignment.event_id != event_id
            or assignment.status != AssignmentStatus.accepted
        ):
            raise NotFound
        assignment.rating = entry.rating
        if entry.coordinator_note is not None:
            assignment.coordinator_note = entry.coordinator_note
        rated_volunteer_ids.append(assignment.volunteer_id)

    for booking in db.scalars(
        select(Booking).where(Booking.event_id == event_id, Booking.status == BookingStatus.confirmed)
    ):
        booking.status = BookingStatus.no_show

    honored_assignments = list(
        db.scalars(
            select(VolunteerAssignment).where(
                VolunteerAssignment.event_id == event_id,
                VolunteerAssignment.status == AssignmentStatus.accepted,
            )
        )
    )
    honored_volunteer_ids = [a.volunteer_id for a in honored_assignments]

    event.status = EventStatus.closed

    db.commit()
    db.refresh(autopsy)
    return autopsy, rated_volunteer_ids, honored_volunteer_ids


def list_pending_autopsies(db: DBSession, user: CurrentUser, *, city_id: int | None = None) -> list[Event]:
    """Events awaiting the lead's review — the door is closed but the autopsy (which is what
    actually closes the event out) hasn't been submitted yet. Computed, never a stored flag."""
    stmt = select(Event).where(
        Event.status == EventStatus.awaiting_review,
        ~Event.id.in_(select(EventAutopsy.event_id)),
    )
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(Event.city_id == user.city_id)
    elif user.role == StaffRole.event_lead:
        stmt = stmt.where(Event.lead_id == user.id)
    if city_id is not None:
        stmt = stmt.where(Event.city_id == city_id)
    return list(db.scalars(stmt.order_by(Event.starts_at.desc())))


def list_autopsies_for_venue(db: DBSession, venue_id: int, *, limit: int | None = None) -> list[EventAutopsy]:
    stmt = (
        select(EventAutopsy)
        .join(Event, EventAutopsy.event_id == Event.id)
        .where(Event.venue_id == venue_id)
        .order_by(EventAutopsy.submitted_at.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


# --- Decisions ---------------------------------------------------------


def get_decision(db: DBSession, decision_id: int) -> Decision:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFound
    return decision


def list_decisions(
    db: DBSession,
    *,
    city_id: int | None = None,
    venue_id: int | None = None,
    category: EventCategory | None = None,
    q: str | None = None,
) -> list[Decision]:
    stmt = select(Decision)
    if city_id is not None:
        stmt = stmt.where(Decision.city_id == city_id)
    if venue_id is not None:
        stmt = stmt.where(Decision.venue_id == venue_id)
    if category is not None:
        stmt = stmt.where(Decision.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Decision.title.ilike(like), Decision.body.ilike(like)))
    return list(db.scalars(stmt.order_by(Decision.decided_at.desc())))


def create_decision(
    db: DBSession,
    user: CurrentUser,
    *,
    title: str,
    body: str,
    city_id: int | None,
    venue_id: int | None,
    category: EventCategory | None,
    decided_at: date,
) -> Decision:
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    if user.role == StaffRole.city_lead and city_id is not None and city_id != user.city_id:
        raise Forbidden
    decision = Decision(
        title=title,
        body=body,
        author_id=user.id,
        city_id=city_id,
        venue_id=venue_id,
        category=category,
        decided_at=decided_at,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def update_decision(
    db: DBSession,
    user: CurrentUser,
    decision_id: int,
    *,
    title: str | None,
    body: str | None,
    city_id: int | None,
    venue_id: int | None,
    category: EventCategory | None,
    decided_at: date | None,
) -> Decision:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFound
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    if user.role == StaffRole.city_lead and decision.city_id is not None and decision.city_id != user.city_id:
        raise Forbidden
    if title is not None:
        decision.title = title
    if body is not None:
        decision.body = body
    if city_id is not None:
        decision.city_id = city_id
    if venue_id is not None:
        decision.venue_id = venue_id
    if category is not None:
        decision.category = category
    if decided_at is not None:
        decision.decided_at = decided_at
    db.commit()
    db.refresh(decision)
    return decision


# --- Issues -------------------------------------------------------------

_LEVEL_ORDER = [IssueLevel.event_lead, IssueLevel.city_lead, IssueLevel.founder]


def _issue_city_id(db: DBSession, issue: Issue) -> int | None:
    """Derives the city an issue belongs to via whichever tag it carries."""
    if issue.event_id is not None:
        event = db.get(Event, issue.event_id)
        if event is not None:
            return event.city_id
    if issue.venue_id is not None:
        venue = db.get(Venue, issue.venue_id)
        if venue is not None:
            return venue.city_id
    if issue.volunteer_id is not None:
        volunteer = db.get(Volunteer, issue.volunteer_id)
        if volunteer is not None:
            return volunteer.city_id
    return None


def _can_view_issue(db: DBSession, user: CurrentUser, issue: Issue) -> bool:
    if user.user_type == SessionRecipientType.volunteer:
        return issue.raised_by_type == RaisedByType.volunteer and issue.raised_by_id == user.id
    if user.role == StaffRole.founder:
        return True
    if issue.raised_by_type == RaisedByType.staff and issue.raised_by_id == user.id:
        return True
    if user.role == StaffRole.city_lead:
        return _issue_city_id(db, issue) == user.city_id
    if user.role == StaffRole.event_lead:
        if issue.current_level == IssueLevel.event_lead and issue.event_id is not None:
            event = db.get(Event, issue.event_id)
            return event is not None and event.lead_id == user.id
        return False
    return False


def _can_act_on_issue(db: DBSession, user: CurrentUser, issue: Issue) -> bool:
    """Escalate/resolve: whoever currently holds the issue's level, or above."""
    if user.user_type == SessionRecipientType.volunteer:
        return False
    if user.role == StaffRole.founder:
        return True
    if user.role == StaffRole.city_lead:
        if issue.current_level == IssueLevel.founder:
            return False
        city_id = _issue_city_id(db, issue)
        return city_id is None or city_id == user.city_id
    if user.role == StaffRole.event_lead:
        if issue.current_level != IssueLevel.event_lead or issue.event_id is None:
            return False
        event = db.get(Event, issue.event_id)
        return event is not None and event.lead_id == user.id
    return False


def get_issue(db: DBSession, user: CurrentUser, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise NotFound
    if not _can_view_issue(db, user, issue):
        raise Forbidden
    return issue


def list_issues(
    db: DBSession,
    user: CurrentUser,
    *,
    city_id: int | None = None,
    venue_id: int | None = None,
    event_id: int | None = None,
) -> list[Issue]:
    stmt = select(Issue)
    if venue_id is not None:
        stmt = stmt.where(Issue.venue_id == venue_id)
    if event_id is not None:
        stmt = stmt.where(Issue.event_id == event_id)
    issues = list(db.scalars(stmt.order_by(Issue.created_at.desc())))
    if user.user_type == SessionRecipientType.volunteer:
        issues = [i for i in issues if i.raised_by_type == RaisedByType.volunteer and i.raised_by_id == user.id]
    elif user.role != StaffRole.founder:
        issues = [i for i in issues if _can_view_issue(db, user, i)]
    if city_id is not None:
        issues = [i for i in issues if _issue_city_id(db, i) == city_id]
    return issues


def _notify_level_holders(db: DBSession, issue: Issue, *, title: str, body: str) -> None:
    level = issue.current_level
    recipients: list[Staff] = []
    if level == IssueLevel.event_lead and issue.event_id is not None:
        event = db.get(Event, issue.event_id)
        if event is not None:
            lead = db.get(Staff, event.lead_id)
            if lead is not None:
                recipients = [lead]
    if not recipients and level != IssueLevel.founder:
        city_id = _issue_city_id(db, issue)
        if city_id is not None:
            recipients = list(
                db.scalars(
                    select(Staff).where(
                        Staff.role == StaffRole.city_lead, Staff.city_id == city_id, Staff.active.is_(True)
                    )
                )
            )
    if not recipients:
        recipients = list(
            db.scalars(select(Staff).where(Staff.role == StaffRole.founder, Staff.active.is_(True)))
        )
    for staff in recipients:
        notifications_service.notify(
            db,
            recipient_type=NotificationRecipientType.staff,
            recipient_id=staff.id,
            title=title,
            body=body,
            action_type="issue",
            action_ref=issue.id,
        )


def create_issue(
    db: DBSession,
    user: CurrentUser,
    *,
    title: str,
    body: str,
    event_id: int | None,
    venue_id: int | None,
    volunteer_id: int | None,
) -> Issue:
    issue = Issue(
        title=title,
        body=body,
        raised_by_type=RaisedByType(user.user_type.value),
        raised_by_id=user.id,
        event_id=event_id,
        venue_id=venue_id,
        volunteer_id=volunteer_id,
    )
    db.add(issue)
    db.flush()
    _notify_level_holders(db, issue, title=f"New issue: {title}", body=body)
    db.commit()
    db.refresh(issue)
    return issue


def escalate_issue(db: DBSession, user: CurrentUser, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise NotFound
    if issue.status != IssueStatus.open:
        raise InvalidTransition
    idx = _LEVEL_ORDER.index(issue.current_level)
    if idx == len(_LEVEL_ORDER) - 1:
        raise InvalidTransition
    if not _can_act_on_issue(db, user, issue):
        raise Forbidden
    issue.current_level = _LEVEL_ORDER[idx + 1]
    _notify_level_holders(db, issue, title=f"Issue escalated: {issue.title}", body=issue.body)
    db.commit()
    db.refresh(issue)
    return issue


def resolve_issue(db: DBSession, user: CurrentUser, issue_id: int, *, resolution_note: str) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise NotFound
    if issue.status != IssueStatus.open:
        raise InvalidTransition
    if not _can_act_on_issue(db, user, issue):
        raise Forbidden
    issue.status = IssueStatus.resolved
    issue.resolution_note = resolution_note
    issue.resolved_by = user.id
    issue.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(issue)
    return issue


def count_recent_issues(
    db: DBSession, *, venue_id: int | None = None, volunteer_id: int | None = None, days: int = 60
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(func.count()).select_from(Issue).where(Issue.created_at >= cutoff)
    if venue_id is not None:
        stmt = stmt.where(Issue.venue_id == venue_id)
    if volunteer_id is not None:
        stmt = stmt.where(Issue.volunteer_id == volunteer_id)
    return db.scalar(stmt) or 0
