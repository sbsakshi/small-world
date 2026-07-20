import enum
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class DecisionStatus(str, enum.Enum):
    open = "open"
    decided = "decided"


class Decision(TimestampMixin, Base):
    """A city-scoped call staff need to make (or have made), optionally tied to a venue."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus, name="decision_status"), default=DecisionStatus.open
    )
    raised_by_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    # Freeform context, e.g. who else was involved ("with Kavya") — not modeled relationally.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hides the decision from event_leads (e.g. reliability notes about a host/volunteer).
    staff_only: Mapped[bool] = mapped_column(default=False)

    city = relationship("City")
    venue = relationship("Venue")
    raised_by = relationship("Staff", foreign_keys=[raised_by_id])
    decided_by = relationship("Staff", foreign_keys=[decided_by_id])


class IssuePriority(str, enum.Enum):
    high = "high"
    low = "low"


class IssueStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class Issue(TimestampMixin, Base):
    """A city-scoped operational problem, optionally tied to a venue."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    priority: Mapped[IssuePriority] = mapped_column(SAEnum(IssuePriority, name="issue_priority"))
    status: Mapped[IssueStatus] = mapped_column(SAEnum(IssueStatus, name="issue_status"), default=IssueStatus.open)
    raised_by_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    city = relationship("City")
    venue = relationship("Venue")
    raised_by = relationship("Staff", foreign_keys=[raised_by_id])
    resolved_by = relationship("Staff", foreign_keys=[resolved_by_id])


class EventReport(TimestampMixin, Base):
    """The narrative debrief for a single completed event. One-to-one with `Event`."""

    __tablename__ = "event_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), unique=True)
    note: Mapped[str] = mapped_column(Text)
    # List of {"tone": "good"|"warn"|"accent"|"plain", "label": str}; small and always read/written whole.
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))

    event = relationship("Event")
    created_by = relationship("Staff")
