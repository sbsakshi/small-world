from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.jobs import tasks as job_tasks
from app.modules.events.models import EventCategory
from app.modules.knowledge import service
from app.modules.knowledge.schemas import (
    AutopsyCreate,
    AutopsyOut,
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    IssueCreate,
    IssueOut,
    IssueResolve,
    PatternCountOut,
    PendingAutopsyEventOut,
)
from app.modules.org.deps import get_current_user, require_staff
from app.modules.org.schemas import CurrentUser

router = APIRouter(tags=["knowledge"])

staff_router = APIRouter(dependencies=[Depends(require_staff)])


# --- Event autopsies ------------------------------------------------------


@staff_router.get("/events/{event_id}/autopsy", response_model=AutopsyOut)
def get_autopsy(event_id: int, db: DBSession = Depends(get_db)) -> AutopsyOut:
    try:
        return service.get_autopsy(db, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No autopsy for this event")


@staff_router.post("/events/{event_id}/autopsy", response_model=AutopsyOut)
def submit_autopsy(
    event_id: int,
    payload: AutopsyCreate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> AutopsyOut:
    try:
        autopsy, rated_volunteer_ids = service.submit_autopsy(
            db,
            user,
            event_id,
            attendance_actual=payload.attendance_actual,
            venue_rating=payload.venue_rating,
            what_worked=payload.what_worked,
            what_didnt=payload.what_didnt,
            volunteer_ratings=payload.volunteer_ratings,
        )
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event or assignment not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot submit an autopsy for this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only completed events can have an autopsy")
    except service.AlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "This event already has an autopsy")
    job_tasks.cancel_autopsy_reminder(event_id)
    for volunteer_id in set(rated_volunteer_ids):
        job_tasks.schedule_score_recalc(volunteer_id)
    return autopsy


@staff_router.get("/venues/{venue_id}/autopsies", response_model=list[AutopsyOut])
def list_venue_autopsies(
    venue_id: int, limit: int | None = None, db: DBSession = Depends(get_db)
) -> list[AutopsyOut]:
    return service.list_autopsies_for_venue(db, venue_id, limit=limit)


@staff_router.get("/autopsies/pending", response_model=list[PendingAutopsyEventOut])
def list_pending_autopsies(
    city_id: int | None = None, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> list[PendingAutopsyEventOut]:
    return service.list_pending_autopsies(db, user, city_id=city_id)


# --- Decisions ---------------------------------------------------------


@staff_router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(
    city_id: int | None = None,
    venue_id: int | None = None,
    category: EventCategory | None = None,
    q: str | None = None,
    db: DBSession = Depends(get_db),
) -> list[DecisionOut]:
    return service.list_decisions(db, city_id=city_id, venue_id=venue_id, category=category, q=q)


@staff_router.get("/decisions/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: int, db: DBSession = Depends(get_db)) -> DecisionOut:
    try:
        return service.get_decision(db, decision_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")


@staff_router.post("/decisions", response_model=DecisionOut)
def create_decision(
    payload: DecisionCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> DecisionOut:
    try:
        return service.create_decision(db, user, **payload.model_dump())
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot raise a decision in this city")


@staff_router.patch("/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(
    decision_id: int,
    payload: DecisionUpdate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> DecisionOut:
    try:
        return service.update_decision(db, user, decision_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this decision")


# --- Issues -------------------------------------------------------------


@router.get("/issues", response_model=list[IssueOut], tags=["knowledge"])
def list_issues(
    city_id: int | None = None,
    venue_id: int | None = None,
    event_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[IssueOut]:
    return service.list_issues(db, user, city_id=city_id, venue_id=venue_id, event_id=event_id)


@router.get("/issues/pattern-count", response_model=PatternCountOut, tags=["knowledge"])
def issue_pattern_count(
    venue_id: int | None = None,
    volunteer_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PatternCountOut:
    return PatternCountOut(count=service.count_recent_issues(db, venue_id=venue_id, volunteer_id=volunteer_id))


@router.get("/issues/{issue_id}", response_model=IssueOut, tags=["knowledge"])
def get_issue(
    issue_id: int, user: CurrentUser = Depends(get_current_user), db: DBSession = Depends(get_db)
) -> IssueOut:
    try:
        return service.get_issue(db, user, issue_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this issue")


@router.post("/issues", response_model=IssueOut, tags=["knowledge"])
def create_issue(
    payload: IssueCreate, user: CurrentUser = Depends(get_current_user), db: DBSession = Depends(get_db)
) -> IssueOut:
    return service.create_issue(db, user, **payload.model_dump())


@router.post("/issues/{issue_id}/escalate", response_model=IssueOut, tags=["knowledge"])
def escalate_issue(
    issue_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> IssueOut:
    try:
        return service.escalate_issue(db, user, issue_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot escalate this issue")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Issue cannot be escalated further")


@router.post("/issues/{issue_id}/resolve", response_model=IssueOut, tags=["knowledge"])
def resolve_issue(
    issue_id: int,
    payload: IssueResolve,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> IssueOut:
    try:
        return service.resolve_issue(db, user, issue_id, resolution_note=payload.resolution_note)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot resolve this issue")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Issue is already resolved")


router.include_router(staff_router)
