import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.modules.org.models import StaffRole
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.service import create_volunteer


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def city(db):
    founder = create_staff(
        db, name="Seed Founder", phone="+919900000200", email=None,
        login_identifier="seed-founder", password="pw", role=StaffRole.founder, city_id=None,
    )
    return create_city(db, _as_user(founder, StaffRole.founder, None), name="Router City")


def _as_user(staff, role, city_id):
    from app.modules.org.schemas import CurrentUser

    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=role, city_id=city_id)


def _login(client, login_identifier: str, password: str = "pw") -> None:
    res = client.post("/auth/login", json={"login_identifier": login_identifier, "password": password})
    assert res.status_code == 200, res.text


@pytest.fixture
def founder(db):
    return create_staff(
        db, name="Founder", phone="+919900000201", email=None,
        login_identifier="founder-router", password="pw", role=StaffRole.founder, city_id=None,
    )


@pytest.fixture
def event_lead(db, city):
    return create_staff(
        db, name="Lead", phone="+919900000202", email=None,
        login_identifier="lead-router", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )


@pytest.fixture
def volunteer(db, city):
    return create_volunteer(
        db, name="Vol", phone="+919900000203", email=None,
        login_identifier="vol-router", password="pw", city_id=city.id, skills=[],
    )


def test_health_needs_no_auth(client):
    assert client.get("/health").status_code == 200


def test_org_endpoints_require_auth(client):
    assert client.get("/cities").status_code == 401


def test_login_with_bad_credentials_is_401(client, founder):
    res = client.post("/auth/login", json={"login_identifier": "founder-router", "password": "wrong"})
    assert res.status_code == 401


def test_founder_can_list_and_create_city(client, founder):
    _login(client, "founder-router")
    assert client.get("/cities").status_code == 200

    res = client.post("/cities", json={"name": "New City"})
    assert res.status_code == 200
    assert res.json()["name"] == "New City"


def test_event_lead_is_403_on_org_admin_endpoints(client, event_lead):
    _login(client, "lead-router")
    res = client.get("/cities")
    assert res.status_code == 403

    res = client.post("/cities", json={"name": "Nope"})
    assert res.status_code == 403


def test_volunteer_is_403_on_staff_only_endpoints(client, volunteer):
    _login(client, "vol-router")
    res = client.get("/events")
    assert res.status_code == 403

    res = client.get("/cities")
    assert res.status_code == 403


def test_volunteer_can_reach_their_own_endpoints(client, volunteer):
    _login(client, "vol-router")
    res = client.get("/volunteers/me/assignments")
    assert res.status_code == 200
    assert res.json() == []


def test_event_not_found_is_404(client, founder):
    _login(client, "founder-router")
    assert client.get("/events/999999").status_code == 404


def test_city_lead_cannot_create_venue_outside_own_city(db, client, city, founder):
    other_city = create_city(db, _as_user(founder, StaffRole.founder, None), name="Other Router City")
    create_staff(
        db, name="Scoped Lead", phone="+919900000204", email=None,
        login_identifier="scoped-lead-router", password="pw", role=StaffRole.city_lead, city_id=city.id,
    )
    _login(client, "scoped-lead-router")

    res = client.post(
        "/venues",
        json={"name": "Venue", "city_id": other_city.id, "address": "Addr", "capacity": 10},
    )
    assert res.status_code == 403

    res = client.post(
        "/venues",
        json={"name": "Venue", "city_id": city.id, "address": "Addr", "capacity": 10},
    )
    assert res.status_code == 200


def test_decisions_role_gating(client, event_lead, city):
    _login(client, "lead-router")
    # Write access to decisions is city_lead + founder only — event_lead is refused outright.
    res = client.post(
        "/decisions",
        json={"title": "Buy easels?", "body": "Cost review", "city_id": city.id, "decided_at": "2026-07-20"},
    )
    assert res.status_code == 403


