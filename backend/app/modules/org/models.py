import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class StaffRole(str, enum.Enum):
    founder = "founder"
    city_lead = "city_lead"
    event_lead = "event_lead"


class City(TimestampMixin, Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    venues: Mapped[list["Venue"]] = relationship(back_populates="city")


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(15))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_identifier: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[StaffRole] = mapped_column(SAEnum(StaffRole, name="staff_role"))
    # Founder has no city (sees everything); city_lead/event_lead are scoped to one city.
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    city: Mapped[City | None] = relationship()


class Venue(TimestampMixin, Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    address: Mapped[str] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    city: Mapped[City] = relationship(back_populates="venues")


class SessionRecipientType(str, enum.Enum):
    staff = "staff"
    volunteer = "volunteer"


class Session(TimestampMixin, Base):
    """Server-side cookie session. Deleting a row revokes it immediately."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Sessions authenticate either a staff member or a volunteer; user_type disambiguates user_id.
    user_type: Mapped[SessionRecipientType] = mapped_column(SAEnum(SessionRecipientType, name="session_user_type"))
    user_id: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
