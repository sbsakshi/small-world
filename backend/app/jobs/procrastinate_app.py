import procrastinate

from app.core.config import settings

# Jobs must always be enqueued inside the same DB transaction as the data
# change they relate to (see architecture decision #4) — that's what
# PsycopgConnector's transaction-aware enqueue gives us, vs. a separate broker.
connector = procrastinate.PsycopgConnector(conninfo=settings.procrastinate_database_url)
app = procrastinate.App(connector=connector)

# Imported for its side effect of registering tasks on `app` — required so the
# `procrastinate ... worker` CLI (which only loads this module) sees them.
from app.jobs import tasks  # noqa: E402,F401
