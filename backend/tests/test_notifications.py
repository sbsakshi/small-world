from datetime import datetime, timezone

import pytest

from app.modules.events.models import EventCategory
from app.modules.events.service import create_event, publish_event
from app.modules.notifications.models import NotificationRecipientType
from app.modules.notifications.service import NotFound, list_inbox, mark_read, notify
from app.modules.org.models import StaffRole
from app.modules.org.schemas import CurrentUser
from app.modules.org.service import create_city, create_staff, create_venue


def test_notify_creates_a_notification(db):
    notification = notify(
        db,
        recipient_type=NotificationRecipientType.staff,
        recipient_id=1,
        title="Hello",
        body="World",
        action_type="test_action",
        action_ref=42,
    )
    assert notification.id is not None
    assert notification.read_at is None


def test_list_inbox_scopes_to_recipient(db):
    notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, title="A", body="a")
    notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=2, title="B", body="b")
    notify(db, recipient_type=NotificationRecipientType.volunteer, recipient_id=1, title="C", body="c")

    inbox = list_inbox(db, recipient_type=NotificationRecipientType.staff, recipient_id=1)
    assert [n.title for n in inbox] == ["A"]


def test_list_inbox_unread_only_filters_read(db):
    n = notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, title="A", body="a")
    mark_read(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, notification_id=n.id)
    notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, title="B", body="b")

    unread = list_inbox(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, unread_only=True)
    assert [x.title for x in unread] == ["B"]


def test_mark_read_is_idempotent(db):
    n = notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, title="A", body="a")
    first = mark_read(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, notification_id=n.id)
    second = mark_read(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, notification_id=n.id)
    assert first.read_at == second.read_at


def test_mark_read_rejects_wrong_recipient(db):
    n = notify(db, recipient_type=NotificationRecipientType.staff, recipient_id=1, title="A", body="a")
    with pytest.raises(NotFound):
        mark_read(db, recipient_type=NotificationRecipientType.staff, recipient_id=2, notification_id=n.id)
    with pytest.raises(NotFound):
        mark_read(db, recipient_type=NotificationRecipientType.volunteer, recipient_id=1, notification_id=n.id)


# --- Missing-notification backlog items (create/publish an event notifies its lead) ---


@pytest.fixture
def founder(db):
    staff = create_staff(
        db, name="Founder", phone="+919900000600", email=None,
        login_identifier="founder-notify", password="pw", role=StaffRole.founder, city_id=None,
    )
    return CurrentUser(user_type="staff", id=staff.id, name=staff.name, role=StaffRole.founder, city_id=None)


@pytest.fixture
def notify_world(db, founder):
    city = create_city(db, founder, name="Notify City")
    venue = create_venue(db, founder, name="Venue", city_id=city.id, address="Addr", capacity=10)
    lead = create_staff(
        db, name="Lead", phone="+919900000601", email=None,
        login_identifier="lead-notify", password="pw", role=StaffRole.event_lead, city_id=city.id,
    )
    return {"city": city, "venue": venue, "lead": lead}


def _lead_notifications(db, lead_id):
    return list_inbox(db, recipient_type=NotificationRecipientType.staff, recipient_id=lead_id)


def test_create_event_notifies_the_lead(db, founder, notify_world):
    event = create_event(
        db, founder, title="Night", category=EventCategory.art, city_id=notify_world["city"].id,
        venue_id=notify_world["venue"].id, starts_at=datetime.now(timezone.utc), capacity=10,
        lead_id=notify_world["lead"].id,
    )
    inbox = _lead_notifications(db, notify_world["lead"].id)
    assert [n.action_type for n in inbox] == ["event_created"]
    assert inbox[0].action_ref == event.id


def test_publish_event_notifies_the_lead(db, founder, notify_world):
    event = create_event(
        db, founder, title="Night", category=EventCategory.art, city_id=notify_world["city"].id,
        venue_id=notify_world["venue"].id, starts_at=datetime.now(timezone.utc), capacity=10,
        lead_id=notify_world["lead"].id,
    )
    publish_event(db, founder, event.id)
    inbox = _lead_notifications(db, notify_world["lead"].id)
    assert {n.action_type for n in inbox} == {"event_created", "event_published"}
