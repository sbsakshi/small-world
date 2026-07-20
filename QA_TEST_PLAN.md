# Small World OS — Manual QA Test Plan

_Last audited: 2026-07-20. This is a manual, human-executable test plan — distinct from and complementary to the automated suite in `backend/tests/` (63 pytest tests as of phase 2). Update this file whenever a module's behavior changes; don't let it drift._

Format: each scenario is one bullet — **ID — Title.** `Pre:` starting state/session. `Steps:` what to do. `Expected:` the specific, checkable outcome (status code, field value, visibility). IDs are stable references, not execution order.

---

## 1. Introduction & Scope

**Purpose:** verify the whole application — org/auth, events, contacts/bookings, volunteers, notifications, jobs, and the phase-2 knowledge system (event autopsies, decisions, issues) — behaves as designed, and surface any gaps between documented intent and actual behavior.

**In scope:** functional correctness of every backend endpoint (role gating, state machines, data validation, cross-module side effects) and the frontend screens that are actually wired to the real API (login, `/cities`, `/cities/{id}`, `/cities/{id}/events/{id}`, per `PROGRESS.md` item 11 — other screens still run on mock data and are out of scope until wired).

**Out of scope:** load/performance testing, pixel-level visual QA, the existing automated pytest suite (already passing; this plan is the manual complement to it), and any payment-provider integration (razorpay/bms/district bookings are modeled but no such integration exists — see §12).

**How to read a scenario:** run `Steps` from the stated `Pre` condition and confirm the system matches `Expected` exactly — a different status code, a leaked field, or a silently-accepted invalid value are all failures, even where no explicit validation was expected (see the many "confirm this is accepted" scenarios below — these pin down currently-permissive behavior so a future regression is detectable).

---

## 2. Test Environment & Preconditions

- Stack: `docker-compose.yml` — `postgres`, `backend` (FastAPI, hot-reload), `worker` (Procrastinate), `frontend` (Next.js). Bring up with `docker compose up`; confirm `GET /health` returns `{"status":"ok"}` before testing.
- Seed data: `backend/app/scripts/seed.py` (founder, 2 cities, 3 venues, 3 staff — one of each role — 4 volunteers with weekly availability, 4 events spanning every status, assignments, bookings including one no-show) and `backend/app/scripts/bootstrap_founder.py` for a fresh DB. Seeding is idempotent — no-ops if a city already exists.
- Recommended test accounts (create beyond seed data as needed to get two of each scoped role):
  - Founder (1 needed — seed provides one)
  - City_lead × 2, one per city ("City A lead", "City B lead")
  - Event_lead × 2 in the **same** city, one leading a given test event and one not, to test the "wrong event_lead" cases
  - Volunteer × 2, ideally in different cities, to test cross-city visibility
- No automated e2e tooling exists (no Playwright/Cypress in `frontend/package.json`) — all UI scenarios in this plan are executed by hand in a browser; all others are executed directly against the API (curl/HTTPie/Postman) since most screens aren't wired yet.
- Timezone: the backend always stores and returns UTC (`DateTime(timezone=True)` everywhere). The frontend renders via `toLocaleString(undefined, …)`, i.e. the **browser's** local timezone, not a hardcoded IST — when testing event/booking/notification timestamps, note both the raw UTC value from the API and what the browser displays, especially if testing from a non-IST timezone.
- Data reset: either re-run `seed.py` against a dropped/recreated database, or track created ids per test session and clean up manually — there is no dedicated test-data reset endpoint.

---

## 3. Cross-Cutting Concerns

_Test once; don't repeat per module unless a module's exact behavior diverges (noted inline in later sections where it does)._

- **CC-1 — No session cookie on a protected endpoint.** Pre: no cookie. Steps: `GET /cities` (or any staff/volunteer endpoint) with no `sw_session` cookie. Expected: `401 Unauthorized`, "Not authenticated".
- **CC-2 — Expired session cookie.** Pre: a session row whose `expires_at` has passed (or manually delete the row from `sessions`). Steps: make any authenticated request with that cookie. Expected: `401`, "Session invalid or expired".
- **CC-3 — Logout invalidates the session immediately.** Pre: logged in. Steps: `POST /auth/logout`, then reuse the same (now-cleared) cookie on any endpoint. Expected: logout returns `{"ok": true}` and deletes the cookie; the reused cookie gets `401`.
- **CC-4 — Staff-only endpoint hit by a volunteer.** Pre: volunteer session. Steps: `GET /cities`, `GET /events`, `GET /staff`, etc. Expected: `403`, role-appropriate message (e.g. "Staff access only").
- **CC-5 — Volunteer-only endpoint hit by staff.** Pre: staff session (any role). Steps: `POST /assignments/{id}/respond`. Expected: `403`, "Volunteer access only".
- **CC-6 — `login_identifier` shared across the staff and volunteer tables.** Pre: create a staff member and a volunteer with the same `login_identifier` but different passwords. Steps: `POST /auth/login` with that identifier and each password in turn. Expected: staff password logs in as staff (`user_type=staff`); volunteer password logs in as that volunteer (`user_type=volunteer`) — `service.login` tries staff first, then volunteer.
- **CC-7 — Malformed JSON body.** Pre: any authenticated session. Steps: `POST /events` (or any POST/PATCH) with an invalid/missing required field. Expected: `422 Unprocessable Entity`, never a `500`.
- **CC-8 — Invalid enum value.** Steps: `POST /events` with `"category": "not-a-real-category"`, or similarly invalid `status`/`role`/`source` elsewhere. Expected: `422`.
- **CC-9 — CORS from an unexpected origin.** Steps: issue a credentialed cross-origin request from an origin other than `settings.frontend_url`. Expected: browser blocks the response (no `Access-Control-Allow-Origin` match) — confirm via browser devtools, not curl (curl ignores CORS).
- **CC-10 — No pagination anywhere.** Steps: seed a few dozen rows into any list endpoint (`/events`, `/contacts`, `/bookings`, `/volunteers`, `/assignments`, `/decisions`, `/issues`, `/notifications`) and call it with no query params. Expected: the full result set is returned in one response every time — confirm this is consistent (not a per-module bug to file individually) and note it if response size ever becomes a real-world concern.
- **CC-11 — 404 takes precedence over 403 for a nonexistent id.** Steps: as an event_lead who doesn't lead any events, `GET /events/999999`. Expected: `404` (not `403`) — spot-checked on events; assumed consistent elsewhere via the same `db.get(...) is None → NotFound` pattern in every service module.
- **CC-12 — Deactivating a staff/volunteer account invalidates their session.** Pre: an active staff member is logged in (cookie held). Steps: an admin sets `active=false` on that staff row via `PATCH /staff/{id}`, then the deactivated user makes any request with their existing cookie. Expected: `401` — `get_current_user` checks `staff.active`/volunteer active on every request, so deactivation takes effect immediately, not just on next login.
- **CC-13 — Systemic absence of field-level bounds validation.** Note, not a single scenario: ratings, capacities, amounts, day-of-week values, and attendance counts have no `ge`/`le`/`min_length` constraints anywhere in the Pydantic schemas found in this codebase. Rather than filing this once, each module section below includes the specific fields affected so each is verified individually — but don't be surprised to find the same root cause repeatedly.

