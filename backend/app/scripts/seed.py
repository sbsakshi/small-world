"""Dev-data seeder: founder + 3 cities (mature/growing/new-launch scenarios) +
venues + staff + volunteers + events across every lifecycle status, with
bookings, assignments, autopsies, decisions, issues and notifications to
match. Built for demos — every city tells a different story (Mumbai: healthy
and mature, Bangalore: growing with some rough edges, Delhi: brand-new and
still rocky). Safe to re-run — no-ops entirely if any city already exists, so
it never duplicates data on a second run.

Usage: python -m app.scripts.seed
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.contacts.models import Booking, BookingSource, BookingStatus, Contact
from app.modules.events.models import Event, EventCategory, EventStatus
from app.modules.knowledge.models import Decision, EventAutopsy, Issue, IssueLevel, IssueStatus, RaisedByType
from app.modules.notifications.models import Notification, NotificationRecipientType
from app.modules.org.models import City, StaffRole, Venue
from app.modules.org.service import create_city, create_staff, create_venue
from app.modules.volunteers.models import AssignmentStatus, VolunteerAssignment
from app.modules.volunteers.service import create_volunteer, set_weekly_availability


class _Founder:
    """Minimal CurrentUser stand-in with founder privileges, for calling org.service directly."""

    role = StaffRole.founder
    city_id = None


def main() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(City)) is not None:
            print("Seed data already present (a city exists); skipping.")
            return

        now = datetime.now(timezone.utc)
        actor = _Founder()

        founder = create_staff(
            db, name="Founder One", phone="+919900000001", email="founder@smallworld.dev",
            login_identifier="founder", password="password123", role=StaffRole.founder, city_id=None,
        )

        # --- Cities: three different demo scenarios ---
        mumbai = create_city(db, actor, name="Mumbai")       # flagship, mature, healthy
        bangalore = create_city(db, actor, name="Bangalore")  # growing, mixed signals
        delhi = create_city(db, actor, name="Delhi")          # brand-new launch, still rocky

        # --- Venues ---
        kala_studio = create_venue(db, actor, name="Kala Studio", city_id=mumbai.id, address="Chapel Road, Bandra West", capacity=18)
        mixing_bowl = create_venue(db, actor, name="The Mixing Bowl", city_id=mumbai.id, address="14th Road, Khar West", capacity=12)
        loft_42 = create_venue(db, actor, name="Loft 42", city_id=mumbai.id, address="SoBo Central, Colaba", capacity=24)

        quiet_hours = create_venue(db, actor, name="Quiet Hours", city_id=bangalore.id, address="12th Main, Indiranagar", capacity=16)
        garden_house = create_venue(db, actor, name="The Garden House", city_id=bangalore.id, address="Sarjapur Road", capacity=20)

        the_annex = create_venue(db, actor, name="The Annex", city_id=delhi.id, address="Hauz Khas Village", capacity=15)

        # --- Staff ---
        mumbai_lead = create_staff(db, name="Priya Nair", phone="+919900000002", email="priya@smallworld.dev", login_identifier="priya", password="password123", role=StaffRole.city_lead, city_id=mumbai.id)
        blr_lead = create_staff(db, name="Naina Pillai", phone="+919900000003", email="naina@smallworld.dev", login_identifier="naina", password="password123", role=StaffRole.city_lead, city_id=bangalore.id)
        event_lead = create_staff(db, name="Kavya Menon", phone="+919900000004", email="kavya@smallworld.dev", login_identifier="kavya", password="password123", role=StaffRole.event_lead, city_id=mumbai.id)
        blr_event_lead = create_staff(db, name="Rohan Shetty", phone="+919900000005", email="rohan@smallworld.dev", login_identifier="rohan", password="password123", role=StaffRole.event_lead, city_id=bangalore.id)
        delhi_lead = create_staff(db, name="Ananya Kapoor", phone="+919900000006", email="ananya@smallworld.dev", login_identifier="ananya", password="password123", role=StaffRole.city_lead, city_id=delhi.id)

        # --- Volunteers: reliability spread across the full 0-100 score range ---
        # (name, phone_suffix, login, city, skills, cached_score, events_done, active)
        volunteer_specs = [
            ("Riya Malhotra", "01", "riya", mumbai, [EventCategory.art], 96, 18, True),
            ("Aditya Kapoor", "02", "aditya", mumbai, [EventCategory.art, EventCategory.social], 88, 14, True),
            ("Meera Krishnan", "03", "meera", mumbai, [EventCategory.cooking], 72, 9, True),
            ("Simran Oberoi", "04", "simran", mumbai, [EventCategory.social], 34, 3, True),
            ("Dev Anand", "05", "dev", mumbai, [EventCategory.wellness], 61, 6, False),
            ("Ishaan Verma", "06", "ishaan", bangalore, [EventCategory.wellness], 79, 11, True),
            ("Tanvi Rao", "07", "tanvi", bangalore, [EventCategory.art, EventCategory.social], 91, 15, True),
            ("Karan Bhatia", "08", "karan", bangalore, [EventCategory.cooking], 45, 4, True),
            ("Neha Joshi", "09", "neha", bangalore, [EventCategory.social], 22, 2, True),
            ("Arjun Malhotra", "10", "arjun", delhi, [EventCategory.art], 100, 0, True),
            ("Sana Iyer", "11", "sana", delhi, [EventCategory.wellness, EventCategory.social], 55, 2, True),
        ]
        vol = {}
        for name, suffix, login, city, skills, score, events_done, active in volunteer_specs:
            v = create_volunteer(
                db, name=name, phone=f"+9199000001{suffix}", email=None,
                login_identifier=login, password="password123", city_id=city.id, skills=skills,
            )
            set_weekly_availability(db, v.id, [4, 5, 6])
            v.cached_score = score
            v.events_done = events_done
            v.active = active
            vol[login] = v
        db.commit()

        # --- Events: every lifecycle status, spread across cities/categories/time ---
        events = {}

        def make_event(key, title, category, city_id, venue_id, lead_id, starts_at, status, started_at=None):
            e = Event(
                title=title, category=category, city_id=city_id, venue_id=venue_id,
                starts_at=starts_at, capacity=14, lead_id=lead_id, status=status, started_at=started_at,
            )
            db.add(e)
            events[key] = e

        # Mumbai — mature, mostly healthy
        make_event("ink_chai", "Ink & Chai", EventCategory.art, mumbai.id, kala_studio.id, event_lead.id, now - timedelta(days=7), EventStatus.closed)
        make_event("jazz_jam", "Sunset Jazz Jam", EventCategory.social, mumbai.id, loft_42.id, event_lead.id, now - timedelta(days=20), EventStatus.closed)
        make_event("clay_coffee", "Clay & Coffee", EventCategory.art, mumbai.id, kala_studio.id, event_lead.id, now - timedelta(days=3), EventStatus.closed)
        make_event("watercolour", "Watercolour Nite", EventCategory.art, mumbai.id, kala_studio.id, event_lead.id, now + timedelta(days=2), EventStatus.published)
        make_event("konkan", "Flavors of Konkan", EventCategory.cooking, mumbai.id, mixing_bowl.id, event_lead.id, now - timedelta(hours=2), EventStatus.started, started_at=now - timedelta(hours=1, minutes=40))
        make_event("knife_skills", "Knife Skills 101", EventCategory.cooking, mumbai.id, mixing_bowl.id, event_lead.id, now + timedelta(days=10), EventStatus.draft)
        make_event("rooftop_mixer", "Rooftop Mixer", EventCategory.social, mumbai.id, loft_42.id, event_lead.id, now - timedelta(days=1), EventStatus.awaiting_review, started_at=now - timedelta(days=1, hours=3))

        # Bangalore — growing, mixed signals
        make_event("sunday_reset", "Sunday Reset", EventCategory.wellness, bangalore.id, quiet_hours.id, blr_event_lead.id, now + timedelta(days=5), EventStatus.published)
        make_event("garden_potluck", "Garden Potluck", EventCategory.cooking, bangalore.id, garden_house.id, blr_event_lead.id, now - timedelta(days=14), EventStatus.closed)
        make_event("wellness_circle", "Midweek Wellness Circle", EventCategory.wellness, bangalore.id, quiet_hours.id, blr_event_lead.id, now - timedelta(days=6), EventStatus.awaiting_review, started_at=now - timedelta(days=6, hours=2))
        make_event("sketch_social", "Founders' Sketch Social", EventCategory.art, bangalore.id, garden_house.id, blr_event_lead.id, now + timedelta(days=8), EventStatus.cancelled)

        # Delhi — brand-new launch, still rocky
        make_event("delhi_mixer", "Welcome to Delhi Mixer", EventCategory.social, delhi.id, the_annex.id, delhi_lead.id, now + timedelta(days=3), EventStatus.published)
        make_event("hauz_khas_walk", "Hauz Khas Art Walk", EventCategory.art, delhi.id, the_annex.id, delhi_lead.id, now + timedelta(days=15), EventStatus.draft)
        make_event("first_cooking_jam", "First Cooking Jam", EventCategory.cooking, delhi.id, the_annex.id, delhi_lead.id, now - timedelta(days=10), EventStatus.closed)

        db.flush()

        # --- Volunteer assignments: every status, ratings on closed events ---
        def make_assignment(event_key, volunteer_login, assigned_by_id, status, rating=None, note=None, responded_at=None):
            db.add(VolunteerAssignment(
                event_id=events[event_key].id, volunteer_id=vol[volunteer_login].id,
                status=status, assigned_by=assigned_by_id, responded_at=responded_at,
                coordinator_note=note, rating=rating,
            ))

        make_assignment("ink_chai", "riya", mumbai_lead.id, AssignmentStatus.accepted, rating=5, note="Great with the walk-in crowd.", responded_at=now - timedelta(days=8))
        make_assignment("jazz_jam", "aditya", mumbai_lead.id, AssignmentStatus.accepted, rating=4, note="Solid door management, arrived late.", responded_at=now - timedelta(days=21))
        make_assignment("clay_coffee", "riya", mumbai_lead.id, AssignmentStatus.accepted, rating=5, responded_at=now - timedelta(days=4))
        make_assignment("watercolour", "riya", mumbai_lead.id, AssignmentStatus.pending)
        make_assignment("konkan", "meera", mumbai_lead.id, AssignmentStatus.accepted, responded_at=now - timedelta(days=1))
        make_assignment("rooftop_mixer", "dev", mumbai_lead.id, AssignmentStatus.accepted, responded_at=now - timedelta(days=2))
        make_assignment("sunday_reset", "ishaan", blr_lead.id, AssignmentStatus.pending)
        make_assignment("garden_potluck", "karan", blr_lead.id, AssignmentStatus.accepted, rating=3, note="Ran out of plates halfway through.", responded_at=now - timedelta(days=15))
        make_assignment("garden_potluck", "tanvi", blr_lead.id, AssignmentStatus.declined, responded_at=now - timedelta(days=16))
        make_assignment("wellness_circle", "ishaan", blr_lead.id, AssignmentStatus.accepted, responded_at=now - timedelta(days=7))
        make_assignment("sketch_social", "tanvi", blr_lead.id, AssignmentStatus.expired)
        make_assignment("delhi_mixer", "sana", delhi_lead.id, AssignmentStatus.pending)
        make_assignment("first_cooking_jam", "arjun", delhi_lead.id, AssignmentStatus.accepted, rating=2, note="Turnout was half of RSVPs — mostly no-shows.", responded_at=now - timedelta(days=11))

        # --- Bookings: contacts + varied sources/statuses per event ---
        def make_booking(event_key, name, phone, status, source, amount=0):
            contact = Contact(phone=phone, name=name, city_id=events[event_key].city_id)
            db.add(contact)
            db.flush()
            db.add(Booking(contact_id=contact.id, event_id=events[event_key].id, status=status, source=source, amount=amount))

        # Ink & Chai (closed) — bookkeeping already applied
        make_booking("ink_chai", "Aarav Menon", "+919911000001", BookingStatus.checked_in, BookingSource.manual)
        make_booking("ink_chai", "Diya Sharma", "+919911000002", BookingStatus.checked_in, BookingSource.razorpay, amount=500)
        make_booking("ink_chai", "Kabir Rao", "+919911000003", BookingStatus.no_show, BookingSource.manual)

        # Sunset Jazz Jam (closed)
        make_booking("jazz_jam", "Neel Chatterjee", "+919911000004", BookingStatus.checked_in, BookingSource.razorpay, amount=700)
        make_booking("jazz_jam", "Alia Fernandes", "+919911000005", BookingStatus.checked_in, BookingSource.bms, amount=650)
        make_booking("jazz_jam", "Yash Thakur", "+919911000006", BookingStatus.checked_in, BookingSource.manual)
        make_booking("jazz_jam", "Priyanka Das", "+919911000007", BookingStatus.no_show, BookingSource.district, amount=650)

        # Clay & Coffee (closed)
        make_booking("clay_coffee", "Rhea Kulkarni", "+919911000008", BookingStatus.checked_in, BookingSource.csv)
        make_booking("clay_coffee", "Farhan Sheikh", "+919911000009", BookingStatus.checked_in, BookingSource.district, amount=450)
        make_booking("clay_coffee", "Ira Bose", "+919911000010", BookingStatus.cancelled, BookingSource.razorpay, amount=450)

        # Watercolour Nite (published) — pre-event signups, nobody checked in yet
        make_booking("watercolour", "Vivaan Khanna", "+919911000011", BookingStatus.confirmed, BookingSource.razorpay, amount=500)
        make_booking("watercolour", "Anaya Pillai", "+919911000012", BookingStatus.confirmed, BookingSource.manual)

        # Flavors of Konkan (started) — door is live right now
        make_booking("konkan", "Dhruv Nair", "+919911000013", BookingStatus.checked_in, BookingSource.razorpay, amount=600)
        make_booking("konkan", "Myra Ahluwalia", "+919911000014", BookingStatus.checked_in, BookingSource.manual)
        make_booking("konkan", "Sai Krishnan", "+919911000015", BookingStatus.checked_in, BookingSource.bms, amount=600)
        make_booking("konkan", "Zoya Ansari", "+919911000016", BookingStatus.confirmed, BookingSource.razorpay, amount=600)

        # Rooftop Mixer (awaiting_review) — door closed, no-show bookkeeping NOT run yet
        make_booking("rooftop_mixer", "Kiaan Bhatt", "+919911000017", BookingStatus.checked_in, BookingSource.manual)
        make_booking("rooftop_mixer", "Tara Iyengar", "+919911000018", BookingStatus.checked_in, BookingSource.razorpay, amount=550)
        make_booking("rooftop_mixer", "Reyansh Dutta", "+919911000019", BookingStatus.confirmed, BookingSource.manual)

        # Garden Potluck (closed) — mediocre event, higher no-show ratio
        make_booking("garden_potluck", "Advika Rao", "+919911000020", BookingStatus.checked_in, BookingSource.manual)
        make_booking("garden_potluck", "Ivan Pinto", "+919911000021", BookingStatus.checked_in, BookingSource.csv)
        make_booking("garden_potluck", "Larissa Fonseca", "+919911000022", BookingStatus.no_show, BookingSource.manual)
        make_booking("garden_potluck", "Aryan Hegde", "+919911000023", BookingStatus.no_show, BookingSource.csv)
        make_booking("garden_potluck", "Meher Chawla", "+919911000024", BookingStatus.cancelled, BookingSource.manual)

        # Midweek Wellness Circle (awaiting_review, overdue) — in limbo, no bookkeeping yet
        make_booking("wellness_circle", "Nitya Subramaniam", "+919911000025", BookingStatus.checked_in, BookingSource.manual)
        make_booking("wellness_circle", "Om Prakash", "+919911000026", BookingStatus.confirmed, BookingSource.manual)
        make_booking("wellness_circle", "Sara Mathew", "+919911000027", BookingStatus.confirmed, BookingSource.manual)

        # Founders' Sketch Social (cancelled) — bookings orphaned by the cancellation
        make_booking("sketch_social", "Aisha Noronha", "+919911000028", BookingStatus.cancelled, BookingSource.manual)
        make_booking("sketch_social", "Vihaan Kamath", "+919911000029", BookingStatus.cancelled, BookingSource.razorpay, amount=400)

        # Welcome to Delhi Mixer (published) — new city, first signups
        make_booking("delhi_mixer", "Ritvik Sinha", "+919911000030", BookingStatus.confirmed, BookingSource.manual)
        make_booking("delhi_mixer", "Anvi Bakshi", "+919911000031", BookingStatus.confirmed, BookingSource.manual)

        # First Cooking Jam (closed, Delhi) — rocky launch, mostly no-shows
        make_booking("first_cooking_jam", "Kabir Malhotra", "+919911000032", BookingStatus.checked_in, BookingSource.manual)
        make_booking("first_cooking_jam", "Diya Kapoor", "+919911000033", BookingStatus.no_show, BookingSource.manual)
        make_booking("first_cooking_jam", "Rehan Qureshi", "+919911000034", BookingStatus.no_show, BookingSource.csv)
        make_booking("first_cooking_jam", "Vanya Chopra", "+919911000035", BookingStatus.no_show, BookingSource.manual)

        # --- Event autopsies for every closed event ---
        def make_autopsy(event_key, submitted_by, attendance_actual, venue_rating, what_worked, what_didnt, submitted_at):
            db.add(EventAutopsy(
                event_id=events[event_key].id, submitted_by=submitted_by,
                attendance_actual=attendance_actual, venue_rating=venue_rating,
                what_worked=what_worked, what_didnt=what_didnt, submitted_at=submitted_at,
            ))

        make_autopsy("ink_chai", event_lead.id, 2, 5, "Cozy space, great for a small art crowd.", "One no-show despite a confirmation call.", now - timedelta(days=6, hours=20))
        make_autopsy("jazz_jam", event_lead.id, 3, 5, "Loft's acoustics were perfect, sold out fast.", "Started 20 min late, sound check ran over.", now - timedelta(days=19, hours=22))
        make_autopsy("clay_coffee", event_lead.id, 2, 4, "Good repeat-attendee turnout.", "One cancellation refunded late.", now - timedelta(days=2, hours=18))
        make_autopsy("garden_potluck", blr_event_lead.id, 2, 3, "Great food, strong energy from those who came.", "Two no-shows and a last-minute cancellation hurt the potluck math.", now - timedelta(days=13, hours=15))
        make_autopsy("first_cooking_jam", delhi_lead.id, 1, 2, "The one attendee who came loved it.", "Barely any awareness yet — 3 of 4 bookings no-showed. Need local marketing before the next one.", now - timedelta(days=9, hours=10))

        # --- Decisions: institutional memory ---
        db.add(Decision(title="Standardize on Razorpay for Mumbai ticketing", body="Consolidating away from manual collection for anything with a ticket price — fewer reconciliation headaches.", author_id=founder.id, city_id=mumbai.id, venue_id=None, category=None, decided_at=(now - timedelta(days=30)).date()))
        db.add(Decision(title="Cap art workshops at 14 seats", body="Beyond 14 the instructor can't give individual feedback — capacity should reflect that, not just room size.", author_id=mumbai_lead.id, city_id=None, venue_id=None, category=EventCategory.art, decided_at=(now - timedelta(days=60)).date()))
        db.add(Decision(title="Pilot Delhi launch with manual bookings only for first month", body="No payment gateway integration until we've validated turnout — avoids reconciling refunds for an unproven market.", author_id=founder.id, city_id=delhi.id, venue_id=None, category=None, decided_at=(now - timedelta(days=12)).date()))
        db.add(Decision(title="Move cooking events out of Kala Studio", body="No proper ventilation for hot-plate work — Knife Skills 101 and future cooking jams go to The Mixing Bowl instead.", author_id=event_lead.id, city_id=None, venue_id=kala_studio.id, category=EventCategory.cooking, decided_at=(now - timedelta(days=5)).date()))

        # --- Issues: open + resolved, across the escalation ladder ---
        db.add(Issue(title="Garden Potluck no-show rate", body="Two of five bookings no-showed with no cancellation — considering a deposit for potlucks going forward.", raised_by_type=RaisedByType.staff, raised_by_id=blr_event_lead.id, event_id=events["garden_potluck"].id, venue_id=garden_house.id, status=IssueStatus.open, current_level=IssueLevel.event_lead))
        db.add(Issue(title="Neha's last three assignments all declined or expired", body="Worth a check-in before assigning her again — might just be a bad month, might be availability mismatch.", raised_by_type=RaisedByType.staff, raised_by_id=blr_lead.id, volunteer_id=vol["neha"].id, status=IssueStatus.open, current_level=IssueLevel.city_lead))
        db.add(Issue(title="First Cooking Jam turnout", body="3 of 4 confirmed bookings no-showed for our very first Delhi event — need a local-marketing push before scheduling the next one.", raised_by_type=RaisedByType.staff, raised_by_id=delhi_lead.id, event_id=events["first_cooking_jam"].id, status=IssueStatus.resolved, current_level=IssueLevel.founder, resolution_note="Agreed to hold off on a second Delhi event until we've run a local WhatsApp community push.", resolved_by=founder.id, resolved_at=now - timedelta(days=4)))
        db.add(Issue(title="AC at Quiet Hours cut out mid-session", body="Got warm fast once it died — venue said they'd get it serviced before Sunday Reset.", raised_by_type=RaisedByType.volunteer, raised_by_id=vol["ishaan"].id, venue_id=quiet_hours.id, status=IssueStatus.open, current_level=IssueLevel.event_lead))

        # --- Notifications: a mix of read/unread across recipients ---
        db.add(Notification(recipient_type=NotificationRecipientType.staff, recipient_id=mumbai_lead.id, title="Watercolour Nite published", body="Assign a volunteer before it fills up.", action_type="event_published", action_ref=events["watercolour"].id))
        db.add(Notification(recipient_type=NotificationRecipientType.volunteer, recipient_id=vol["riya"].id, title="You've been assigned to Watercolour Nite", body="Respond within 24h.", action_type="assignment_created", action_ref=None, read_at=now - timedelta(days=1)))
        db.add(Notification(recipient_type=NotificationRecipientType.staff, recipient_id=blr_lead.id, title="Tanvi Rao declined Garden Potluck", body="You'll need to find another volunteer.", action_type="assignment_declined", action_ref=None))
        db.add(Notification(recipient_type=NotificationRecipientType.staff, recipient_id=blr_event_lead.id, title="Midweek Wellness Circle is overdue for review", body="The door closed 6 days ago — file the autopsy to close it out.", action_type="autopsy_reminder", action_ref=events["wellness_circle"].id))
        db.add(Notification(recipient_type=NotificationRecipientType.volunteer, recipient_id=vol["ishaan"].id, title="Reminder: Sunday Reset needs a response", body="Your assignment is still pending.", action_type="assignment_created", action_ref=None, read_at=now - timedelta(hours=5)))

        db.commit()
        print(
            f"Seeded: founder(login=founder,pw=password123), 3 cities, 6 venues, 5 city/event leads, "
            f"{len(vol)} volunteers, {len(events)} events (every lifecycle status), bookings, assignments, "
            f"5 autopsies, 4 decisions, 4 issues, notifications."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
