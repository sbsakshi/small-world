from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.jobs.procrastinate_app import app as procrastinate_app
from app.modules.contacts.router import router as contacts_router
from app.modules.events.router import router as events_router
from app.modules.notifications.router import router as notifications_router
from app.modules.org.router import router as org_router
from app.modules.reports.router import router as reports_router
from app.modules.volunteers.router import router as volunteers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Jobs are deferred synchronously from request handlers, so the app's
    # connection pool needs to be open for the lifetime of the process.
    with procrastinate_app.open():
        yield


app = FastAPI(title="Small World OS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(org_router)
app.include_router(events_router)
app.include_router(contacts_router)
app.include_router(volunteers_router)
app.include_router(notifications_router)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
