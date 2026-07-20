# Small World OS — Phase-1 Progress

_Last audited: 2026-07-19. Update this file whenever a checklist item's status changes — don't let it drift._

**Backend is functionally complete for phase 1** — every module has a real service/router, verified end-to-end via Docker (create→publish→assign→accept→book→check-in→complete, cancel-cascade, CSV idempotency, job scheduling). 26 automated tests pass. Frontend still runs on mock data screen-by-screen; the typed API client now covers every backend endpoint, but no page has been rewired yet.

## Status by checklist item

### 1. Foundation — DONE
- `docker-compose.yml`: all 4 services (postgres, backend, worker, frontend) wired correctly.
- FastAPI skeleton + all 5 module routers (org, events, contacts, volunteers, notifications) mounted in `main.py`.
- Alembic: one migration (`f2ff4b7c0767_initial_schema.py`) creates all 11 phase-1 tables + `sessions`. Procrastinate's own tables are applied separately (`python -m procrastinate ... schema --apply`, documented in `docker-compose.yml`).
- Health check: `GET /health` works.

### 2. Auth — DONE
- Login (staff-or-volunteer identifier), logout, `/auth/me` in `backend/app/modules/org/router.py`.
- Server-side cookie sessions (`sessions` table), not JWT.
- `org/deps.py`: `get_current_user`, `require_staff`, `require_volunteer`, `require_roles(*roles)`.
- Founder bootstrap (`scripts/bootstrap_founder.py`) and full dev seeder (`scripts/seed.py`) both work.

### 3. Org module (cities/venues/staff CRUD) — DONE
- `service.py` + `router.py`: full CRUD for cities, venues, staff.
- Role-gating: founder = all; city_lead = own city only, may only create/edit `event_lead`s in their own city.

### 4. Events module — DONE
- `schemas.py` + `service.py` + `router.py`: create/edit, publish, cancel (cascades to non-terminal bookings, same transaction), complete (auto no-shows any still-`confirmed` booking), duplicate, list/get with role + query scoping.
- Role-gating: founder = all; city_lead = own city; event_lead = only events they lead.
- Check-in lives under `/events/{event_id}/checkin/{booking_id}` (in the contacts router, since it operates on `Booking`).

### 5. Contacts module — DONE
- `normalize_phone` (`contacts/service.py`): any Indian format → `+91XXXXXXXXXX`, rejects anything that isn't a plausible 10-digit mobile number.
- CSV import (`POST /events/{id}/bookings/import`): idempotent via `(source=csv, external_id=f"{phone}:{event_id}")`; re-uploading the same file is a no-op. Per-row errors reported, not silently dropped.
- Manual booking entry (`POST /bookings/manual`), contact list/get/update.

### 6. Volunteers module — DONE
- Roster CRUD, weekly availability (full-replace) + date overrides (self-service and staff-viewable).
- Assignment state machine: `pending → accepted/declined` (volunteer), `pending → expired` (escalation job). Double-respond and wrong-volunteer-responds are rejected.
- Volunteer self-service under `/volunteers/me/*` (assignments, availability).
- `cached_score` and `events_done` are write-only from the job/service layer, never from request payloads directly.

### 6b. Reports module (decisions/issues/event-reports) — DONE
- Decided the fate raised in item 1 below: added real backend models instead of simplifying the frontend — these are genuine operational data staff need persisted, not mock-only concepts.
- `app/modules/reports/`: `Decision` (city + optional venue scoped, open/decided, staff_only flag to hide reliability-note-style decisions from event_leads), `Issue` (city + optional venue scoped, high/low priority, open/resolved), `EventReport` (one-to-one with a completed `Event`; freeform note + JSON tags list — checked-in count is deliberately not duplicated here since it's already derivable from `Booking`).
- Role-gating mirrors events: founder = all; city_lead = own city (raise + decide/resolve); event_lead = own city, read-only on staff_only decisions, can raise but not decide/resolve. Event reports use the same founder/city_lead/event_lead-of-that-event access as `events.service._ensure_event_access`, and can only be created once the event is `completed`.
- Migration `d00c615dab00_decisions_issues_event_reports.py` (hand-trimmed after autogenerate to drop noise from Procrastinate's separately-managed tables).
- 3 new tests in `tests/test_reports.py` (city-scoping/Forbidden, decide/resolve state transitions, report-requires-completed-event + one-report-per-event).
- Frontend `lib/api.ts` now has typed functions for all of these; no page wired yet (still mock data) — that's item 2 below.

### 7. Notifications module — DONE
- `MessagingProvider` ABC + `InAppProvider` (writes to the `notifications` table). Swappable for a future SMS/WhatsApp provider behind the same interface.
- `/notifications` inbox (staff or volunteer, whichever the session belongs to), mark-read.

### 8. Jobs (Procrastinate) — DONE
- `expire_assignment`: 24h escalation, scheduled on assignment creation, cancelled (deleted by `queueing_lock`) if the volunteer responds first.
- `sweep_no_shows`: marks lingering `confirmed` bookings as `no_show` 6h after an event starts if staff never closes it out; cancelled on manual cancel/complete.
- `recalc_volunteer_score`: reliability = share of decided assignments that were honored; triggered after expiry, response, and event completion.
- All scheduling calls are wrapped in a `_best_effort` guard — a broker hiccup logs and moves on instead of turning an already-committed business transaction into a 500 (found and fixed live during e2e testing: publishing an event under `AppNotOpen` had silently left the event published despite the request itself 500ing).
- Procrastinate's connection pool is opened via FastAPI's `lifespan` in `main.py`.

### 9. Seeder — DONE
- `backend/app/scripts/seed.py`: founder, 2 cities, 3 venues, 3 staff (founder/city_lead ×2/event_lead), 4 volunteers with weekly availability, 4 events across every status, assignments, and bookings (including a no-show). Idempotent — no-ops if any city already exists.

### 10. Tests — DONE (core coverage; not exhaustive)
- `backend/tests/`: 26 tests, all passing against a real Postgres (SAVEPOINT-per-test isolation, see `conftest.py`).
- Phone normalization (valid formats + rejections), assignment state machine (accept/decline/double-respond/wrong-volunteer/expire), event cancel-cascade, CSV import idempotency + row-level error reporting, job `_best_effort` guard, decisions/issues/event-reports (city-scoping, state transitions, one-report-per-completed-event).
- Not yet covered: router-level (HTTP) tests, notifications, no-show sweep job, score-recalc formula, org CRUD role-gating edge cases.

### 11. Frontend — PARTIAL (real UI shell, mock data; API client now complete)
- Real routed screens exist: login, cities list, city detail, event detail, check-in, contact/person detail, volunteer view — with a shared UI kit (`components/ui/*`).
- `frontend/src/lib/api.ts` now has typed functions for every backend endpoint (org, events, contacts/bookings, volunteers/assignments, notifications, decisions/issues/event-reports), not just auth. Typechecks clean.
- **Not done:** no page has been switched over from `mockData.ts` to the real client yet.

## What's left

1. ~~Decide the fate of decisions/issues/event-reports~~ — DONE, see 6b above: real backend models added.
2. **Wire frontend screens to the real API**, now that (1) is settled — cities/venues/staff admin screens first (closest 1:1 match to the API today), then events (incl. the new decisions/issues/event-report screens), then volunteer self-service.
3. **Router-level tests** (HTTP status codes, role-gating 403s) to complement the service-level tests that exist now.
4. **Notifications, no-show sweep, and score-recalc tests** — logic is simple but untested directly (only exercised transitively via the state-machine/cascade tests).
