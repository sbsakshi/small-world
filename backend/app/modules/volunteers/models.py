import enum
from datetime import date, datetime

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin
from app.modules.events.models import EventCategory


class Volunteer(TimestampMixin, Base):
    __tablename__ = "volunteers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(15), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_identifier: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    skills: Mapped[list[EventCategory]] = mapped_column(ARRAY(SAEnum(EventCategory, name="event_category")))
    # Source of truth is assignment/booking history; this is a display cache
    # refreshed by the score-recalc job. Never write to it directly elsewhere.
    cached_score: Mapped[int] = mapped_column(Integer, default=100)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    events_done: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    city = relationship("City")


class VolunteerWeeklyAvailability(Base):
    __tablename__ = "volunteer_weekly_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    volunteer_id: Mapped[int] = mapped_column(ForeignKey("volunteers.id"))
    # 0 = Monday .. 6 = Sunday. Row present = generally free that weekday.
    day_of_week: Mapped[int] = mapped_column(Integer)


class VolunteerDateOverride(Base):
    __tablename__ = "volunteer_date_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    volunteer_id: Mapped[int] = mapped_column(ForeignKey("volunteers.id"))
    date: Mapped[date] = mapped_column(Date)
    # Overrides the weekly pattern for this specific date, either direction.
    available: Mapped[bool] = mapped_column(Boolean)


class AssignmentStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class VolunteerAssignment(TimestampMixin, Base):
    __tablename__ = "volunteer_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    volunteer_id: Mapped[int] = mapped_column(ForeignKey("volunteers.id"))
    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, name="assignment_status"), default=AssignmentStatus.pending
    )
    assigned_by: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Per-event "passport" note the coordinator leaves for whoever assigns this volunteer next.
    coordinator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Written through from the event autopsy form, staff-only (never volunteer-visible).
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    event = relationship("Event")
    volunteer = relationship("Volunteer")
