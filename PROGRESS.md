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

---

# Phase 2 — Knowledge System

_Added 2026-07-20._ Builds a new `knowledge/` module (event autopsies, decisions, issues) per the phase-2 handoff, **replacing** the phase-1 `reports/` module entirely — the two covered similar ground but with materially different shapes (structured autopsy fields + volunteer rating write-through; FK-tagged decisions with no status workflow; a 3-level issue escalation ladder instead of priority/due_date). The old module's ~0 rows of real data (one throwaway dev-test `event_reports` row, empty `decisions`/`issues`) were migrated forward where the schemas honestly map (decisions, issues); `event_reports` had no honest mapping onto the new structured autopsy fields and was dropped without migration.

- `backend/app/modules/knowledge/`: `models.py` (`EventAutopsy`, `Decision`, `Issue`), `schemas.py`, `service.py`, `router.py`. `volunteer_assignments` gains a nullable `rating` column, written through from the autopsy form.
- Migration `c133a1e4dd0a_knowledge_system.py`: renames the old `decisions`/`issues` tables aside, rebuilds them with the new shape, migrates rows forward, then drops the renamed originals and `event_reports`. Applied and verified against the running dev Postgres (via the already-running docker-compose stack), not just written blind.
- Jobs: `send_autopsy_prompt` (fired via `schedule_autopsy_prompt` right after an event completes — a job creates the notification, matching the `expire_assignment` pattern, not a synchronous call) and `send_autopsy_reminder` (one-shot at +48h, `queueing_lock=autopsy_reminder:{event_id}`, cancelled if the autopsy is submitted first). Wired into `events/router.py`'s `complete_event`.
- Issues have no `city_id` column (per spec — tags are event/venue/volunteer only); city-lead/founder scoping derives the city through whichever tag is present (`_issue_city_id` in `knowledge/service.py`). An issue with none of those tags is visible only to its raiser and the founder — a judgment call made in the absence of a stored city, flagged here rather than silently assumed.
- Tests: `backend/tests/test_knowledge.py` (autopsy uniqueness/scoping/write-through, prompt+reminder job behavior, decision write-access, issue escalation ladder/resolve/visibility, 60-day pattern count) plus two router-level tests in `test_routers.py` updated for the new endpoints.
- Frontend: `lib/api.ts`'s decisions/issues/event-report client replaced with the new autopsy/decision/issue shapes; the three pages that were already wired to the old endpoints (`cities/page.tsx`, `cities/[cityId]/page.tsx`, `cities/[cityId]/events/[eventId]/page.tsx`) updated to match — Decisions tab (title/body/decided_at, no decide workflow), Issues tab (title/body/venue tag, escalate + resolve-with-note, issue age instead of priority), event page's autopsy form (structured fields + per-accepted-volunteer rating). `npx tsc --noEmit` and `npm run build` both clean.
- Not built (matches "composed views only, no new storage" from the handoff): dedicated venue-page autopsy/decision/issue sections and a founder-facing pending-autopsies dashboard widget — the backend queries for both (`list_autopsies_for_venue`, `list_pending_autopsies`, issue venue/event filters) exist and are exposed via the API, just not yet surfaced in a frontend screen.

---

## Backlog — flagged during tech/product walkthrough (2026-07-21)

Found by comparing the owner's mental model of the event/volunteer lifecycle against the actual code. Plumbing (jobs, `notifications_service.notify`) already exists for all three to-dos below — they're missing call sites, not new systems.

### To-dos (gaps vs. intended behavior)

_Items 1–8 done, 2026-07-22 — see below. 9–11 still open._

