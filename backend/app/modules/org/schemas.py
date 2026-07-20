from pydantic import BaseModel, ConfigDict

from app.modules.org.models import SessionRecipientType, StaffRole


class LoginRequest(BaseModel):
    login_identifier: str
    password: str


class CurrentUser(BaseModel):
    """Shape returned by /auth/login and /auth/me — same for staff and volunteers.

    role/city_id are None for volunteers; a volunteer's reliability score is
    deliberately never included here (staff-only, per decision on cached_score visibility).
    """

    model_config = ConfigDict(from_attributes=True)

    user_type: SessionRecipientType
    id: int
    name: str
    role: StaffRole | None = None
    city_id: int | None = None


class CityCreate(BaseModel):
    name: str
    active: bool = True


class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class CityUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class VenueCreate(BaseModel):
    name: str
    city_id: int
    address: str
    capacity: int
    active: bool = True


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city_id: int
    address: str
    capacity: int
    active: bool


class VenueUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    capacity: int | None = None
    active: bool | None = None


class StaffCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    login_identifier: str
    password: str
    role: StaffRole
    city_id: int | None = None


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str | None
    login_identifier: str
    role: StaffRole
    city_id: int | None
    active: bool


class StaffUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    role: StaffRole | None = None
    city_id: int | None = None
    active: bool | None = None
