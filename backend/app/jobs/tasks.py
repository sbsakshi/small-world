import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.db import SessionLocal
from app.jobs.procrastinate_app import app
from app.modules.notifications import service as notifications_service
from app.modules.notifications.models import NotificationRecipientType
from app.modules.volunteers import service as volunteers_service

logger = logging.getLogger(__name__)

ASSIGNMENT_RESPONSE_WINDOW_HOURS = 24
NO_SHOW_SWEEP_DELAY_HOURS = 6


def _assignment_expiry_lock(assignment_id: int) -> str:
    return f"assignment-expiry-{assignment_id}"


def _no_show_sweep_lock(event_id: int) -> str:
    return f"no-show-sweep-{event_id}"


def _best_effort(action: str, fn) -> None:
    """Job scheduling is a side effect of an already-committed business transaction —
    a broker hiccup here must never surface as a 500 on an otherwise-successful request."""
    try:
        fn()
    except Exception:
        logger.exception("job scheduling failed: %s", action)


def schedule_assignment_expiry(assignment_id: int) -> None:
    """Enqueues the 24h escalation job for a freshly-created pending assignment."""
    _best_effort(
        f"schedule_assignment_expiry({assignment_id})",
        lambda: expire_assignment.configure(
            queueing_lock=_assignment_expiry_lock(assignment_id),
            schedule_at=datetime.now(timezone.utc) + timedelta(hours=ASSIGNMENT_RESPONSE_WINDOW_HOURS),
        ).defer(assignment_id=assignment_id),
    )


def cancel_assignment_expiry(assignment_id: int) -> None:
    """Best-effort cancel: removes the still-queued expiry job when a volunteer responds early.

    Deletes by queueing_lock directly against procrastinate's job table rather than
    going through the job-manager API, since only jobs still in `todo` are ever
    targeted and a job that already started running is left alone either way.
    """

    def _delete() -> None:
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM procrastinate_jobs WHERE queueing_lock = :lock AND status = 'todo'"),
                {"lock": _assignment_expiry_lock(assignment_id)},
            )
            db.commit()

    _best_effort(f"cancel_assignment_expiry({assignment_id})", _delete)


def schedule_no_show_sweep(event_id: int, starts_at: datetime) -> None:
    """Enqueues a sweep that marks any still-`confirmed` booking as a no-show a few
    hours after an event starts, in case staff never explicitly closes the door."""
    _best_effort(
        f"schedule_no_show_sweep({event_id})",
        lambda: sweep_no_shows.configure(
            queueing_lock=_no_show_sweep_lock(event_id),
            schedule_at=starts_at + timedelta(hours=NO_SHOW_SWEEP_DELAY_HOURS),
        ).defer(event_id=event_id),
    )


def cancel_no_show_sweep(event_id: int) -> None:
    """Called when an event is cancelled or manually completed before the sweep fires."""

    def _delete() -> None:
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM procrastinate_jobs WHERE queueing_lock = :lock AND status = 'todo'"),
                {"lock": _no_show_sweep_lock(event_id)},
            )
            db.commit()

    _best_effort(f"cancel_no_show_sweep({event_id})", _delete)


def schedule_score_recalc(volunteer_id: int) -> None:
    _best_effort(
        f"schedule_score_recalc({volunteer_id})",
        lambda: recalc_volunteer_score.defer(volunteer_id=volunteer_id),
    )


@app.task(name="expire_assignment")
def expire_assignment(assignment_id: int) -> None:
    with SessionLocal() as db:
        assignment = volunteers_service.expire_assignment(db, assignment_id)
        if assignment is None:
            return
        notifications_service.notify(
            db,
            recipient_type=NotificationRecipientType.staff,
            recipient_id=assignment.assigned_by,
            title="Assignment expired",
            body="A volunteer didn't respond to their assignment within 24 hours.",
            action_type="assignment_expired",
            action_ref=assignment.id,
        )
        db.commit()
        volunteer_id = assignment.volunteer_id
    recalc_volunteer_score.defer(volunteer_id=volunteer_id)


@app.task(name="sweep_no_shows")
def sweep_no_shows(event_id: int) -> None:
    from app.modules.contacts.models import Booking, BookingStatus
    from app.modules.events.models import Event, EventStatus
    from sqlalchemy import select

    with SessionLocal() as db:
        event = db.get(Event, event_id)
        if event is None or event.status != EventStatus.published:
            return
        bookings = list(
            db.scalars(select(Booking).where(Booking.event_id == event_id, Booking.status == BookingStatus.confirmed))
        )
        for booking in bookings:
            booking.status = BookingStatus.no_show
        db.commit()


@app.task(name="recalc_volunteer_score")
def recalc_volunteer_score(volunteer_id: int) -> None:
    """Reliability score = share of assignments the volunteer honored (accepted, not expired/declined),
    weighted against a 100-point baseline. Purely a display cache — never read for logic elsewhere."""
    from sqlalchemy import select

    from app.modules.volunteers.models import AssignmentStatus, Volunteer, VolunteerAssignment

    with SessionLocal() as db:
        volunteer = db.get(Volunteer, volunteer_id)
        if volunteer is None:
            return
        assignments = list(
            db.scalars(select(VolunteerAssignment).where(VolunteerAssignment.volunteer_id == volunteer_id))
        )
        decided = [a for a in assignments if a.status != AssignmentStatus.pending]
        if not decided:
            return
        honored = sum(1 for a in decided if a.status == AssignmentStatus.accepted)
        volunteer.cached_score = round(100 * honored / len(decided))
        db.commit()