---

## 4. Org Module (Auth, Cities, Venues, Staff)

### Happy path
- **ORG-1 — Founder full CRUD.** Steps: founder creates a city, a venue in it, and a staff member (any role) in it. Expected: all `200`, city/venue/staff visible in subsequent `GET`s.
- **ORG-2 — City_lead scoped visibility.** Pre: city_lead of City A. Steps: `GET /cities`, `/venues`, `/staff`. Expected: only City A's rows returned.
- **ORG-3 — City_lead creates an event_lead in their own city.** Steps: `POST /staff` with `role=event_lead`, `city_id=<own city>`. Expected: `200`.
- **ORG-4 — Founder updates a venue.** Steps: `PATCH /venues/{id}` changing `capacity`/`active`. Expected: `200`, fields updated.
- **ORG-5 — Login then logout.** Steps: `/auth/login` → `/auth/me` reflects correct `role`/`city_id` (volunteer: `role=null`) → `/auth/logout`. Expected: cookie cleared, session row deleted.

### Role & permission edge cases
- **ORG-6 — Event_lead hits any org-admin endpoint.** Steps: `GET`/`POST` on `/cities`, `/venues`, `/staff` as event_lead. Expected: `403` on all of them (`_org_admin = require_roles(founder, city_lead)`).
- **ORG-7 — City_lead attempts to create a city.** Expected: `403`, "Founder access only".
- **ORG-8 — City_lead creates/edits a venue in another city.** Expected: `403`, "Cannot create/edit a venue outside your city".
- **ORG-9 — City_lead creates staff with `role=city_lead` or `role=founder`.** Expected: `403`, "City leads may only create event_leads in their own city".
- **ORG-10 — City_lead creates an event_lead in a *different* city than their own.** Expected: `403`, same message as ORG-9.
- **ORG-11 — City_lead edits an existing founder/city_lead staff row (even in their own city).** Expected: `403`, "Insufficient permissions for this staff member" (`update_staff` blocks touching anyone but an `event_lead`).
- **ORG-12 — City_lead attempts to promote an event_lead to city_lead/founder via `PATCH /staff/{id}`.** Expected: `403`.
- **ORG-13 — City_lead attempts to move a staff member's `city_id` to a different city via update.** Expected: `403`.
- **ORG-14 — Volunteer hits any staff-only org endpoint.** Expected: `403`.

### State-machine / not-found edge cases
- **ORG-15 — Update a nonexistent city/venue/staff id.** Expected: `404` ("City/Venue/Staff not found").