1. ~~**No notification when an event is created/published telling the lead to assign volunteers.**~~ — DONE. `events/service.create_event` and `publish_event` now call `notifications_service.notify` (staff recipient = `event.lead_id`, `action_type` `event_created`/`event_published`) right after each commit.
2. ~~**No notification to the volunteer when they're assigned.**~~ — DONE. `volunteers/router.create_assignment` notifies the volunteer (`action_type="assignment_created"`) right after `schedule_assignment_expiry`.
3. ~~**No notification to the lead on an explicit decline.**~~ — DONE. `respond_to_assignment` notifies `assignment.assigned_by` (`action_type="assignment_declined"`) when `accept` is false; accept still only recalculates score, no double-notify.
4. ~~**Volunteers need door check-in access.**~~ — DONE. `contacts/router.py`'s checkin/close-door/door-roster routes now use `get_current_user` + a shared `events.service._ensure_door_access` check (staff via normal event-access rules, or a volunteer with an accepted `VolunteerAssignment` for that event). New `GET /events/{id}/door-roster` (denormalized guest name/phone, since volunteers can't hit the staff-only `/contacts` directory) backs a new volunteer-facing screen at `frontend/src/app/volunteer/checkin/[eventId]/page.tsx`, linked from each accepted shift on `/volunteer`. The existing staff checkin page also gained a "Close the door" button.
5. ~~**Venue detail page.**~~ — DONE. Added `GET /venues/{id}` (`org/service.get_venue`) and a new `frontend/src/app/cities/[cityId]/venues/[venueId]/page.tsx` showing venue info, past (`closed`) events, and each one's autopsy via `listVenueAutopsies`. Venue names on the city page now link there.
6. ~~**Real event-lifecycle status, driven by ground-truth actions.**~~ — DONE. `EventStatus` is now `draft, published, started, awaiting_review, closed, cancelled` (migration `bae21774dc3b`, renames the old `completed` value to `closed` via `ALTER TYPE ... RENAME VALUE` and adds the two new values + `Event.started_at`). First successful check-in calls `events.service.mark_started`. A new `close_door` (staff or the assigned/accepted volunteer) moves `published`/`started` → `awaiting_review` and fires `schedule_autopsy_prompt`/`schedule_autopsy_reminder` — no bookkeeping yet. **Decided during implementation**: the old standalone staff "complete" action is kept, but repurposed as an override that reaches `awaiting_review` directly (same `close_door` function, staff callers skip needing an actual check-in first) rather than being removed — there's still exactly one moment of truth for completion. `knowledge/service.submit_autopsy` is now that moment: requires `awaiting_review`, marks still-`confirmed` bookings `no_show`, sets `event.status = closed`, and returns the accepted-assignment volunteer ids so the router can bump `events_done` + schedule score recalc.
7. ~~**"Today's events" view with live status.**~~ — DONE. New `frontend/src/app/today/page.tsx` (linked from `StaffHeader`), client-filters `listEvents()` (already role-scoped server-side) to today's `starts_at`, showing the live status badge per event.
8. ~~**Unified Decisions+Issues feed.**~~ — DONE. `cities/[cityId]/page.tsx`'s separate Decisions/Issues tabs are replaced by one "Activity" tab merging both lists (sorted by `created_at` desc, each row tagged with a type `Badge`), with separate "+ Add decision"/"+ Add issue" actions since the underlying models are unchanged.
9. **Comment/reply threads on both Decisions and Issues** (confirmed intended, 2026-07-21) — "consider it like a reddit/slack thread." Needs a new comment model (polymorphic to decision_id/issue_id, or two parallel tables), author (staff or volunteer, same polymorphic pattern as `Issue.raised_by_type`), body, created_at. Anyone can comment, same as anyone can create the issue/decision itself.
   - **Implementation note**: for "feels live" updates, reuse the existing pattern already in this codebase — `NotificationsBell.tsx` polls `GET /notifications` every 30s; do the same for an open thread (poll on an interval while the thread is open) rather than reaching for WebSockets/SSE. Webhooks are the wrong tool entirely — those are for server-to-server callbacks to *external* systems (e.g. actually posting into a real Slack channel), not for pushing updates to your own open browser tabs. Real push (WebSockets) is worth revisiting only if polling staleness becomes an actual problem with real concurrent usage.
