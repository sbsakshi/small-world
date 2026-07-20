from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.events.models import EventCategory, EventStatus


class EventCreate(BaseModel):
    title: str
    category: EventCategory
    city_id: int
    venue_id: int
    starts_at: datetime
    capacity: int
    lead_id: int


class EventUpdate(BaseModel):
    title: str | None = None
    category: EventCategory | None = None
    venue_id: int | None = None
    starts_at: datetime | None = None
    capacity: int | None = None
    lead_id: int | None = None


class EventDuplicate(BaseModel):
    starts_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: EventCategory
    city_id: int
    venue_id: int
    starts_at: datetime
    capacity: int
    lead_id: int
    status: EventStatus
