from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.events.models import EventCategory
from app.modules.knowledge.models import IssueLevel, IssueStatus, RaisedByType


# --- Event autopsies -----------------------------------------------------


class AutopsyVolunteerRatingIn(BaseModel):
    assignment_id: int
    rating: int
    coordinator_note: str | None = None


class AutopsyCreate(BaseModel):
    attendance_actual: int
    venue_rating: int
    what_worked: str
    what_didnt: str
    volunteer_ratings: list[AutopsyVolunteerRatingIn] = []


class AutopsyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    submitted_by: int
    attendance_actual: int
    venue_rating: int
    what_worked: str
    what_didnt: str
    submitted_at: datetime


class PendingAutopsyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    city_id: int
    venue_id: int
    starts_at: datetime


# --- Decisions -------------------------------------------------------------


class DecisionCreate(BaseModel):
    title: str
    body: str
    city_id: int | None = None
    venue_id: int | None = None
    category: EventCategory | None = None
    decided_at: date


class DecisionUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    city_id: int | None = None
    venue_id: int | None = None
    category: EventCategory | None = None
    decided_at: date | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    author_id: int
    city_id: int | None
    venue_id: int | None
    category: EventCategory | None
    decided_at: date
    created_at: datetime
    updated_at: datetime


# --- Issues -------------------------------------------------------------


class IssueCreate(BaseModel):
    title: str
    body: str
    event_id: int | None = None
    venue_id: int | None = None
    volunteer_id: int | None = None


class IssueResolve(BaseModel):
    resolution_note: str


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    raised_by_type: RaisedByType
    raised_by_id: int
    event_id: int | None
    venue_id: int | None
    volunteer_id: int | None
    status: IssueStatus
    current_level: IssueLevel
    resolution_note: str | None
    resolved_by: int | None
    created_at: datetime
    resolved_at: datetime | None


class PatternCountOut(BaseModel):
    count: int
