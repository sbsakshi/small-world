import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Always normalized to +91XXXXXXXXXX before insert (see contacts.service.normalize_phone).
    phone: Mapped[str] = mapped_column(String(15), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)

    city = relationship("City")


class BookingStatus(str, enum.Enum):
    initiated = "initiated"
    confirmed = "confirmed"
    checked_in = "checked_in"
    cancelled = "cancelled"
    abandoned = "abandoned"
    no_show = "no_show"


class BookingSource(str, enum.Enum):
    razorpay = "razorpay"
    bms = "bms"
    district = "district"
    manual = "manual"
    csv = "csv"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_booking_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status"), default=BookingStatus.initiated
    )
    source: Mapped[BookingSource] = mapped_column(SAEnum(BookingSource, name="booking_source"))
    amount: Mapped[int] = mapped_column(Integer)
    # Nullable: manual/csv bookings have no external order id to key idempotency on.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    contact = relationship("Contact")
    event = relationship("Event")