### Data validation edge cases
- **ORG-16 — Staff/volunteer `phone` has no format validation.** Steps: `POST /staff` with `phone: "not a phone"`. Expected: silently accepted `200` — contrast with contacts, which strictly validates via `normalize_phone` (CB-15/16). This asymmetry is a real gap: staff/volunteer phone numbers are never normalized or checked.
- **ORG-17 — Duplicate `login_identifier` within the same table.** Steps: create two staff members with the identical `login_identifier`. Expected: fails at the DB unique-constraint level — confirm whether this surfaces as a clean `409`/`422` or an unhandled `500` (no explicit `AlreadyExists` catch exists in `org/service.py`'s `create_staff`). **Likely a gap** — document whatever actually happens.
- **ORG-18 — Duplicate city name.** Steps: create two cities with the identical `name` (unique constraint on `City.name`). Expected: same concern as ORG-17 — confirm actual status code.
- **ORG-19 — Missing required fields.** Steps: `POST /staff` omitting `role`, or `POST /venues` omitting `capacity`. Expected: `422`.

### Cross-module interlocks
- **ORG-20 — A freshly created event_lead is immediately usable.** Steps: city_lead creates an event_lead (ORG-3), then log in as them, then set them as an event's `lead_id` on `POST /events`. Expected: works end-to-end with no propagation delay.
- **ORG-21 — Deactivated staff keeps their led events untouched.** Steps: deactivate a staff member who leads an event (`active=false`). Expected: their events are unaffected (no cascade); see CC-12 for the session-invalidation half of this.
- **ORG-22 — Login tries staff before volunteer for a shared identifier — verify no silent cross-account bleed.** See CC-6; repeat once here in the org context specifically confirming `role`/`city_id` in `/auth/me` never mixes fields from the wrong account.
- **ORG-23 — City deactivation (`active=false`) doesn't cascade to venues/staff/events in it.** Steps: deactivate a city with existing venues/staff. Expected: venues/staff/events remain readable and functional; `active` is purely a display/filter flag, not an access gate (confirm no endpoint silently 403s just because the parent city is inactive).

---

## 5. Events Module

### Happy path
- **EV-1 — Create a draft event.** Steps: founder/city_lead `POST /events` with valid `category`/`city_id`/`venue_id`/`starts_at`/`capacity`/`lead_id`. Expected: `200`, `status=draft`.
- **EV-2 — Publish a draft.** Steps: `POST /events/{id}/publish`. Expected: `200`, `status=published`; a no-show-sweep job is scheduled for `starts_at + 6h` (verify via `procrastinate_jobs` table, `queueing_lock='no-show-sweep-{id}'`).
- **EV-3 — Update editable fields on a draft or published event.** Steps: `PATCH /events/{id}` changing title/category/venue/starts_at/capacity/lead_id. Expected: `200`, fields updated.
- **EV-4 — Complete a published event.** Steps: `POST /events/{id}/complete`. Expected: `200`, `status=completed`; any still-`confirmed` booking → `no_show`; each `accepted` volunteer assignment's volunteer gets `events_done`++ and a score-recalc job; the no-show-sweep job is cancelled; an autopsy-prompt job and a 48h autopsy-reminder job are both scheduled (chain into §11 E2E-1).
- **EV-5 — Cancel a draft or published event.** Steps: `POST /events/{id}/cancel`. Expected: `200`, `status=cancelled`; every `initiated`/`confirmed` booking on it → `cancelled`, same transaction; no-show-sweep job cancelled.
- **EV-6 — Duplicate an event.** Steps: `POST /events/{id}/duplicate` with a new `starts_at`. Expected: `200`, new event created as `draft` with title/category/city/venue/capacity/lead_id cloned from the source.
- **EV-7 — List/filter events.** Steps: `GET /events?city_id=&venue_id=&status_=`. Expected: correctly filtered, respecting the caller's own role-scoping on top.

### Role & permission edge cases
- **EV-8 — Event_lead attempts to create an event.** Expected: `403` — `create_event` restricts to founder/city_lead only.
- **EV-9 — Event_lead attempts to duplicate an event they lead.** Expected: `403` — `duplicate_event` re-checks the founder/city_lead role even after the lead-access check passes; being the event's own lead is not sufficient.
- **EV-10 — City_lead attempts anything in another city.** Steps: create/view/edit an event in a city that isn't theirs. Expected: `403` throughout.
- **EV-11 — Event_lead attempts any action on an event they don't lead.** Expected: `403` on view/update/publish/cancel/complete.
- **EV-12 — Confirm event_lead has FULL lifecycle control over events they DO lead.** Steps: as the event's own event_lead, `PATCH`, `publish`, `cancel`, and `complete` the event (in the appropriate order/states). Expected: **all succeed** — `update_event`/`publish_event`/`cancel_event`/`complete_event` only call `_ensure_event_access`, with no additional role restriction the way `create_event`/`duplicate_event` have. This is a confirmed behavior, not a bug — verify it explicitly since it's easy to assume event_leads are read-only.
- **EV-13 — Volunteer hits any `/events/*` endpoint.** Expected: `403`.

### State-machine / invalid-transition edge cases
- **EV-14 — Publish an already-published/completed/cancelled event.** Expected: `409`, "Only draft events can be published"; state unchanged.
- **EV-15 — Update a completed or cancelled event.** Expected: `409`, "Event is no longer editable".
- **EV-16 — Cancel an already-cancelled event.** Expected: `409`, "Event is already finalized".
- **EV-17 — Cancel a completed event.** Expected: `409`, same message as EV-16.
- **EV-18 — Complete a draft, cancelled, or already-completed event.** Expected: `409`, "Only published events can be completed".
- **EV-19 — Cancel-cascade only touches `initiated`/`confirmed` bookings.** Steps: cancel an event that has a `checked_in` booking alongside a `confirmed` one. Expected: the `confirmed` booking → `cancelled`; the `checked_in` one is untouched.
- **EV-20 — Complete-driven no-show conversion only touches `confirmed` bookings.** Steps: complete an event with both `confirmed` and `checked_in` bookings. Expected: `confirmed` → `no_show`; `checked_in` untouched.

### Data validation edge cases
- **EV-21 — Event `capacity` is never checked against the venue's `capacity`.** Steps: create/update an event with `capacity` greater than its venue's. Expected: silently accepted — this is a deliberate non-check per the model's own comment, but worth pinning down explicitly.
- **EV-22 — Zero or negative `capacity`.** Expected: silently accepted (no `ge=1` constraint).
- **EV-23 — `starts_at` in the past.** Steps: create/update/duplicate with a past `starts_at`. Expected: silently accepted, no future-date constraint.
- **EV-24 — Invalid `category` enum value.** Expected: `422`.
- **EV-25 — Nonexistent `lead_id`/`venue_id`/`city_id` (bad FK) on create.** Expected: confirm actual behavior — no explicit FK-existence check exists in `create_event`, so this may `500` at the DB constraint level rather than returning a clean error. **Flag whatever actually happens.**

### Cross-module interlocks
- **EV-26 — Publish schedules the no-show sweep; completing/cancelling before it fires cancels the queued job.** Verify directly against `procrastinate_jobs` (row with matching `queueing_lock` disappears), not just the HTTP response.
- **EV-27 — Completing an event with accepted volunteer assignments triggers `events_done`++ and score recalc for each.** Chain into §11 E2E-1.
- **EV-28 — Cancelling an event with existing volunteer assignments — confirm whether assignments are touched.** Steps: cancel an event that has `pending`/`accepted` `VolunteerAssignment` rows. Expected: per the cascade code, only `Booking` rows are touched — assignments are left as-is (still `pending`/`accepted` on a now-cancelled event). Confirm this is really true; it's a plausible gap (a volunteer could stay "accepted" for an event that no longer happens).

---

## 6. Contacts & Bookings Module

### Happy path
- **CB-1 — Manual booking on a published event.** Steps: `POST /bookings/manual` with `event_id` (published), `phone`, `name`, `email`, `amount`. Expected: `200`, `status=confirmed`, `source=manual`; a `Contact` is created or matched by normalized phone.
- **CB-2 — Repeat phone reuses the existing contact.** Steps: submit a second manual booking with the same phone (different event or same). Expected: both bookings reference the same `Contact.id`.
- **CB-3 — CSV import with valid rows.** Steps: `POST /events/{id}/bookings/import` with a `phone,name,email` CSV. Expected: `200`, `created=N`, bookings as `confirmed`/`source=csv`.
- **CB-4 — Re-uploading the identical CSV is a no-op.** Steps: import the same file twice. Expected: second import reports `created=0`, `skipped_duplicate=N`, keyed on `(source=csv, external_id=phone:event_id)`.
- **CB-5 — Check-in a confirmed booking.** Steps: `POST /events/{event_id}/checkin/{booking_id}`. Expected: `200`, `status=checked_in`.
- **CB-6 — Update a contact.** Steps: `PATCH /contacts/{id}` changing name/email/`opted_out`. Expected: `200`.
- **CB-7 — List/filter bookings and contacts.** Steps: `GET /bookings?event_id=`, `GET /contacts?city_id=`. Expected: correctly filtered.

### Role & permission edge cases
- **CB-8 — Confirmed gap: this entire module has NO city or event-lead scoping.** Steps: as an event_lead who belongs to City B and doesn't lead the event in question, call `GET /contacts`, `GET /bookings?event_id=<City-A-event>`, `POST /bookings/manual` against that event, `POST .../checkin/...`, and `POST .../bookings/import`. Expected: **all succeed** — `contacts/router.py` only depends on `require_staff`, with no `_ensure_event_access`/`_ensure_city_access` call anywhere in `contacts/service.py`. This is a genuine cross-city/cross-lead data-access gap, not a hypothetical — confirm it explicitly rather than assuming staff-only is enough scoping.
- **CB-9 — Volunteer hits any contacts/bookings endpoint.** Expected: `403`.

### State-machine / invalid-transition edge cases
- **CB-10 — Manual booking against a draft/completed/cancelled event.** Expected: `409`, "Event is not open for bookings" — only `published` is accepted.
- **CB-11 — CSV import has NO event-status gate.** Steps: import a CSV into a `draft`, `completed`, or `cancelled` event. Expected: **succeeds**, creating `confirmed` bookings regardless of event status — inconsistent with manual booking's stricter published-only gate (CB-10). Follow up by checking-in one of these bookings (should also succeed, since check-in only checks booking status, not event status) — document the full inconsistency.
- **CB-12 — Check in a booking that isn't `confirmed`.** Steps: check in an already-`checked_in`, `cancelled`, `no_show`, or `abandoned` booking. Expected: `409`, "Only confirmed bookings can be checked in".
- **CB-13 — Check in with a mismatched `event_id` in the URL.** Steps: `POST /events/{wrong_event_id}/checkin/{booking_id}` where the booking actually belongs to a different event. Expected: `404`, "Booking not found for this event".
- **CB-14 — Double check-in.** Expected: `409` on the second call.

### Data validation edge cases
- **CB-15 — Phone normalization, valid formats.** Steps: submit `9876543210`, `+919876543210`, `919876543210`, `09876543210`, and spaced/dashed variants. Expected: all normalize to `+91XXXXXXXXXX`.
- **CB-16 — Phone rejection.** Steps: submit numbers not starting with 6/7/8/9, wrong length, or non-numeric garbage. Expected: manual booking → `422`, "Invalid phone number"; CSV row → reported as a per-row error, not a whole-file failure.
- **CB-17 — CSV rows missing phone or name.** Expected: per-row error ("missing phone or name"), rest of the file still processes.
- **CB-18 — Mixed valid/invalid/duplicate CSV in one file.** Expected: correct partition into `created`/`skipped_duplicate`/`errors`, with 1-indexed-from-2 row numbers in errors (header is row 1).
- **CB-19 — Negative `amount` on manual booking.** Expected: silently accepted (no `ge=0` constraint).
- **CB-20 — `BookingStatus.initiated`/`abandoned` and non-manual/csv `BookingSource` values are unreachable.** Note, not a bug: no payment-provider webhook exists yet for razorpay/bms/district, so these values can never actually occur via any current code path — don't spend QA time trying to trigger them.
- **CB-21 — Duplicate phone across two different manual bookings.** Expected: both route to the same `Contact.id` via the phone unique constraint (see CB-2).

### Cross-module interlocks
- **CB-22 — Event cancel cascades to bookings.** See EV-5/EV-19.
- **CB-23 — Event complete flips lingering confirmed bookings to no-show.** See EV-4/EV-20.
- **CB-24 — The 6h no-show sweep job does the same thing independently if staff never manually closes the event.** Chain into §11 E2E-2.

---

## 7. Volunteers Module

### Happy path
- **VOL-1 — Staff creates a volunteer.** Steps: `POST /volunteers` with `skills` (subset of event categories), scoped to caller's city. Expected: `200`.
- **VOL-2 — Volunteer login.** Steps: `/auth/login` with volunteer credentials. Expected: `/auth/me` shows `user_type=volunteer`, `role=null`.
- **VOL-3 — Set weekly availability (full replace).** Steps: `PUT /volunteers/me/availability/weekly` with a new `days` list. Expected: old pattern fully replaced by the new set (not merged).
- **VOL-4 — Set a date override.** Steps: `PUT /volunteers/me/availability/overrides` for a specific date, opposite of the weekly pattern. Expected: overrides the weekly pattern for that date only.
- **VOL-5 — Staff assigns a volunteer to an event.** Steps: `POST /assignments`. Expected: `200`, `status=pending`; a 24h expiry job scheduled (`queueing_lock='assignment-expiry-{id}'`).
- **VOL-6 — Volunteer accepts their own pending assignment.** Steps: `POST /assignments/{id}/respond` with `accept=true`. Expected: `200`, `status=accepted`; expiry job cancelled; score-recalc job scheduled.
- **VOL-7 — Volunteer declines their own pending assignment.** Expected: `status=declined`.
- **VOL-8 — Staff views a volunteer's availability.** Steps: `GET /volunteers/{id}/availability/weekly` and `/overrides`. Expected: `200`, read-only for staff.
- **VOL-9 — List/filter roster by city.** Steps: `GET /volunteers?city_id=`. Expected: correctly filtered.

### Role & permission edge cases
- **VOL-10 — City_lead creates/edits a volunteer in another city.** Expected: `403`, "Cannot create/edit a volunteer outside your city".
- **VOL-11 — A volunteer responds to an assignment that isn't theirs.** Steps: `POST /assignments/{other_volunteer's_id}/respond`. Expected: `404` (not `403` — `respond_to_assignment` raises `NotFound` when `assignment.volunteer_id != volunteer_id`, deliberately not distinguishing "not yours" from "doesn't exist").
- **VOL-12 — Staff attempts to respond to an assignment.** Expected: `403` (`require_volunteer` gate on that route).
- **VOL-13 — Volunteer hits a staff-only roster/assignment endpoint.** Expected: `403`.
- **VOL-14 — Confirmed gap: staff-side volunteer/assignment READS are unscoped by city.** Steps: as a city_lead of City B, `GET /volunteers/{City-A-volunteer-id}`, their availability, and `GET /assignments?event_id=<City-A-event>`. Expected: **all succeed** — `get_volunteer`, the availability-view endpoints, and `list_assignments` (staff) have no `_ensure_city_access` check at all. Any staff role, any city, can read any volunteer's data. Contrast with VOL-1/VOL-10, where *writes* (create/update volunteer) ARE city-scoped — reads are not.
- **VOL-15 — `cached_score`/`events_done` cannot be set via request payload.** Steps: attempt `POST`/`PATCH` a volunteer including `cached_score`/`events_done` in the body. Expected: silently ignored (these fields aren't present in `VolunteerCreate`/`VolunteerUpdate` at all) — confirm the value in the DB is untouched by the request, only ever changed by `mark_events_done`/`recalc_volunteer_score`.

### State-machine / invalid-transition edge cases
- **VOL-16 — Double-respond to the same assignment.** Steps: accept, then accept again (or decline). Expected: `409` on the second call, "Assignment already responded to".
- **VOL-17 — Respond to an already-expired assignment.** Expected: `409`.
- **VOL-18 — The 24h expiry job no-ops if already responded.** Steps: accept an assignment, then manually invoke/wait for its scheduled expiry job. Expected: no change, no duplicate notification.
- **VOL-19 — Expiry job on a nonexistent assignment id.** Expected: clean no-op, no error.

### Data validation edge cases
- **VOL-20 — Weekly availability accepts out-of-range day values.** Steps: `PUT .../availability/weekly` with `days: [7, -1, 99]`. Expected: silently stored as-is — no `0–6` bound check on `WeeklyAvailabilitySet.days`.
- **VOL-21 — Duplicate values in `days` are deduplicated.** Steps: submit `[1, 1, 2]`. Expected: stored as `[1, 2]` (`sorted(set(days))`).
- **VOL-22 — Setting an override for the same date twice.** Expected: second call updates the existing row rather than creating a duplicate.
- **VOL-23 — `create_assignment` has no cross-checks.** Steps: (a) assign a City-B volunteer to a City-A event; (b) assign the same volunteer to the same event a second time while the first assignment is still `pending`/`accepted`; (c) assign a volunteer whose `skills` don't include the event's `category`. Expected: **all three succeed** — no city-match check, no duplicate-assignment check, no skill-match check exists in `create_assignment`. These are three separate, real gaps worth documenting individually since each has a distinct operational consequence.
- **VOL-24 — Volunteer phone/login_identifier have the same lack of normalization as staff (ORG-16).**

### Cross-module interlocks
- **VOL-25 — Assignment acceptance → event completion → `events_done`/`cached_score` update.** Chain into §11 E2E-1.
- **VOL-26 — Assignment expiry → notification to the assigning staff member (`assigned_by`, not the volunteer) → score recalc.** Chain into §11 E2E-3.
- **VOL-27 — Autopsy submission writes `rating`/`coordinator_note` onto this volunteer's assignment row and triggers another score recalc.** Chain into §11 E2E-1. Also confirm `rating` is never exposed back to the volunteer themself via `GET /volunteers/me/assignments` (staff-only data per phase-1 convention) — check both the API response and that the frontend never surfaces it on a volunteer-facing screen.
- **VOL-28 — Score formula sanity check.** Steps: give a volunteer 2 accepted and 1 declined assignment (1 still-pending, uncounted), trigger recalc. Expected: `cached_score = round(100 * 2/3) = 67`.

---

## 8. Notifications Module

### Happy path
- **NOTIF-1 — Inbox listing.** Steps: `GET /notifications`. Expected: caller's own notifications, newest first.
- **NOTIF-2 — Unread-only filter.** Steps: `GET /notifications?unread_only=true`. Expected: only rows with `read_at=null`.
- **NOTIF-3 — Mark read.** Steps: `POST /notifications/{id}/read`. Expected: `read_at` set to current time.
- **NOTIF-4 — Idempotent mark-read.** Steps: mark the same notification read twice. Expected: `200` both times; `read_at` unchanged after the first call (not bumped to a new timestamp on the second).

### Role & permission edge cases
- **NOTIF-5 — Mark/read another user's notification.** Steps: attempt `POST /notifications/{other_staff_or_volunteer's_id}/read`. Expected: `404` (recipient mismatch → `NotFound`, not `403` — deliberately doesn't confirm existence to the wrong caller).
- **NOTIF-6 — Cross-user-type guessing.** Steps: as a volunteer, guess a staff notification's id. Expected: `404`, same as NOTIF-5.

