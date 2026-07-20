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
    res = client.post("/decisions", json={"city_id": city.id, "text": "Buy easels?"})
    assert res.status_code == 200
    decision_id = res.json()["id"]

    # event_lead may raise but not decide
    res = client.post(f"/decisions/{decision_id}/decide")
    assert res.status_code == 403


def test_event_report_requires_completed_event(client, founder, event_lead, city, db):
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

    res = client.post(f"/events/{event_id}/report", json={"note": "too early"})
    assert res.status_code == 409
