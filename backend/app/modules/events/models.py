import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class EventCategory(str, enum.Enum):
    art = "art"
    social = "social"
    wellness = "wellness"
    cooking = "cooking"


class EventStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    started = "started"
    awaiting_review = "awaiting_review"
    closed = "closed"
    cancelled = "cancelled"


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[EventCategory] = mapped_column(SAEnum(EventCategory, name="event_category"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # May be less than venue.capacity; never validated against it beyond that (owner call).
    capacity: Mapped[int] = mapped_column(Integer)
    lead_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    status: Mapped[EventStatus] = mapped_column(
        SAEnum(EventStatus, name="event_status"), default=EventStatus.draft
    )
    # Set once, the first time a check-in succeeds against this event (draft -> published -> started).
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    city = relationship("City")
    venue = relationship("Venue")
    lead = relationship("Staff")