### Data validation edge cases
- **NOTIF-7 — Nonexistent notification id.** Expected: `404`.
- **NOTIF-8 — `read_at` is a timestamp, never a boolean re-null.** Confirm no code path ever clears `read_at` back to null once set.

### Cross-module interlocks
- **NOTIF-9 — `assignment_expired` notification → recipient is `assigned_by`, not the volunteer.** See VOL-26.
- **NOTIF-10 — `autopsy_fill` notification (prompt) → recipient is the event's `lead_id`.** See AUT-17/18.
- **NOTIF-11 — `autopsy_fill` reminder notification only fires if no autopsy exists by +48h.** See JOB-5, AUT-19.
- **NOTIF-12 — Issue notifications follow the escalation ladder's recipient-resolution rules.** Steps: create/escalate issues in each of the three scenarios below and confirm the recipient each time: (a) event-tagged, level=event_lead → that event's lead; (b) venue-tagged only, level=city_lead → that city's city_lead(s); (c) untagged, any level → falls back to all founders. See ISS-4/5/6 for the corresponding issue-side scenarios.

---

## 9. Jobs (Procrastinate)

_Most job effects are exercised via the module scenarios above; this section covers job-specific mechanics not already implied there._

### Happy path
- **JOB-1 — `expire_assignment` fires at +24h with no response.** Expected: `status=expired`, `assigned_by` notified.
- **JOB-2 — `sweep_no_shows` fires at `starts_at+6h`.** Expected: lingering `confirmed` bookings → `no_show`.
- **JOB-3 — `recalc_volunteer_score` formula.** See VOL-28.
- **JOB-4 — `send_autopsy_prompt` fires immediately on event completion.** Expected: notification to the event's lead, `action_type=autopsy_fill`.
- **JOB-5 — `send_autopsy_reminder` fires at +48h only if no autopsy exists yet.** Expected: notification sent if missing; no-op if an autopsy was already submitted.

