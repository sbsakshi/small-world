import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin
from app.modules.events.models import EventCategory


class EventAutopsy(Base):
    """One structured debrief per completed event. Immutable once submitted — no edit endpoint."""

    __tablename__ = "event_autopsies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), unique=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    # Human correction on top of computed check-in counts — door tapping is imperfect.
    attendance_actual: Mapped[int] = mapped_column(Integer)
    venue_rating: Mapped[int] = mapped_column(Integer)
    what_worked: Mapped[str] = mapped_column(Text)
    what_didnt: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    event = relationship("Event")
    submitted_by_staff = relationship("Staff", foreign_keys=[submitted_by])


class Decision(TimestampMixin, Base):
    """A company decision record, optionally tagged to a city, venue, and/or category.

    No status workflow, no version history — it's a record, not a task (deliberate anti-scope).
    """

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    category: Mapped[EventCategory | None] = mapped_column(
        SAEnum(EventCategory, name="event_category"), nullable=True
    )
    # When the decision was actually made — may predate the record itself.
    decided_at: Mapped[date] = mapped_column(Date)

    author = relationship("Staff")
    city = relationship("City")
    venue = relationship("Venue")


class RaisedByType(str, enum.Enum):
    staff = "staff"
    volunteer = "volunteer"


class IssueStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class IssueLevel(str, enum.Enum):
    event_lead = "event_lead"
    city_lead = "city_lead"
    founder = "founder"


class Issue(Base):
    """A problem raised by anyone, climbing a visible (manually-escalated) ladder."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    # Polymorphic raiser (staff or volunteer), same pattern as Notification.recipient_type/_id.
    raised_by_type: Mapped[RaisedByType] = mapped_column(SAEnum(RaisedByType, name="raised_by_type"))
    raised_by_id: Mapped[int] = mapped_column(Integer)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    # An issue ABOUT a volunteer — distinct from raised_by (who may or may not be that volunteer).
    volunteer_id: Mapped[int | None] = mapped_column(ForeignKey("volunteers.id"), nullable=True)
    status: Mapped[IssueStatus] = mapped_column(SAEnum(IssueStatus, name="issue_status"), default=IssueStatus.open)
    current_level: Mapped[IssueLevel] = mapped_column(
        SAEnum(IssueLevel, name="issue_level"), default=IssueLevel.event_lead
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event = relationship("Event")
    venue = relationship("Venue")
    volunteer = relationship("Volunteer")
    resolved_by_staff = relationship("Staff", foreign_keys=[resolved_by])
