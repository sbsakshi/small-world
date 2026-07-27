from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.contacts.models import BookingSource, BookingStatus


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str
    email: str | None
    city_id: int | None
    opted_out: bool


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    city_id: int | None = None
    opted_out: bool | None = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    event_id: int
    status: BookingStatus
    source: BookingSource
    amount: int
    external_id: str | None
    created_at: datetime


class DoorRosterEntry(BaseModel):
    booking_id: int
    name: str
    phone: str
    status: BookingStatus


class ManualBookingCreate(BaseModel):
    event_id: int
    phone: str
    name: str
    email: str | None = None
    amount: int = 0


class CsvImportRow(BaseModel):
    row: int
    error: str


class CsvImportResult(BaseModel):
    created: int
    skipped_duplicate: int
    errors: list[CsvImportRow]