### State-machine / invalid-transition edge cases
- **JOB-6 — `expire_assignment` on an already-decided assignment.** Expected: no-op, no notification (job checks `status == pending` before acting).
- **JOB-7 — Cancelling an expiry job only removes it if still `todo`.** Note: a job already mid-execution when the volunteer responds is left to run to completion regardless (`cancel_assignment_expiry` deletes by `queueing_lock` where `status='todo'` only) — a race condition, hard to force manually but worth a documented judgment call if reproducible under load.
- **JOB-8 — `sweep_no_shows` no-ops if the event is no longer `published`.** Expected: already-`completed`/`cancelled` events are skipped.
- **JOB-9 — `sweep_no_shows` on a nonexistent event id.** Expected: clean no-op.
- **JOB-10 — `send_autopsy_reminder` no-ops once an autopsy exists.** See AUT-19.
- **JOB-11 — `recalc_volunteer_score` on a volunteer with zero decided assignments.** Expected: no-op, score stays at the default `100`.
- **JOB-12 — Queueing-lock dedup.** Steps: attempt to trigger the same job twice for the same entity (e.g. publish, then somehow re-trigger the sweep schedule). Expected: no duplicate rows in `procrastinate_jobs` for the same `queueing_lock`.

### Cross-module interlocks
- **JOB-13 — `_best_effort` never turns a committed action into a request-level 500.** Steps: if feasible, temporarily stop the `worker`/procrastinate connector mid-request and publish/complete an event. Expected: the business action (event status change) still succeeds and is committed; only the job-scheduling side effect is logged as a failure — this exact bug was found and fixed during phase-1 e2e testing per `PROGRESS.md`, making it a real regression risk worth re-testing, not a hypothetical.
- **JOB-14 — Full lifecycle job chain.** See §11 E2E-1 for the connected narrative across assignment expiry-cancel, score recalc, and autopsy prompt/reminder scheduling and cancellation.

