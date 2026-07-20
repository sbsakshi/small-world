import os

import psycopg
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
# Import every module's models so Base.metadata knows about all tables.
from app.modules.contacts import models as contacts_models  # noqa: F401
from app.modules.events import models as events_models  # noqa: F401
from app.modules.notifications import models as notifications_models  # noqa: F401
from app.modules.org import models as org_models  # noqa: F401
from app.modules.reports import models as reports_models  # noqa: F401
from app.modules.volunteers import models as volunteers_models  # noqa: F401

BASE_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://smallworld:smallworld@localhost:5432/smallworld"
)
TEST_DATABASE_URL = BASE_DATABASE_URL.rsplit("/", 1)[0] + "/smallworld_test"
_ADMIN_CONNINFO = BASE_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://").rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(scope="session")
def engine():
    with psycopg.connect(_ADMIN_CONNINFO, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'smallworld_test'")
            if cur.fetchone() is None:
                cur.execute("CREATE DATABASE smallworld_test")

    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """Wraps each test in an outer transaction that's rolled back afterwards, so
    tests never see each other's data even though they share one database.

    Service code calls session.commit() freely; a SAVEPOINT restarted after each
    commit (via the after_transaction_end hook) keeps everything nested inside
    the one outer, never-committed connection-level transaction.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, autocommit=False)()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


class _FakeSessionContext:
    """Mimics `with SessionLocal() as db:` while reusing the test's own isolated session,
    so job code (which opens its own SessionLocal) still runs inside the per-test SAVEPOINT."""

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, *exc_info):
        return False


@pytest.fixture
def patch_job_session(db, monkeypatch):
    """Redirects `app.jobs.tasks.SessionLocal()` to the test's `db` fixture, so job functions
    under test (sweep_no_shows, recalc_volunteer_score, ...) participate in test isolation."""
    monkeypatch.setattr("app.jobs.tasks.SessionLocal", lambda: _FakeSessionContext(db))
