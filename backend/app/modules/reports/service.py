from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.modules.events.models import Event, EventStatus
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.reports.models import (
    Decision,
    DecisionStatus,
    EventReport,
    Issue,
    IssuePriority,
    IssueStatus,
)


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidTransition(Exception):
    pass


class AlreadyExists(Exception):
    pass


def _ensure_city_access(user: CurrentUser, city_id: int) -> None:
    if user.role != StaffRole.founder and city_id != user.city_id:
        raise Forbidden


# --- Decisions ---------------------------------------------------------


def list_decisions(db: DBSession, user: CurrentUser, *, city_id: int | None = None) -> list[Decision]:
    stmt = select(Decision)
    if user.role != StaffRole.founder:
        stmt = stmt.where(Decision.city_id == user.city_id)
    if city_id is not None:
        stmt = stmt.where(Decision.city_id == city_id)
    if user.role == StaffRole.event_lead:
        stmt = stmt.where(Decision.staff_only.is_(False))
    return list(db.scalars(stmt.order_by(Decision.created_at.desc())))


def get_decision(db: DBSession, user: CurrentUser, decision_id: int) -> Decision:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFound
    _ensure_city_access(user, decision.city_id)
    if user.role == StaffRole.event_lead and decision.staff_only:
        raise Forbidden
    return decision


def create_decision(
    db: DBSession,
    user: CurrentUser,
    *,
    city_id: int,
    venue_id: int | None,
    text: str,
    note: str | None,
    staff_only: bool,
) -> Decision:
    _ensure_city_access(user, city_id)
    decision = Decision(
        city_id=city_id,
        venue_id=venue_id,
        text=text,
        note=note,
        staff_only=staff_only,
        raised_by_id=user.id,
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
    text: str | None,
    note: str | None,
    staff_only: bool | None,
) -> Decision:
    decision = get_decision(db, user, decision_id)
    if text is not None:
        decision.text = text
    if note is not None:
        decision.note = note
    if staff_only is not None:
        decision.staff_only = staff_only
    db.commit()
    db.refresh(decision)
    return decision


def decide_decision(db: DBSession, user: CurrentUser, decision_id: int) -> Decision:
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    decision = get_decision(db, user, decision_id)
    if decision.status != DecisionStatus.open:
        raise InvalidTransition
    decision.status = DecisionStatus.decided
    decision.decided_by_id = user.id
    db.commit()
    db.refresh(decision)
    return decision


# --- Issues -------------------------------------------------------------


def list_issues(db: DBSession, user: CurrentUser, *, city_id: int | None = None) -> list[Issue]:
    stmt = select(Issue)
    if user.role != StaffRole.founder:
        stmt = stmt.where(Issue.city_id == user.city_id)
    if city_id is not None:
        stmt = stmt.where(Issue.city_id == city_id)
    return list(db.scalars(stmt.order_by(Issue.created_at.desc())))


def get_issue(db: DBSession, user: CurrentUser, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise NotFound
    _ensure_city_access(user, issue.city_id)
    return issue


def create_issue(
    db: DBSession,
    user: CurrentUser,
    *,
    city_id: int,
    venue_id: int | None,
    text: str,
    priority: IssuePriority,
    due_date: date | None,
) -> Issue:
    _ensure_city_access(user, city_id)
    issue = Issue(
        city_id=city_id,
        venue_id=venue_id,
        text=text,
        priority=priority,
        due_date=due_date,
        raised_by_id=user.id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def update_issue(
    db: DBSession,
    user: CurrentUser,
    issue_id: int,
    *,
    text: str | None,
    priority: IssuePriority | None,
    due_date: date | None,
) -> Issue:
    issue = get_issue(db, user, issue_id)
    if text is not None:
        issue.text = text
    if priority is not None:
        issue.priority = priority
    if due_date is not None:
        issue.due_date = due_date
    db.commit()
    db.refresh(issue)
    return issue


def resolve_issue(db: DBSession, user: CurrentUser, issue_id: int) -> Issue:
    if user.role not in (StaffRole.founder, StaffRole.city_lead):
        raise Forbidden
    issue = get_issue(db, user, issue_id)
    if issue.status != IssueStatus.open:
        raise InvalidTransition
    issue.status = IssueStatus.resolved
    issue.resolved_by_id = user.id
    issue.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(issue)
    return issue


# --- Event reports --------------------------------------------------------


def _ensure_event_access(user: CurrentUser, event: Event) -> None:
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


def _get_event(db: DBSession, user: CurrentUser, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    _ensure_event_access(user, event)
    return event


def get_report(db: DBSession, user: CurrentUser, event_id: int) -> EventReport:
    _get_event(db, user, event_id)
    report = db.scalar(select(EventReport).where(EventReport.event_id == event_id))
    if report is None:
        raise NotFound
    return report


def create_report(
    db: DBSession, user: CurrentUser, event_id: int, *, note: str, tags: list[dict] | None
) -> EventReport:
    event = _get_event(db, user, event_id)
    if event.status != EventStatus.completed:
        raise InvalidTransition
    if db.scalar(select(EventReport).where(EventReport.event_id == event_id)) is not None:
        raise AlreadyExists
    report = EventReport(event_id=event_id, note=note, tags=tags, created_by_id=user.id)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def update_report(
    db: DBSession, user: CurrentUser, event_id: int, *, note: str | None, tags: list[dict] | None
) -> EventReport:
    _get_event(db, user, event_id)
    report = db.scalar(select(EventReport).where(EventReport.event_id == event_id))
    if report is None:
        raise NotFound
    if note is not None:
        report.note = note
    if tags is not None:
        report.tags = tags
    db.commit()
    db.refresh(report)
    return report