---

## 10. Knowledge Module (Event Autopsies, Decisions, Issues)

### 10.1 Event Autopsies

**Happy path**
- **AUT-1 — Submit an autopsy with no volunteer ratings.** Pre: completed event, caller is its event_lead/city_lead/founder. Steps: `POST /events/{id}/autopsy` with `attendance_actual`, `venue_rating` (1-5), `what_worked`, `what_didnt`, `volunteer_ratings: []`. Expected: `200`.
- **AUT-2 — Submit with volunteer ratings writes through in one transaction.** Steps: include `volunteer_ratings: [{assignment_id, rating, coordinator_note}]` for one or more `accepted` assignments on that event. Expected: `200`; those `VolunteerAssignment` rows now show the given `rating`/`coordinator_note`; a score-recalc job is enqueued per rated volunteer; the 48h reminder job for this event is cancelled.
- **AUT-3 — Any staff can read any autopsy.** Steps: as a city_lead or event_lead with no scope-relationship to the event at all, `GET /events/{id}/autopsy`. Expected: `200` — read access is deliberately unscoped by role/city (only volunteers are excluded).
- **AUT-4 — Venue autopsy history.** Steps: `GET /venues/{id}/autopsies?limit=3`. Expected: most-recent-first, respecting `limit`.
- **AUT-5 — Pending autopsies view.** Steps: as a city_lead, `GET /autopsies/pending`. Expected: only completed events in their own city with no autopsy yet; as founder, all cities.

**Role & permission edge cases**
- **AUT-6 — City_lead submits for a completed event in another city.** Expected: `403`.
- **AUT-7 — Event_lead submits for a completed event they don't lead.** Expected: `403`.
- **AUT-8 — Volunteer hits any autopsy endpoint.** Expected: `403` (staff-only router).
- **AUT-9 — Pending-autopsies scoping cross-check.** Steps: as a city_lead of a city with zero pending autopsies (all events elsewhere), `GET /autopsies/pending`. Expected: empty list, not another city's data.

**State-machine / invalid-transition edge cases**
- **AUT-10 — Submit for a draft/published/cancelled event.** Expected: `409`, "Only completed events can have an autopsy".
- **AUT-11 — Second submission for the same event.** Expected: `409`, "This event already has an autopsy" (`event_id` unique) — even by a different, otherwise-authorized staff member.
- **AUT-12 — No edit/delete endpoint exists.** Confirm there is genuinely no way to correct a submitted autopsy via the API — immutable by design.
- **AUT-13 — Volunteer rating referencing an assignment from a different event.** Expected: `404`.
- **AUT-14 — Volunteer rating referencing a non-`accepted` assignment (still `pending`, or `declined`/`expired`).** Expected: `404`.

**Data validation edge cases**
- **AUT-15 — `venue_rating`/per-volunteer `rating` have no 1–5 bound enforced.** Steps: submit `venue_rating=0`, `999`, or negative. Expected: silently accepted despite the documented 1-5 scale — a real gap between the spec and the schema (`AutopsyCreate`/`AutopsyVolunteerRatingIn` are plain `int`).
- **AUT-16 — `attendance_actual` accepts negative values.** Expected: silently accepted.
- **AUT-17 — Empty-string `what_worked`/`what_didnt`.** Expected: silently accepted (no `min_length`).

**Cross-module interlocks**
- **AUT-18 — Autopsy prompt fires as a job, not synchronously.** Steps: complete an event, then check `procrastinate_jobs`/the lead's notification inbox. Expected: an in-app notification (`action_type=autopsy_fill`) appears for the event's `lead_id`, created by the `send_autopsy_prompt` job, not inline in the `complete` response.
- **AUT-19 — Reminder-cancel-on-submit.** Steps: complete an event (reminder job scheduled at +48h), then submit an autopsy before that window elapses. Expected: the reminder job is deleted from `procrastinate_jobs` (`queueing_lock=autopsy_reminder:{event_id}`); if manually invoked anyway, `send_autopsy_reminder` correctly no-ops since an autopsy now exists.
- **AUT-20 — `list_pending_autopsies` updates same-transaction.** Steps: submit an autopsy, immediately re-check `GET /autopsies/pending`. Expected: that event is gone from the list instantly.

### 10.2 Decisions

**Happy path**
- **DEC-1 — City_lead creates a decision tagged to their own city.** Steps: `POST /decisions` with `title`, `body`, `city_id=<own city>`, optional `venue_id`/`category`, `decided_at`. Expected: `200`.
- **DEC-2 — Company-wide decision.** Steps: `city_id=null`. Expected: `200`, visible to all staff regardless of city.
- **DEC-3 — Founder creates in any city or company-wide.** Expected: `200`.
- **DEC-4 — Any staff (including event_lead) reads/lists/searches decisions.** Steps: `GET /decisions?city_id=&venue_id=&category=&q=`. Expected: `200` for every role, filters apply correctly, `q` does a free-text ILIKE match on title/body.
- **DEC-5 — Edit shows the "edited" signal.** Steps: `PATCH /decisions/{id}` some time after creation. Expected: `updated_at` moves forward while `created_at` stays fixed; the frontend's "edited N days after creation" indicator (city detail page) should trigger once the gap exceeds its threshold.

