from datetime import datetime, timezone

import pytest

from app.modules.events.models import EventCategory
from app.modules.events.service import create_event, publish_event
from app.modules.contacts.service import import_csv
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue

CSV = b"phone,name,email\n9876543210,Aarav Menon,aarav@example.com\n9876543211,Diya Sharma,\n"


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000000", email=None,
        login_identifier="founder-csv", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def event(db, founder):
    city = create_city(db, founder, name="CSV City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000012", email=None,
        login_identifier="lead-csv", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    ev = create_event(
        db, founder, title="Event", category=EventCategory.art, city_id=city.id,
        venue_id=venue.id, starts_at=datetime.now(timezone.utc), capacity=10, lead_id=lead.id,
    )
    return publish_event(db, founder, ev.id)


def test_first_import_creates_bookings(db, event):
    created, skipped, errors = import_csv(db, event_id=event.id, content=CSV)
    assert created == 2
    assert skipped == 0
    assert errors == []


def test_reimporting_same_file_is_a_no_op(db, event):
    import_csv(db, event_id=event.id, content=CSV)
    created, skipped, errors = import_csv(db, event_id=event.id, content=CSV)
    assert created == 0
    assert skipped == 2
    assert errors == []


def test_invalid_rows_are_reported_not_silently_dropped(db, event):
    bad_csv = b"phone,name,email\nnotaphone,Bad Row,\n,,\n"
    created, skipped, errors = import_csv(db, event_id=event.id, content=bad_csv)
    assert created == 0
    assert len(errors) == 2
