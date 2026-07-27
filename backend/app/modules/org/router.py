from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.db import get_db
from app.modules.org import service
from app.modules.org.deps import get_current_user, require_roles
from app.modules.org.models import StaffRole
from app.modules.org.schemas import (
    CityCreate,
    CityOut,
    CityUpdate,
    CurrentUser,
    LoginRequest,
    StaffCreate,
    StaffOut,
    StaffUpdate,
    VenueCreate,
    VenueOut,
    VenueUpdate,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=CurrentUser)
def login(payload: LoginRequest, response: Response, db: DBSession = Depends(get_db)) -> CurrentUser:
    try:
        user, token, expires_at = service.login(db, payload.login_identifier, payload.password)
    except service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.env != "development",
        expires=expires_at,
    )
    return user


@auth_router.post("/logout")
def logout(
    response: Response,
    db: DBSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> dict[str, bool]:
    if session_token is not None:
        service.logout(db, session_token)
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@auth_router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user


# Cities/venues/staff CRUD is restricted to founders and city leads; event_leads get 403.
_org_admin = require_roles(StaffRole.founder, StaffRole.city_lead)

cities_router = APIRouter(prefix="/cities", tags=["cities"], dependencies=[Depends(_org_admin)])


@cities_router.get("", response_model=list[CityOut])
def list_cities(user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)) -> list[CityOut]:
    return service.list_cities(db, user)


@cities_router.post("", response_model=CityOut)
def create_city(
    payload: CityCreate, user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)
) -> CityOut:
    try:
        return service.create_city(db, user, name=payload.name, active=payload.active)
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Founder access only")


@cities_router.patch("/{city_id}", response_model=CityOut)
def update_city(
    city_id: int,
    payload: CityUpdate,
    user: CurrentUser = Depends(_org_admin),
    db: DBSession = Depends(get_db),
) -> CityOut:
    try:
        return service.update_city(db, user, city_id, name=payload.name, active=payload.active)
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Founder access only")
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "City not found")


venues_router = APIRouter(prefix="/venues", tags=["venues"], dependencies=[Depends(_org_admin)])


@venues_router.get("", response_model=list[VenueOut])
def list_venues(user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)) -> list[VenueOut]:
    return service.list_venues(db, user)


@venues_router.get("/{venue_id}", response_model=VenueOut)
def get_venue(
    venue_id: int, user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)
) -> VenueOut:
    try:
        return service.get_venue(db, user, venue_id)
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view a venue outside your city")


@venues_router.post("", response_model=VenueOut)
def create_venue(
    payload: VenueCreate, user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)
) -> VenueOut:
    try:
        return service.create_venue(
            db,
            user,
            name=payload.name,
            city_id=payload.city_id,
            address=payload.address,
            capacity=payload.capacity,
            active=payload.active,
        )
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create a venue outside your city")


@venues_router.patch("/{venue_id}", response_model=VenueOut)
def update_venue(
    venue_id: int,
    payload: VenueUpdate,
    user: CurrentUser = Depends(_org_admin),
    db: DBSession = Depends(get_db),
) -> VenueOut:
    try:
        return service.update_venue(
            db,
            user,
            venue_id,
            name=payload.name,
            address=payload.address,
            capacity=payload.capacity,
            active=payload.active,
        )
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit a venue outside your city")
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")


staff_router = APIRouter(prefix="/staff", tags=["staff"], dependencies=[Depends(_org_admin)])


@staff_router.get("", response_model=list[StaffOut])
def list_staff(user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)) -> list[StaffOut]:
    return service.list_staff(db, user)


@staff_router.post("", response_model=StaffOut)
def create_staff(
    payload: StaffCreate, user: CurrentUser = Depends(_org_admin), db: DBSession = Depends(get_db)
) -> StaffOut:
    try:
        return service.create_staff_scoped(
            db,
            user,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            login_identifier=payload.login_identifier,
            password=payload.password,
            role=payload.role,
            city_id=payload.city_id,
        )
    except service.Forbidden:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "City leads may only create event_leads in their own city"
        )


@staff_router.patch("/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    user: CurrentUser = Depends(_org_admin),
    db: DBSession = Depends(get_db),
) -> StaffOut:
    try:
        return service.update_staff(
            db,
            user,
            staff_id,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            role=payload.role,
            city_id=payload.city_id,
            active=payload.active,
        )
    except service.Forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions for this staff member")
    except service.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff not found")


router = APIRouter()
router.include_router(auth_router)
router.include_router(cities_router)
router.include_router(venues_router)
router.include_router(staff_router)