**Role & permission edge cases**
- **DEC-6 — Event_lead attempts to create or update ANY decision.** Expected: `403` — write access is city_lead+founder only, with zero exceptions (not even for a decision the event_lead would otherwise be scoped to read).
- **DEC-7 — City_lead creates a decision tagged to another city.** Expected: `403`.
- **DEC-8 — City_lead updates an existing decision to re-tag it to another city.** Expected: `403`.
- **DEC-9 — City_lead updates a decision that already belongs to another city, without even changing `city_id`.** Expected: `403` — the check is on the decision's existing `city_id`, not just the payload.
- **DEC-10 — Event_lead reads a decision tagged to a city they're not part of.** Expected: `200` — read truly is unrestricted; confirm no hidden filtering sneaks in.

**Data validation edge cases**
- **DEC-11 — `decided_at` unconstrained relative to `created_at`.** Steps: set `decided_at` far in the future, or long before the record's `created_at`. Expected: both accepted — decisions are explicitly allowed to record something decided before the record itself was written.
- **DEC-12 — Invalid `category` enum value.** Expected: `422`; `null` accepted for company-wide/uncategorized.

**Cross-module interlocks**
- **DEC-13 — A decision tagged to a venue that's later deactivated remains readable.** Expected: no cascade, no broken reference.

### 10.3 Issues

**Happy path**
- **ISS-1 — Volunteer raises an issue with any combination of tags.** Steps: `POST /issues` as a volunteer, with none/one/multiple of `event_id`/`venue_id`/`volunteer_id`. Expected: `200`, `raised_by_type=volunteer`, `current_level=event_lead`.
- **ISS-2 — Staff raises an issue the same way.** Expected: `200`, `raised_by_type=staff`.
- **ISS-3 — Event-tagged issue notifies that event's lead.** See NOTIF-12(a).
- **ISS-4 — Escalate event_lead → city_lead.** Steps: the event's lead (or the raiser) escalates. Expected: `current_level=city_lead`; that city's city_lead(s) notified.
- **ISS-5 — Escalate city_lead → founder.** Expected: `current_level=founder`; all founders notified.
- **ISS-6 — Resolve an open issue with a note.** Steps: whoever holds the current level resolves with `resolution_note`. Expected: `status=resolved`, `resolved_by`/`resolved_at` set.
- **ISS-7 — Pattern-count query.** Steps: `GET /issues/pattern-count?venue_id=` or `?volunteer_id=`. Expected: count of issues (any status) created in the last 60 days about that venue/volunteer.

**Role & permission edge cases**
- **ISS-8 — Volunteer's own issue list is scoped to only their own.** Steps: `GET /issues` as a volunteer who has raised one issue while others exist (raised by other volunteers/staff, some even tagging this volunteer's own `volunteer_id`). Expected: only their own raised issue appears — being the *subject* of an issue (via `volunteer_id`) does not grant visibility.
- **ISS-9 — Volunteer direct-fetches another's issue.** Steps: `GET /issues/{id}` for an issue raised by someone else. Expected: `403`.
- **ISS-10 — Event_lead's issue list.** Expected: only issues at `current_level=event_lead` tagged to an event they lead, OR issues they personally raised (any level/tag) — confirm an event-tagged issue that's already escalated past `event_lead` disappears from this event_lead's list unless they raised it themselves.
- **ISS-11 — City_lead's issue list.** Expected: issues whose derived city (via event→city, else venue→city, else volunteer→city) matches their own city, OR issues they personally raised regardless of derived city — explicitly verify the "OR raised by me" branch works even when the derived city is a *different* city than their own.
- **ISS-12 — Founder sees everything.** Expected: no filtering at all, any tag/level/raiser.
- **ISS-13 — A fully untagged issue (no event/venue/volunteer) is visible only to its raiser and the founder.** Steps: raise a tagless issue as one staff member; attempt to view it as a different city_lead, a different event_lead, and the founder. Expected: only the raiser and founder can see it via list or direct fetch.
- **ISS-14 — Escalate/resolve attempted below the required level.** Steps: an event_lead attempts to escalate/resolve an issue already at `current_level=city_lead` or `founder`. Expected: `403`.
- **ISS-15 — Escalate/resolve attempted by an event_lead who doesn't lead the tagged event.** Expected: `403`, even while `current_level=event_lead`.
- **ISS-16 — Volunteer attempts to escalate or resolve any issue, including one they raised.** Expected: `403` — both actions require staff.
- **ISS-17 — Confirmed view-vs-act asymmetry: a city_lead can ACT on but cannot VIEW a fully untagged issue.** Steps: as a city_lead (not the raiser, not founder), attempt `GET /issues/{id}` on a tagless issue (expect `403`, per ISS-13), then attempt `POST /issues/{id}/escalate` or `/resolve` on the SAME issue. Expected: the escalate/resolve call **succeeds** — `_can_act_on_issue` treats `city_id is None` (undeterminable) as permitted for any city_lead, while `_can_view_issue` requires an exact match or being the raiser. This is a confirmed logic inconsistency in `knowledge/service.py` — a city_lead can blind-act on an issue their own UI would never show them. Document as a finding regardless of whether it's judged acceptable.

**State-machine / invalid-transition edge cases**
- **ISS-18 — Escalate an issue already at `founder`.** Expected: `409` — cannot escalate past the ceiling.
- **ISS-19 — Escalate or resolve an already-resolved issue.** Expected: `409` on both (status must be `open` first).
- **ISS-20 — Resolve then attempt to escalate the same issue.** Expected: `409`.
- **ISS-21 — Double-resolve.** Expected: `409` on the second call.
- **ISS-22 — No auto-escalation ever happens.** Steps: leave an issue untouched at `event_lead` level for an extended period (no job/timer exists for issues, unlike assignments/autopsies). Expected: it never moves on its own — confirm by checking `procrastinate_jobs` has no issue-related scheduled task at all.

