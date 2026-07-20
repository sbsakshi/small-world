"""Dev-data seeder: founder + 2 cities + venues + staff + volunteers + events
across every status, with bookings and assignments to match. Safe to re-run —
no-ops entirely if any city already exists, so it never duplicates data on a
second run.

Usage: python -m app.scripts.seed
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.contacts.models import Booking, BookingSource, BookingStatus, Contact
from app.modules.events.models import Event, EventCategory, EventStatus
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

        founder = create_staff(
            db,
            name="Founder One",
            phone="+919900000001",
            email="founder@smallworld.dev",
            login_identifier="founder",
            password="password123",
            role=StaffRole.founder,
            city_id=None,
        )

        mumbai = create_city(db, _Founder(), name="Mumbai")
        bangalore = create_city(db, _Founder(), name="Bangalore")

        kala_studio = create_venue(
            db, _Founder(), name="Kala Studio", city_id=mumbai.id,
            address="Chapel Road, Bandra West", capacity=18,
        )
        mixing_bowl = create_venue(
            db, _Founder(), name="The Mixing Bowl", city_id=mumbai.id,
            address="14th Road, Khar West", capacity=12,
        )
        quiet_hours = create_venue(
            db, _Founder(), name="Quiet Hours", city_id=bangalore.id,
            address="12th Main, Indiranagar", capacity=16,
        )

        mumbai_lead = create_staff(
            db, name="Priya Nair", phone="+919900000002", email="priya@smallworld.dev",
            login_identifier="priya", password="password123",
            role=StaffRole.city_lead, city_id=mumbai.id,
        )
        blr_lead = create_staff(
            db, name="Naina Pillai", phone="+919900000003", email="naina@smallworld.dev",
            login_identifier="naina", password="password123",
            role=StaffRole.city_lead, city_id=bangalore.id,
        )
        event_lead = create_staff(
            db, name="Kavya Menon", phone="+919900000004", email="kavya@smallworld.dev",
            login_identifier="kavya", password="password123",
            role=StaffRole.event_lead, city_id=mumbai.id,
        )

        volunteers = []
        for i, (name, skills) in enumerate(
            [
                ("Riya Malhotra", [EventCategory.art]),
                ("Aditya Kapoor", [EventCategory.art, EventCategory.social]),
                ("Meera Krishnan", [EventCategory.cooking]),
                ("Ishaan Verma", [EventCategory.wellness]),
            ],
            start=1,
        ):
            city_id = mumbai.id if i <= 3 else bangalore.id
            volunteer = create_volunteer(
                db,
                name=name,
                phone=f"+9199000001{i:02d}",
                email=None,
                login_identifier=name.split()[0].lower(),
                password="password123",
                city_id=city_id,
                skills=skills,
            )
            set_weekly_availability(db, volunteer.id, [4, 5, 6])
            volunteers.append(volunteer)

        now = datetime.now(timezone.utc)

        completed_event = Event(
            title="Ink & Chai", category=EventCategory.art, city_id=mumbai.id,
            venue_id=kala_studio.id, starts_at=now - timedelta(days=7),
            capacity=14, lead_id=event_lead.id, status=EventStatus.completed,
        )
        published_event = Event(
            title="Watercolour Nite", category=EventCategory.art, city_id=mumbai.id,
            venue_id=kala_studio.id, starts_at=now + timedelta(days=2),
            capacity=14, lead_id=event_lead.id, status=EventStatus.published,
        )
        draft_event = Event(
            title="Knife Skills 101", category=EventCategory.cooking, city_id=mumbai.id,
            venue_id=mixing_bowl.id, starts_at=now + timedelta(days=10),
            capacity=12, lead_id=event_lead.id, status=EventStatus.draft,
        )
        blr_event = Event(
            title="Sunday Reset", category=EventCategory.wellness, city_id=bangalore.id,
            venue_id=quiet_hours.id, starts_at=now + timedelta(days=5),
            capacity=16, lead_id=blr_lead.id, status=EventStatus.published,
        )
        db.add_all([completed_event, published_event, draft_event, blr_event])
        db.flush()

        db.add(
            VolunteerAssignment(
                event_id=completed_event.id, volunteer_id=volunteers[0].id,
                status=AssignmentStatus.accepted, assigned_by=mumbai_lead.id,
                responded_at=now - timedelta(days=8),
            )
        )
        db.add(
            VolunteerAssignment(
                event_id=published_event.id, volunteer_id=volunteers[0].id,
                status=AssignmentStatus.pending, assigned_by=mumbai_lead.id,
            )
        )
        db.add(
            VolunteerAssignment(
                event_id=blr_event.id, volunteer_id=volunteers[3].id,
                status=AssignmentStatus.pending, assigned_by=blr_lead.id,
            )
        )

        for i, (name, phone, status) in enumerate(
            [
                ("Aarav Menon", "+919911000001", BookingStatus.checked_in),
                ("Diya Sharma", "+919911000002", BookingStatus.checked_in),
                ("Kabir Rao", "+919911000003", BookingStatus.no_show),
            ]
        ):
            contact = Contact(phone=phone, name=name, city_id=mumbai.id)
            db.add(contact)
            db.flush()
            db.add(
                Booking(
                    contact_id=contact.id, event_id=completed_event.id,
                    status=status, source=BookingSource.manual, amount=0,
                )
            )

        db.commit()
        print(f"Seeded: founder(login=founder,pw=password123), 2 cities, 3 venues, "
              f"3 staff, {len(volunteers)} volunteers, 4 events, assignments and bookings.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