10. **Freeform tags on issues/decisions** (confirmed intended, 2026-07-21) — today `Issue` tagging is only the three FK columns (`event_id`/`venue_id`/`volunteer_id`), no ad-hoc tag list. Add a generic tag field/list.
11. **Explicit "ping specific people"** (confirmed intended, 2026-07-21) — let the author pick individual staff/volunteer recipients on an issue/decision/comment, notifying exactly them via the existing `notifications_service.notify()` — same primitive already used for the escalation-ladder auto-notify (`knowledge/service._notify_level_holders`), just with an explicit recipient list instead of a derived one.

### Confirmed as already matching intent (2026-07-21) — no change needed, re: Decisions/Issues
- **Anyone can create an issue** — `create_issue` has no role check today (any authenticated staff or volunteer), matches "anyone" as described.
- **Founder/lead can close an issue** — `resolve_issue`'s `_can_act_on_issue` already gates this to founder (always), city_lead (unless already escalated to founder), or the specific event_lead (only while it's at their level) — matches "founder/lead can close" as described.

### Confirmed as already matching intent (2026-07-21) — no change needed
- Event autopsy scope: venue review (`venue_rating`), volunteer review (per-assignment `rating`), and event/crowd review (`what_worked`/`what_didnt`) are all already captured in one autopsy — matches intent as-is.
- Decisions/Issues are intentionally a separate system from the autopsy/venue-history feature above — not to be conflated.

### Future scope (bigger, unscoped features — explicitly deferred, not to-dos)
1. **Recurring/repeating events** (e.g. "every Tuesday") — doesn't exist; only one-at-a-time `duplicate_event` today.
2. **Volunteer recommendation engine** — rank/filter the roster by category-skill match and `cached_score` when assigning. Data exists (`Volunteer.skills`, `cached_score`); `list_volunteers` only filters by city today, no ranking.
3. **Auto-push events to BMS/District** at a scheduled time (booking `source` enum already reserves `bms`/`district` for bookings coming back the other way).
4. **Scan participant QR at check-in** — as an alternative/complement to manual entry and CSV-imported booking lookup at the door.
5. **Late-start alerts** — if an event's `starts_at` passes with no check-in yet (still `upcoming` well past its start time), alert someone. Flagged 2026-07-21, explicitly not now.
6. **Performance page** — flagged 2026-07-21 alongside the Decisions/Issues discussion, no shape defined yet (likely rolls up autopsy ratings, issue counts, volunteer reliability across events/venues). Explicitly future, not now.


#id pass 
Role	Name	login_identifier	password
founder	Founder One	founder	password123
city_lead	Priya Nair (Mumbai)	priya	password123
city_lead	Naina Pillai (Bangalore)	naina	password123
event_lead	Kavya Menon (Mumbai)	kavya	password123
volunteer	Riya Malhotra (Mumbai)	riya	password123
volunteer	Aditya Kapoor (Mumbai)	aditya	password123
volunteer	Meera Krishnan (Mumbai)	meera	password123
volunteer	Ishaan Verma (Bangalore)	ishaan	password123
event_lead	Rohan Shetty (Bangalore)	rohan	password123
city_lead	Ananya Kapoor (Delhi)	ananya	password123
volunteer	Simran Oberoi (Mumbai)	simran	password123
volunteer	Dev Anand (Mumbai, inactive)	dev	password123
volunteer	Tanvi Rao (Bangalore)	tanvi	password123
volunteer	Karan Bhatia (Bangalore)	karan	password123
volunteer	Neha Joshi (Bangalore)	neha	password123
volunteer	Arjun Malhotra (Delhi)	arjun	password123
volunteer	Sana Iyer (Delhi)	sana	password123

Demo dataset now spans 3 cities (Mumbai=mature/healthy, Bangalore=growing/mixed, Delhi=new/rocky launch) with 14 events across every lifecycle status (draft/published/started/awaiting_review/closed/cancelled), bookings across every source/status, volunteer assignments across every status with ratings, 5 event autopsies, 4 decisions, 4 issues, and a few notifications. Re-seed via `docker compose exec backend python -m app.scripts.seed` (no-ops if a city already exists — truncate the app tables first to reseed on top of old data).