**Data validation edge cases**
- **ISS-23 — Confirmed gap: `resolution_note` is documented as required but NOT enforced.** Steps: `POST /issues/{id}/resolve` with `resolution_note: ""`. Expected: check whether this is silently accepted — neither `IssueResolve.resolution_note: str` (no `min_length`) nor `resolve_issue()` itself checks for emptiness, so an empty resolution likely succeeds despite the documented "requires a resolution_note" rule. **Confirm and document the actual result** — this is a real spec-vs-implementation gap.
- **ISS-24 — Issue tagging a nonexistent `event_id`/`venue_id`/`volunteer_id`.** Expected: confirm actual behavior — no FK-existence check exists in `create_issue`.
- **ISS-25 — Pattern-count 60-day boundary.** Steps: create an issue with `created_at` exactly 60 days ago (may require direct DB manipulation to backdate, mirroring the approach in `test_knowledge.py`'s `test_issue_pattern_count_last_60_days`). Expected: confirm whether the boundary is inclusive or exclusive.

**Cross-module interlocks**
- **ISS-26 — Pattern-count is purely informational.** Steps: raise several issues about a volunteer, check the pattern count, then attempt to create a new assignment for that same volunteer. Expected: assignment creation is unaffected — no auto-block, no warning enforced server-side (the count is surfaced at issue-creation time only, per the "visibility, not detection" design).
- **ISS-27 — Cancelling an event tagged by an issue doesn't cascade into the issue.** Steps: cancel an event that has an open issue tagged to it. Expected: the issue's status/level/tags are untouched.

---

## 11. Cross-Module End-to-End Scenarios

_Highest-value scenarios — each chains several modules into one connected story. Run these after the module-level scenarios above have been individually verified._

- **E2E-1 — Full event lifecycle with volunteer + autopsy write-through.** Create a draft event → assign a volunteer (VOL-5) → volunteer accepts (VOL-6, expiry job cancelled, score-recalc queued) → publish (EV-2) → bookings come in via manual entry and/or CSV (CB-1/CB-3) → check some in (CB-5) → complete the event (EV-4: remaining confirmed bookings → no_show; `events_done`++ for the accepted volunteer; autopsy-prompt job fires (AUT-18) and reminder job scheduled) → the lead submits an autopsy with a rating for that volunteer (AUT-2: assignment row updated, reminder cancelled per AUT-19, another score-recalc queued) → confirm the volunteer's `cached_score` reflects the full history (VOL-28-style check), the autopsy shows up in `GET /venues/{id}/autopsies` (AUT-4), and the event disappears from `GET /autopsies/pending` (AUT-20).
- **E2E-2 — No-show sweep safety net vs. manual close-out race.** Publish an event, book several confirmed attendees, let `starts_at+6h` pass without manually completing it — confirm the sweep job marks lingering confirmed bookings as `no_show` (JOB-2). Separately, on a second event, manually complete it just before the sweep would fire and confirm the sweep job was cancelled (EV-26) and, if force-invoked anyway, is a correct no-op (JOB-8) rather than double-processing or erroring.
- **E2E-3 — Assignment non-response escalation chain.** Assign a volunteer, let 24h pass with no response → confirm `expired` status, a notification to `assigned_by` (not the volunteer), and a score recalculation (VOL-26/JOB-1) → have the volunteer then attempt to respond anyway → `409` (VOL-17) → confirm the event can still be completed/cancelled normally with this unresolved assignment sitting there (EV-28-style check for the completed-event case too).
- **E2E-4 — Issue escalation across the org hierarchy tied to an event complaint.** A volunteer raises an issue tagging an event (logistics complaint) → the event's lead is notified (ISS-3) and escalates (ISS-4) → the city's city_lead(s) are notified and escalate (ISS-5) → all founders are notified → a founder resolves with a note (ISS-6). At each step, verify visibility shifts correctly for: the *other* event_lead in the same city (should lose visibility once escalated past `event_lead`, per ISS-10), a city_lead in a *different* city (should never see it, per ISS-11), and the original volunteer raiser (should retain visibility throughout, since raising it grants permanent access regardless of level). Also confirm the pattern-count for that event's venue reflects the new issue within its 60-day window (ISS-7).
- **E2E-5 (optional, if time allows) — Cross-city isolation stress test.** As a City-A city_lead, in one pass: create an event, assign a volunteer, raise an issue, and submit a decision — then confirm zero visibility/mutation leakage into City-B's data at every touchpoint EXCEPT the two confirmed-unscoped areas (contacts/bookings per CB-8, and staff-side volunteer/assignment reads per VOL-14), where leakage is *expected* today rather than a new finding — use this scenario to demonstrate the gap concretely rather than discover it for the first time.

---

## 12. Known Gaps / Judgment Calls

_Consolidated here so each is logged once instead of re-explained in every scenario that touches it. These are confirmed against the actual source (not assumed) as of this audit date._

- **Contacts/bookings module has no city or event-lead scoping at all** (CB-8) — any staff member, any role, any city, can read/write any city's contacts and bookings, including manual bookings, check-ins, and CSV imports against events they have no relationship to.
- **Staff-side volunteer roster reads and assignment listing are unscoped by city** (VOL-14) — writes (create/update volunteer) are city-scoped; reads are not.
- **No field-level bounds validation anywhere in the API** — ratings (1-5 documented, unenforced), event/venue capacity, booking amount, day-of-week, attendance counts. Systemic, not a per-field bug (see CC-13, ORG-16, EV-21/22/23, CB-19, VOL-20, AUT-15/16/17).
- **`resolution_note` non-empty requirement is documented but not enforced in code** (ISS-23).
- **A city_lead can act on (escalate/resolve) but cannot view a fully untagged issue** (ISS-17) — a confirmed logic inconsistency between `_can_view_issue` and `_can_act_on_issue`.
- **`BookingStatus.initiated`/`abandoned` and non-manual/csv `BookingSource` values are unreachable** — no payment-provider integration exists yet (CB-20).
- **CSV import has no event-status gate, unlike manual booking** (CB-11) — can create confirmed bookings on draft/completed/cancelled events.
- **No explicit duplicate-`login_identifier`/duplicate-city-name handling at the service layer** — relies on a raw DB unique constraint with no `AlreadyExists` catch (ORG-17/18) — confirm actual resulting status code when testing rather than assuming a clean error.
- **`create_assignment` has no city-match, duplicate-assignment, or skill-match checks** (VOL-23) — three separate gaps, each with a distinct operational consequence worth noting individually.
- **No pagination on any list endpoint** (CC-10).
- **Event capacity is never validated against venue capacity** — deliberate, per the model's own code comment (EV-21), not a defect.
- **Frontend is still partly on mock data** outside login, `/cities`, `/cities/{id}`, and `/cities/{id}/events/{id}` (per `PROGRESS.md` item 11) — confirm which screen you're testing is actually wired before treating a UI discrepancy as a backend bug.
- **Phase-1 `reports/` module (Decision/Issue/EventReport with priority+due_date+staff_only+open/decided status) has been fully replaced by phase-2 `knowledge/`** — do not test the old shape; it no longer exists in the codebase or database (see `PROGRESS.md`'s "Phase 2" section for the migration details, including the one dev-scratch `event_reports` row that was deliberately not migrated).
