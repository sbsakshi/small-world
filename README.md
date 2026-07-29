# Small World OS

Internal operations platform for Small World — a multi-city community events company.

Replaces three things that currently live outside any system: attendee data trapped in third-party ticketing platforms, volunteer coordination running on WhatsApp threads, and institutional knowledge that only exists in people's heads.

---

## Status

This is an early but functional build. Not production-loaded — no real attendee or volunteer data yet.

**Working end-to-end:**
- Event creation
- Volunteer assignment with accept/decline state machine (24-hour expiry job)
- CSV attendee import
- Event-day check-in
- Event autopsy (post-event structured form)
- Issue escalation ladder

**UI only, no backend:**
- Metrics view

**Not built:**
- Volunteer notifications (WhatsApp/messaging delivery)
- Ranked volunteer recommendations by category
- Reassignment alerts on explicit reject

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js | App-router, server components where it helps |
| Backend | FastAPI | Python, async, fast to iterate |
| Database | PostgreSQL | Relational fits the domain; no document store needed |
| Jobs | Procrastinate | Postgres-backed queue — jobs enqueue in the same transaction as the write that triggers them. No separate broker to run or keep in sync. |
| Messaging | Adapter (`MessagingProvider`) | Interface defined; Interakt BSP implementation lands when WhatsApp goes live. Nothing above the adapter knows which provider is behind it. |
| Auth | Username/email + password, cookie sessions | Accounts are admin-created. No self-signup, no OAuth. |

---

## Architecture decisions worth knowing before you read code

**Roles over entities.** There is no `volunteers` table, no `coordinators` table, no `attendees` table. There is a `Person`, and roles attach to that person per-context. The same human can be an attendee at one event, a volunteer at the next, and a city lead over both. Modelling them as separate tables meant duplicated humans and reconciliation logic that would never stay correct.

**Compute, don't store.** Reliability scores, volunteer ratings, and similar derived values are computed from raw lifecycle events (assignment accepted, checked in, no-showed, coordinator note) rather than written to a column. Stored aggregates drift the moment anything is backfilled or corrected. If a score needs to be fast, cache it — don't make it a source of truth.

**Build order follows data gravity.** Systems that *generate* data ship before systems that *consume* it. Event Autopsy exists before Living Playbooks, because a playbook with no autopsies behind it is a blank page. Same reason volunteer recommendations are last: they need assignment history to rank against.

**Single-tenant.** One deployment per client. There is no `tenant_id` on anything. This is deliberate for now — see *Open decisions*.

**Adoption is the hard part, not automation.** The institutional-memory features only work if coordinators actually feed them. Every form in this system should be judged on friction first and completeness second. A 5-minute autopsy that gets filled in beats a 15-minute one that doesn't.

---

## Repo layout

```
backend/       FastAPI app, models, jobs, adapters
frontend/      Next.js app
```

> Confirm against the actual tree before relying on this — adjust if directories have moved.

---

## Local setup

**Requires:** Python 3.11+, Node 20+, PostgreSQL 15+

```bash
# Database
createdb smallworld

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL, SESSION_SECRET
alembic upgrade head
uvicorn app.main:app --reload

# Worker (separate terminal — expiry jobs won't fire without it)
procrastinate --app=app.jobs.app worker

# Frontend
cd frontend
npm install
cp .env.example .env.local    # set NEXT_PUBLIC_API_URL
npm run dev
```

Backend runs on `:8000`, frontend on `:3000`.

> Commands above follow the conventional layout for this stack. Verify the module paths (`app.main:app`, `app.jobs.app`) match the actual code and fix this section if not.

### Creating the first user

There is no signup flow. Accounts are created by an admin, and the first admin has to be seeded directly:

```bash
cd backend
python -m app.scripts.create_user --email you@example.com --role admin
```

---

## Core flows

### Volunteer assignment state machine

```
INVITED ──accept──> ACCEPTED ──check-in──> ATTENDED
   │                   │
   │                   └──no check-in──> NO_SHOW
   ├──decline──> DECLINED
   └──24h no response──> EXPIRED
```

The expiry transition is a Procrastinate job scheduled at invite time, in the same transaction as the invite row. If the invite write rolls back, the job never exists. This is the main reason Procrastinate was chosen over Redis-backed alternatives.

`DECLINED` and `EXPIRED` are different states on purpose — an explicit reject should trigger a reassignment alert (not yet built), a silent expiry probably shouldn't fire the same alarm.

### Issue ladder

Issues escalate volunteer → coordinator → city lead → founder. Each step is recorded, not just the final state. Pattern detection (same issue class three times in 60 days) fires on issue creation.

### Event autopsy

Fires to the coordinator when an event closes. Structured: attendance vs. expected, venue rating, volunteer performance, what worked, what didn't. Future events at the same venue pull the last three autopsies.

The design principle here: **the human contributes judgment, the system contributes context.** The form should never ask for something the system already knows.

---



**Multi-tenancy.** Currently single-tenant, redeploy per client. If Small World OS gets sold to a second client, this needs deciding *before* the schema hardens further. Retrofitting `tenant_id` across a live schema with real data is significantly worse than choosing now.

**Attendee journey scope.** Two paths
- (a) WhatsApp + CSV-compatible flows first — works with existing BookMyShow/District bookings, ships faster
- (b) Full version including a public booking page and payment integration — owns the whole funnel, much larger surface area


---
