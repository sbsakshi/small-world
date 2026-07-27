from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.jobs import tasks as job_tasks
from app.modules.contacts import service
from app.modules.contacts.schemas import (
    BookingOut,
    ContactOut,
    ContactUpdate,
    CsvImportResult,
    CsvImportRow,
    DoorRosterEntry,
    ManualBookingCreate,
)
from app.modules.events import service as events_service
from app.modules.events.schemas import EventOut
from app.modules.org.deps import get_current_user, require_staff
from app.modules.org.schemas import CurrentUser

router = APIRouter()


@router.get("/contacts", response_model=list[ContactOut], tags=["contacts"], dependencies=[Depends(require_staff)])
def list_contacts(city_id: int | None = None, db: DBSession = Depends(get_db)) -> list[ContactOut]:
    return service.list_contacts(db, city_id=city_id)


@router.get(
    "/contacts/{contact_id}", response_model=ContactOut, tags=["contacts"], dependencies=[Depends(require_staff)]
)
def get_contact(contact_id: int, db: DBSession = Depends(get_db)) -> ContactOut:
    try:
        return service.get_contact(db, contact_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")


@router.patch(
    "/contacts/{contact_id}", response_model=ContactOut, tags=["contacts"], dependencies=[Depends(require_staff)]
)
def update_contact(contact_id: int, payload: ContactUpdate, db: DBSession = Depends(get_db)) -> ContactOut:
    try:
        return service.update_contact(db, contact_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")


@router.get("/bookings", response_model=list[BookingOut], tags=["bookings"])
def list_bookings(
    event_id: int | None = None,
    contact_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[BookingOut]:
    try:
        return service.list_bookings_for(db, user, event_id=event_id, contact_id=contact_id)
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A volunteer must scope this to one of their events")


@router.post(
    "/bookings/manual", response_model=BookingOut, tags=["bookings"], dependencies=[Depends(require_staff)]
)
def create_manual_booking(payload: ManualBookingCreate, db: DBSession = Depends(get_db)) -> BookingOut:
    try:
        return service.create_manual_booking(db, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.InvalidPhone:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid phone number")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Event is not open for bookings")


@router.get("/events/{event_id}/door-roster", response_model=list[DoorRosterEntry], tags=["bookings"])
def door_roster(
    event_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[DoorRosterEntry]:
    try:
        return service.list_door_roster(db, user, event_id=event_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this event's door roster")


@router.post("/events/{event_id}/checkin/{booking_id}", response_model=BookingOut, tags=["bookings"])
def check_in_booking(
    event_id: int,
    booking_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> BookingOut:
    try:
        return service.check_in_booking(db, user, event_id=event_id, booking_id=booking_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found for this event")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot check people in at this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only confirmed bookings can be checked in")


@router.post("/events/{event_id}/close-door", response_model=EventOut, tags=["bookings"])
def close_door(
    event_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> EventOut:
    try:
        event = events_service.close_door(db, user, event_id)
    except events_service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except events_service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot close the door on this event")
    except events_service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a published or started event can be closed")
    job_tasks.cancel_no_show_sweep(event.id)
    job_tasks.schedule_autopsy_prompt(event.id)
    job_tasks.schedule_autopsy_reminder(event.id)
    return event


@router.post(
    "/events/{event_id}/bookings/import",
    response_model=CsvImportResult,
    tags=["bookings"],
    dependencies=[Depends(require_staff)],
)
async def import_csv(event_id: int, file: UploadFile = File(...), db: DBSession = Depends(get_db)) -> CsvImportResult:
    try:
        content = await file.read()
        created, skipped, errors = service.import_csv(db, event_id=event_id, content=content)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return CsvImportResult(
        created=created,
        skipped_duplicate=skipped,
        errors=[CsvImportRow(row=r, error=e) for r, e in errors],
    )
