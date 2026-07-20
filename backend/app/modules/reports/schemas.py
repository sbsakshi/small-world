from datetime import date

from pydantic import BaseModel, ConfigDict

from app.modules.reports.models import DecisionStatus, IssuePriority, IssueStatus


class DecisionCreate(BaseModel):
    city_id: int
    venue_id: int | None = None
    text: str
    note: str | None = None
    staff_only: bool = False


class DecisionUpdate(BaseModel):
    text: str | None = None
    note: str | None = None
    staff_only: bool | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int
    venue_id: int | None
    text: str
    status: DecisionStatus
    raised_by_id: int
    decided_by_id: int | None
    note: str | None
    staff_only: bool


class IssueCreate(BaseModel):
    city_id: int
    venue_id: int | None = None
    text: str
    priority: IssuePriority
    due_date: date | None = None


class IssueUpdate(BaseModel):
    text: str | None = None
    priority: IssuePriority | None = None
    due_date: date | None = None


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int
    venue_id: int | None
    text: str
    priority: IssuePriority
    status: IssueStatus
    raised_by_id: int
    resolved_by_id: int | None
    due_date: date | None


class ReportTag(BaseModel):
    tone: str
    label: str


class EventReportCreate(BaseModel):
    note: str
    tags: list[ReportTag] | None = None


class EventReportUpdate(BaseModel):
    note: str | None = None
    tags: list[ReportTag] | None = None


class EventReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    note: str
    tags: list[ReportTag] | None
    created_by_id: int
