from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.jobs import tasks as job_tasks
from app.modules.notifications import service as notifications_service
from app.modules.notifications.models import NotificationRecipientType
from app.modules.org.deps import require_staff, require_volunteer
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers import service
from app.modules.volunteers.schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentRespond,
    DateOverrideOut,
    DateOverrideSet,
    VolunteerCreate,
    VolunteerOut,
    VolunteerUpdate,
    WeeklyAvailabilityOut,
    WeeklyAvailabilitySet,
)

router = APIRouter()

# --- Staff-facing roster + assignment management ---

staff_router = APIRouter(prefix="/volunteers", tags=["volunteers"], dependencies=[Depends(require_staff)])


@staff_router.get("", response_model=list[VolunteerOut])
def list_volunteers(
    city_id: int | None = None, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> list[VolunteerOut]:
    return service.list_volunteers(db, user, city_id=city_id)


@staff_router.get("/{volunteer_id}", response_model=VolunteerOut)
def get_volunteer(volunteer_id: int, db: DBSession = Depends(get_db)) -> VolunteerOut:
    try:
        return service.get_volunteer(db, volunteer_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Volunteer not found")


@staff_router.post("", response_model=VolunteerOut)
def create_volunteer(
    payload: VolunteerCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> VolunteerOut:
    try:
        return service.create_volunteer_scoped(db, user, **payload.model_dump())
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create a volunteer outside your city")


@staff_router.patch("/{volunteer_id}", response_model=VolunteerOut)
def update_volunteer(
    volunteer_id: int,
    payload: VolunteerUpdate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> VolunteerOut:
    try:
        return service.update_volunteer(db, user, volunteer_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Volunteer not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit a volunteer outside your city")


@staff_router.get("/{volunteer_id}/availability/weekly", response_model=WeeklyAvailabilityOut)
def get_weekly_availability(volunteer_id: int, db: DBSession = Depends(get_db)) -> WeeklyAvailabilityOut:
    return WeeklyAvailabilityOut(days=service.get_weekly_availability(db, volunteer_id))


@staff_router.get("/{volunteer_id}/availability/overrides", response_model=list[DateOverrideOut])
def list_date_overrides(volunteer_id: int, db: DBSession = Depends(get_db)) -> list[DateOverrideOut]:
    return service.list_date_overrides(db, volunteer_id)


assignments_router = APIRouter(prefix="/assignments", tags=["assignments"])


@assignments_router.get("", response_model=list[AssignmentOut], dependencies=[Depends(require_staff)])
def list_assignments(
    event_id: int | None = None, volunteer_id: int | None = None, db: DBSession = Depends(get_db)
) -> list[AssignmentOut]:
    return service.list_assignments(db, event_id=event_id, volunteer_id=volunteer_id)


@assignments_router.post("", response_model=AssignmentOut, dependencies=[Depends(require_staff)])
def create_assignment(
    payload: AssignmentCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> AssignmentOut:
    try:
        assignment = service.create_assignment(db, user, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event or volunteer not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign volunteers outside your city")
    job_tasks.schedule_assignment_expiry(assignment.id)
    notifications_service.notify(
        db,
        recipient_type=NotificationRecipientType.volunteer,
        recipient_id=assignment.volunteer_id,
        title="You've been assigned to a shift",
        body=assignment.coordinator_note or "Check your assignments to accept or decline.",
        action_type="assignment_created",
        action_ref=assignment.id,
    )
    return assignment


@assignments_router.post("/{assignment_id}/respond", response_model=AssignmentOut)
def respond_to_assignment(
    assignment_id: int,
    payload: AssignmentRespond,
    user: CurrentUser = Depends(require_volunteer),
    db: DBSession = Depends(get_db),
) -> AssignmentOut:
    try:
        assignment = service.respond_to_assignment(db, user.id, assignment_id, accept=payload.accept)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Assignment already responded to")
    job_tasks.cancel_assignment_expiry(assignment.id)
    job_tasks.schedule_score_recalc(assignment.volunteer_id)
    if not payload.accept:
        notifications_service.notify(
            db,
            recipient_type=NotificationRecipientType.staff,
            recipient_id=assignment.assigned_by,
            title="Assignment declined",
            body="A volunteer declined their assignment — you may need to find a replacement.",
            action_type="assignment_declined",
            action_ref=assignment.id,
        )
    return assignment


# --- Volunteer self-service ---

me_router = APIRouter(prefix="/volunteers/me", tags=["volunteer-self"], dependencies=[Depends(require_volunteer)])


@me_router.get("/assignments", response_model=list[AssignmentOut])
def my_assignments(user: CurrentUser = Depends(require_volunteer), db: DBSession = Depends(get_db)) -> list[AssignmentOut]:
    return service.list_assignments(db, volunteer_id=user.id)


@me_router.get("/availability/weekly", response_model=WeeklyAvailabilityOut)
def my_weekly_availability(user: CurrentUser = Depends(require_volunteer), db: DBSession = Depends(get_db)) -> WeeklyAvailabilityOut:
    return WeeklyAvailabilityOut(days=service.get_weekly_availability(db, user.id))


@me_router.put("/availability/weekly", response_model=WeeklyAvailabilityOut)
def set_my_weekly_availability(
    payload: WeeklyAvailabilitySet, user: CurrentUser = Depends(require_volunteer), db: DBSession = Depends(get_db)
) -> WeeklyAvailabilityOut:
    return WeeklyAvailabilityOut(days=service.set_weekly_availability(db, user.id, payload.days))


@me_router.get("/availability/overrides", response_model=list[DateOverrideOut])
def my_date_overrides(user: CurrentUser = Depends(require_volunteer), db: DBSession = Depends(get_db)) -> list[DateOverrideOut]:
    return service.list_date_overrides(db, user.id)


@me_router.put("/availability/overrides", response_model=DateOverrideOut)
def set_my_date_override(
    payload: DateOverrideSet, user: CurrentUser = Depends(require_volunteer), db: DBSession = Depends(get_db)
) -> DateOverrideOut:
    return service.set_date_override(db, user.id, on_date=payload.date, available=payload.available)


router.include_router(staff_router)
router.include_router(assignments_router)
router.include_router(me_router)
