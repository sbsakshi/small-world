"""One-off: create the first founder account so there's a way to log in
before the full seeder (phase-1 item 9) exists. Safe to re-run — no-ops if
the login_identifier is already taken.

Usage: python -m app.scripts.bootstrap_founder <login_identifier> <password> <name>
"""

import sys

from app.core.db import SessionLocal
from app.modules.org.models import Staff, StaffRole
from app.modules.org.service import create_staff


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    login_identifier, password, name = sys.argv[1], sys.argv[2], sys.argv[3]

    db = SessionLocal()
    try:
        existing = db.query(Staff).filter(Staff.login_identifier == login_identifier).first()
        if existing is not None:
            print(f"Staff '{login_identifier}' already exists (id={existing.id}); skipping.")
            return

        staff = create_staff(
            db,
            name=name,
            phone="+910000000000",
            email=None,
            login_identifier=login_identifier,
            password=password,
            role=StaffRole.founder,
            city_id=None,
        )
        print(f"Created founder '{staff.login_identifier}' (id={staff.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
