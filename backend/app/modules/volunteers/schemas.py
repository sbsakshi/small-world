from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.events.models import EventCategory
from app.modules.volunteers.models import AssignmentStatus


class VolunteerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    login_identifier: str
    password: str
    city_id: int
    skills: list[EventCategory] = []


class VolunteerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str | None
    login_identifier: str
    city_id: int
    skills: list[EventCategory]
    cached_score: int
    remarks: str | None
    events_done: int
    active: bool


class VolunteerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    skills: list[EventCategory] | None = None
    remarks: str | None = None
    active: bool | None = None


class WeeklyAvailabilitySet(BaseModel):
    """Full replacement of the volunteer's weekly pattern: the set of weekdays (0=Mon..6=Sun) they're generally free."""

    days: list[int]


class WeeklyAvailabilityOut(BaseModel):
    days: list[int]


class DateOverrideSet(BaseModel):
    date: date
    available: bool


class DateOverrideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    available: bool


class AssignmentCreate(BaseModel):
    event_id: int
    volunteer_id: int
    coordinator_note: str | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    volunteer_id: int
    status: AssignmentStatus
    assigned_by: int
    responded_at: datetime | None
    coordinator_note: str | None


class AssignmentRespond(BaseModel):
    accept: bool
