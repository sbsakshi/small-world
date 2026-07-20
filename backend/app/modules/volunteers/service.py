from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.security import hash_password, verify_password
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers.models import (
    AssignmentStatus,
    Volunteer,
    VolunteerAssignment,
    VolunteerDateOverride,
    VolunteerWeeklyAvailability,
)


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidTransition(Exception):
    pass


def _ensure_city_access(user: CurrentUser, city_id: int) -> None:
    if user.role == StaffRole.city_lead and city_id != user.city_id:
        raise Forbidden


def authenticate_volunteer(db: DBSession, login_identifier: str, password: str) -> Volunteer | None:
    volunteer = db.scalar(
        select(Volunteer).where(
            Volunteer.login_identifier == login_identifier, Volunteer.active.is_(True)
        )
    )
    if volunteer is None or not verify_password(password, volunteer.password_hash):
        return None
    return volunteer


def get_active_volunteer(db: DBSession, volunteer_id: int) -> Volunteer | None:
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None or not volunteer.active:
        return None
    return volunteer


def create_volunteer(
    db: DBSession,
    *,
    name: str,
    phone: str,
    email: str | None,
    login_identifier: str,
    password: str,
    city_id: int,
    skills: list,
) -> Volunteer:
    volunteer = Volunteer(
        name=name,
        phone=phone,
        email=email,
        login_identifier=login_identifier,
        password_hash=hash_password(password),
        city_id=city_id,
        skills=skills,
    )
    db.add(volunteer)
    db.commit()
    db.refresh(volunteer)
    return volunteer


# --- Staff-facing volunteer roster ---


def list_volunteers(db: DBSession, user: CurrentUser, *, city_id: int | None = None) -> list[Volunteer]:
    stmt = select(Volunteer)
    if user.role == StaffRole.city_lead:
        stmt = stmt.where(Volunteer.city_id == user.city_id)
    elif city_id is not None:
        stmt = stmt.where(Volunteer.city_id == city_id)
    return list(db.scalars(stmt))


def get_volunteer(db: DBSession, volunteer_id: int) -> Volunteer:
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise NotFound
    return volunteer


def create_volunteer_scoped(
    db: DBSession,
    user: CurrentUser,
    *,
    name: str,
    phone: str,
    email: str | None,
    login_identifier: str,
    password: str,
    city_id: int,
    skills: list,
) -> Volunteer:
    _ensure_city_access(user, city_id)
    return create_volunteer(
        db,
        name=name,
        phone=phone,
        email=email,
        login_identifier=login_identifier,
        password=password,
        city_id=city_id,
        skills=skills,
    )


def update_volunteer(
    db: DBSession,
    user: CurrentUser,
    volunteer_id: int,
    *,
    name: str | None,
    phone: str | None,
    email: str | None,
    skills: list | None,
    remarks: str | None,
    active: bool | None,
) -> Volunteer:
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise NotFound
    _ensure_city_access(user, volunteer.city_id)
    if name is not None:
        volunteer.name = name
    if phone is not None:
        volunteer.phone = phone
    if email is not None:
        volunteer.email = email
    if skills is not None:
        volunteer.skills = skills
    if remarks is not None:
        volunteer.remarks = remarks
    if active is not None:
        volunteer.active = active
    db.commit()
    db.refresh(volunteer)
    return volunteer


# --- Availability: volunteers manage their own; staff can view via get_volunteer's relations. ---


def set_weekly_availability(db: DBSession, volunteer_id: int, days: list[int]) -> list[int]:
    """Full replacement: deletes the existing weekly pattern and inserts the given weekdays."""
    for row in db.scalars(
        select(VolunteerWeeklyAvailability).where(VolunteerWeeklyAvailability.volunteer_id == volunteer_id)
    ):
        db.delete(row)
    for day in sorted(set(days)):
        db.add(VolunteerWeeklyAvailability(volunteer_id=volunteer_id, day_of_week=day))
    db.commit()
    return sorted(set(days))


def get_weekly_availability(db: DBSession, volunteer_id: int) -> list[int]:
    rows = db.scalars(
        select(VolunteerWeeklyAvailability).where(VolunteerWeeklyAvailability.volunteer_id == volunteer_id)
    )
    return sorted(row.day_of_week for row in rows)


def set_date_override(db: DBSession, volunteer_id: int, *, on_date: date, available: bool) -> VolunteerDateOverride:
    existing = db.scalar(
        select(VolunteerDateOverride).where(
            VolunteerDateOverride.volunteer_id == volunteer_id, VolunteerDateOverride.date == on_date
        )
    )
    if existing is not None:
        existing.available = available
        db.commit()
        db.refresh(existing)
        return existing
    override = VolunteerDateOverride(volunteer_id=volunteer_id, date=on_date, available=available)
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def list_date_overrides(db: DBSession, volunteer_id: int) -> list[VolunteerDateOverride]:
    return list(
        db.scalars(select(VolunteerDateOverride).where(VolunteerDateOverride.volunteer_id == volunteer_id))
    )


# --- Assignments: staff assign volunteers to events; volunteers accept/decline. ---


def create_assignment(
    db: DBSession,
    user: CurrentUser,
    *,
    event_id: int,
    volunteer_id: int,
    coordinator_note: str | None,
) -> VolunteerAssignment:
    from app.modules.events.models import Event

    event = db.get(Event, event_id)
    if event is None:
        raise NotFound
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise NotFound
    _ensure_city_access(user, event.city_id)
    assignment = VolunteerAssignment(
        event_id=event_id,
        volunteer_id=volunteer_id,
        assigned_by=user.id,
        coordinator_note=coordinator_note,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_assignments(
    db: DBSession, *, event_id: int | None = None, volunteer_id: int | None = None
) -> list[VolunteerAssignment]:
    stmt = select(VolunteerAssignment)
    if event_id is not None:
        stmt = stmt.where(VolunteerAssignment.event_id == event_id)
    if volunteer_id is not None:
        stmt = stmt.where(VolunteerAssignment.volunteer_id == volunteer_id)
    return list(db.scalars(stmt))


def respond_to_assignment(
    db: DBSession, volunteer_id: int, assignment_id: int, *, accept: bool
) -> VolunteerAssignment:
    assignment = db.get(VolunteerAssignment, assignment_id)
    if assignment is None or assignment.volunteer_id != volunteer_id:
        raise NotFound
    if assignment.status != AssignmentStatus.pending:
        raise InvalidTransition
    assignment.status = AssignmentStatus.accepted if accept else AssignmentStatus.declined
    assignment.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment


def mark_events_done(db: DBSession, volunteer_ids: list[int]) -> None:
    """Increments events_done for each accepted volunteer once their event is closed out."""
    for volunteer_id in volunteer_ids:
        volunteer = db.get(Volunteer, volunteer_id)
        if volunteer is not None:
            volunteer.events_done += 1
    db.commit()


def expire_assignment(db: DBSession, assignment_id: int) -> VolunteerAssignment | None:
    """Used by the escalation job: pending assignments older than the response window expire."""
    assignment = db.get(VolunteerAssignment, assignment_id)
    if assignment is None or assignment.status != AssignmentStatus.pending:
        return None
    assignment.status = AssignmentStatus.expired
    assignment.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment
