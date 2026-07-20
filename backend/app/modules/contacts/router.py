from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.modules.contacts import service
from app.modules.contacts.schemas import (
    BookingOut,
    ContactOut,
    ContactUpdate,
    CsvImportResult,
    CsvImportRow,
    ManualBookingCreate,
)
from app.modules.org.deps import require_staff

router = APIRouter(dependencies=[Depends(require_staff)])


@router.get("/contacts", response_model=list[ContactOut], tags=["contacts"])
def list_contacts(city_id: int | None = None, db: DBSession = Depends(get_db)) -> list[ContactOut]:
    return service.list_contacts(db, city_id=city_id)


@router.get("/contacts/{contact_id}", response_model=ContactOut, tags=["contacts"])
def get_contact(contact_id: int, db: DBSession = Depends(get_db)) -> ContactOut:
    try:
        return service.get_contact(db, contact_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")


@router.patch("/contacts/{contact_id}", response_model=ContactOut, tags=["contacts"])
def update_contact(contact_id: int, payload: ContactUpdate, db: DBSession = Depends(get_db)) -> ContactOut:
    try:
        return service.update_contact(db, contact_id, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")


@router.get("/bookings", response_model=list[BookingOut], tags=["bookings"])
def list_bookings(
    event_id: int | None = None, contact_id: int | None = None, db: DBSession = Depends(get_db)
) -> list[BookingOut]:
    return service.list_bookings(db, event_id=event_id, contact_id=contact_id)


@router.post("/bookings/manual", response_model=BookingOut, tags=["bookings"])
def create_manual_booking(payload: ManualBookingCreate, db: DBSession = Depends(get_db)) -> BookingOut:
    try:
        return service.create_manual_booking(db, **payload.model_dump())
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except service.InvalidPhone:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid phone number")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Event is not open for bookings")


@router.post("/events/{event_id}/checkin/{booking_id}", response_model=BookingOut, tags=["bookings"])
def check_in_booking(event_id: int, booking_id: int, db: DBSession = Depends(get_db)) -> BookingOut:
    try:
        return service.check_in_booking(db, event_id=event_id, booking_id=booking_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found for this event")
    except service.InvalidTransition:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only confirmed bookings can be checked in")


@router.post("/events/{event_id}/bookings/import", response_model=CsvImportResult, tags=["bookings"])
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
