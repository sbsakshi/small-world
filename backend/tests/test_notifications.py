import pytest

from app.modules.notifications.models import NotificationRecipientType
from app.modules.notifications.service import NotFound, list_inbox, mark_read, notify


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