def test_autopsy_requires_awaiting_review_event(client, founder, event_lead, city, db):
    venue = create_venue(db, _as_user(founder, StaffRole.founder, None), name="V", city_id=city.id, address="A", capacity=5)
    _login(client, "founder-router")
    res = client.post(
        "/events",
        json={
            "title": "Night",
            "category": "art",
            "city_id": city.id,
            "venue_id": venue.id,
            "starts_at": "2026-08-01T18:00:00Z",
            "capacity": 5,
            "lead_id": event_lead.id,
        },
    )
    assert res.status_code == 200
    event_id = res.json()["id"]

    res = client.post(
        f"/events/{event_id}/autopsy",
        json={"attendance_actual": 10, "venue_rating": 4, "what_worked": "Good", "what_didnt": "Bad"},
    )
    assert res.status_code == 409


def test_assignment_create_notifies_volunteer_and_decline_notifies_assigner(client, founder, event_lead, volunteer, city, db):
    venue = create_venue(db, _as_user(founder, StaffRole.founder, None), name="V", city_id=city.id, address="A", capacity=5)
    _login(client, "founder-router")
    res = client.post(
        "/events",
        json={
            "title": "Night",
            "category": "art",
            "city_id": city.id,
            "venue_id": venue.id,
            "starts_at": "2026-08-01T18:00:00Z",
            "capacity": 5,
            "lead_id": event_lead.id,
        },
    )
    event_id = res.json()["id"]

    res = client.post("/assignments", json={"event_id": event_id, "volunteer_id": volunteer.id})
    assert res.status_code == 200
    assignment_id = res.json()["id"]

    _login(client, "vol-router")
    inbox = client.get("/notifications").json()
    assert [n["action_type"] for n in inbox] == ["assignment_created"]

    res = client.post(f"/assignments/{assignment_id}/respond", json={"accept": False})
    assert res.status_code == 200

    _login(client, "founder-router")
    inbox = client.get("/notifications").json()
    assert [n["action_type"] for n in inbox] == ["assignment_declined"]


def test_volunteer_can_checkin_and_close_door_only_when_assigned(client, founder, event_lead, volunteer, city, db):
    from app.modules.contacts.service import create_manual_booking

    venue = create_venue(db, _as_user(founder, StaffRole.founder, None), name="V", city_id=city.id, address="A", capacity=5)
    _login(client, "founder-router")
    res = client.post(
        "/events",
        json={
            "title": "Night",
            "category": "art",
            "city_id": city.id,
            "venue_id": venue.id,
            "starts_at": "2026-08-01T18:00:00Z",
            "capacity": 5,
            "lead_id": event_lead.id,
        },
    )
    event_id = res.json()["id"]
    client.post(f"/events/{event_id}/publish")
    booking = create_manual_booking(db, event_id=event_id, phone="9876543299", name="Guest", email=None, amount=0)

    _login(client, "vol-router")
    res = client.post(f"/events/{event_id}/checkin/{booking.id}")
    assert res.status_code == 403
    res = client.get(f"/events/{event_id}/door-roster")
    assert res.status_code == 403

    _login(client, "founder-router")
    res = client.post("/assignments", json={"event_id": event_id, "volunteer_id": volunteer.id})
    assignment_id = res.json()["id"]

    _login(client, "vol-router")
    client.post(f"/assignments/{assignment_id}/respond", json={"accept": True})

    res = client.get(f"/events/{event_id}/door-roster")
    assert res.status_code == 200
    assert res.json() == [{"booking_id": booking.id, "name": "Guest", "phone": "+919876543299", "status": "confirmed"}]

    res = client.post(f"/events/{event_id}/checkin/{booking.id}")
    assert res.status_code == 200
    assert res.json()["status"] == "checked_in"

    res = client.post(f"/events/{event_id}/close-door")
    assert res.status_code == 200
    assert res.json()["status"] == "awaiting_review"
