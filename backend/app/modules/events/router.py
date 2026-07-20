from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.jobs import tasks as job_tasks
from app.modules.events import service
from app.modules.events.models import EventStatus
from app.modules.events.schemas import EventCreate, EventDuplicate, EventOut, EventUpdate
from app.modules.org.deps import require_staff
from app.modules.org.schemas import CurrentUser
from app.modules.volunteers import service as volunteers_service
from app.modules.volunteers.models import AssignmentStatus

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(require_staff)])


@router.get("", response_model=list[EventOut])
def list_events(
    city_id: int | None = None,
    venue_id: int | None = None,
    status_: EventStatus | None = None,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> list[EventOut]:
    return service.list_events(db, user, city_id=city_id, venue_id=venue_id, status=status_)


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventOut:
    try:
        return service.get_event(db, user, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this event")


@router.post("", response_model=EventOut)
def create_event(
    payload: EventCreate, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventOut:
    try:
        return service.create_event(db, user, **payload.model_dump())
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create an event in this city")


@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    payload: EventUpdate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> EventOut:
    try:
        return service.update_event(db, user, event_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Event is no longer editable")


@router.post("/{event_id}/publish", response_model=EventOut)
def publish_event(
    event_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventOut:
    try:
        event = service.publish_event(db, user, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot publish this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft events can be published")
    job_tasks.schedule_no_show_sweep(event.id, event.starts_at)
    return event


@router.post("/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventOut:
    try:
        event = service.cancel_event(db, user, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot cancel this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Event is already finalized")
    job_tasks.cancel_no_show_sweep(event.id)
    return event


@router.post("/{event_id}/complete", response_model=EventOut)
def complete_event(
    event_id: int, user: CurrentUser = Depends(require_staff), db: DBSession = Depends(get_db)
) -> EventOut:
    try:
        event = service.complete_event(db, user, event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot close out this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only published events can be completed")
    job_tasks.cancel_no_show_sweep(event.id)
    accepted = volunteers_service.list_assignments(db, event_id=event.id)
    honored_ids = [a.volunteer_id for a in accepted if a.status == AssignmentStatus.accepted]
    if honored_ids:
        volunteers_service.mark_events_done(db, honored_ids)
        for volunteer_id in honored_ids:
            job_tasks.schedule_score_recalc(volunteer_id)
    return event


@router.post("/{event_id}/duplicate", response_model=EventOut)
def duplicate_event(
    event_id: int,
    payload: EventDuplicate,
    user: CurrentUser = Depends(require_staff),
    db: DBSession = Depends(get_db),
) -> EventOut:
    try:
        return service.duplicate_event(db, user, event_id, starts_at=payload.starts_at)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot duplicate this event")
