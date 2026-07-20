from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.modules.org.deps import require_staff
from app.modules.org.schemas import CurrentUser
from app.modules.reports import service
from app.modules.reports.schemas import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    EventReportCreate,
    EventReportOut,
    EventReportUpdate,
    IssueCreate,
    IssueOut,
    IssueUpdate,
)

router = APIRouter(tags=["reports"], dependencies=[Depends(require_staff)])


# --- Decisions ---------------------------------------------------------


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(
    city_id: int | None = None, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> list[DecisionOut]:
    return service.list_decisions(db, user, city_id=city_id)


@router.get("/decisions/{decision_id}", response_model=DecisionOut)
def get_decision(
    decision_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> DecisionOut:
    try:
        return service.get_decision(db, user, decision_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this decision")


@router.post("/decisions", response_model=DecisionOut)
def create_decision(
    payload: DecisionCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> DecisionOut:
    try:
        return service.create_decision(db, user, **payload.model_dump())
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot raise a decision in this city")


@router.patch("/decisions/{decision_id}", response_model=DecisionOut)
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


@router.post("/decisions/{decision_id}/decide", response_model=DecisionOut)
def decide_decision(
    decision_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> DecisionOut:
    try:
        return service.decide_decision(db, user, decision_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot decide this decision")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Decision is already decided")


# --- Issues -------------------------------------------------------------


@router.get("/issues", response_model=list[IssueOut])
def list_issues(
    city_id: int | None = None, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> list[IssueOut]:
    return service.list_issues(db, user, city_id=city_id)


@router.get("/issues/{issue_id}", response_model=IssueOut)
def get_issue(
    issue_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> IssueOut:
    try:
        return service.get_issue(db, user, issue_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this issue")


@router.post("/issues", response_model=IssueOut)
def create_issue(
    payload: IssueCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> IssueOut:
    try:
        return service.create_issue(db, user, **payload.model_dump())
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot raise an issue in this city")


@router.patch("/issues/{issue_id}", response_model=IssueOut)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> IssueOut:
    try:
        return service.update_issue(db, user, issue_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this issue")


@router.post("/issues/{issue_id}/resolve", response_model=IssueOut)
def resolve_issue(
    issue_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> IssueOut:
    try:
        return service.resolve_issue(db, user, issue_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot resolve this issue")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Issue is already resolved")


# --- Event reports --------------------------------------------------------


@router.get("/events/{event_id}/report", response_model=EventReportOut)
def get_report(
    event_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventReportOut:
    try:
        return service.get_report(db, user, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No report for this event")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this event's report")


@router.post("/events/{event_id}/report", response_model=EventReportOut)
def create_report(
    event_id: int,
    payload: EventReportCreate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> EventReportOut:
    try:
        return service.create_report(
            db, user, event_id, note=payload.note, tags=[t.model_dump() for t in payload.tags] if payload.tags else None
        )
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot report on this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only completed events can be reported on")
    except service.AlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "This event already has a report")


@router.patch("/events/{event_id}/report", response_model=EventReportOut)
def update_report(
    event_id: int,
    payload: EventReportUpdate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> EventReportOut:
    try:
        return service.update_report(
            db, user, event_id, note=payload.note, tags=[t.model_dump() for t in payload.tags] if payload.tags else None
        )
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No report for this event")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this event's report")
