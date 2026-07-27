"use client";

import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  listCities,
  listVenues,
  listEvents,
  listDecisions,
  listIssues,
  listVolunteers,
  listStaff,
  createDecision,
  createIssue,
  escalateIssue,
  resolveIssue,
  createVenue,
  createEvent,
  createStaff,
  createVolunteer,
  ApiError,
  type City,
  type Venue,
  type Event,
  type Decision,
  type Issue,
  type Volunteer,
  type Staff,
  type EventCategory,
  type StaffRole,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { NavItem } from "@/components/ui/NavItem";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { toastSuccess, toastError } from "@/lib/toast";

type Tab = "Overview" | "Events" | "Activity" | "People";

const NAV: { key: Tab; icon: string }[] = [
  { key: "Overview", icon: "◎" },
  { key: "Events", icon: "❏" },
  { key: "Activity", icon: "⚑" },
  { key: "People", icon: "☷" },
];

const STATUS_LABEL: Record<string, string> = {
  draft: "draft",
  published: "upcoming",
  started: "started",
  awaiting_review: "awaiting review",
  closed: "closed",
  cancelled: "cancelled",
};
const STATUS_TONE: Record<string, "decided" | "open" | "staff"> = {
  closed: "decided",
  published: "open",
  started: "open",
  awaiting_review: "staff",
  draft: "staff",
  cancelled: "staff",
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function CityOverviewPage() {
  const params = useParams<{ cityId: string }>();
  const cityId = Number(params.cityId);
  const { user, ready } = useRequireAuth("staff");
  const [tab, setTab] = useState<Tab>("Overview");

  const [city, setCity] = useState<City | null | undefined>(undefined);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [roster, setRoster] = useState<Volunteer[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      listCities(),
      listVenues(),
      listEvents({ city_id: cityId }),
      listDecisions({ cityId }),
      listIssues({ cityId }),
      listVolunteers(cityId),
    ])
      .then(([cities, v, e, d, i, r]) => {
        setCity(cities.find((c) => c.id === cityId) ?? null);
        setVenues(v.filter((x) => x.city_id === cityId));
        setEvents(e);
        setDecisions(d);
        setIssues(i);
        setRoster(r);
      })
      .catch(() => setError("Couldn't load this city. Try refreshing."));
    // Staff listing is founder/city_lead only — fetched separately so an event_lead's
    // 403 here doesn't take down the rest of the page (they can't see this data anyway).
    listStaff()
      .then((s) => setStaff(s.filter((x) => x.city_id === cityId)))
      .catch(() => setStaff([]));
  }, [ready, cityId, refreshKey]);

  if (ready && city === null) notFound();

  if (!ready || !user || city === undefined) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }
  if (error || !city) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
        <StaffHeader user={user} />
        <div style={{ padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
          {error ?? "Couldn't load this city."}
        </div>
      </div>
    );
  }

  const refresh = () => setRefreshKey((k) => k + 1);
  const openIssues = issues.filter((i) => i.status === "open");
  const upcomingEvents = events.filter((e) => e.status === "published" || e.status === "started");
  const completedEvents = events.filter((e) => e.status === "closed");
  const roleLabel = user.role === "founder" ? "full access" : user.role === "city_lead" ? "city lead" : "event lead";

  const oldestOpenIssue = openIssues
    .slice()
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())[0];
  const needsYou = oldestOpenIssue
    ? { title: oldestOpenIssue.title, sub: `open ${issueAgeDays(oldestOpenIssue.created_at)} days` }
    : decisions[0]
      ? { title: decisions[0].title, sub: decisions[0].body }
      : null;

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
      <StaffHeader user={user} />
      <div style={{ display: "flex", minHeight: "calc(100vh - 69px)" }}>
        <aside
          style={{
            width: 236,
            flexShrink: 0,
            background: "var(--accent-panel)",
            borderRight: "1px solid var(--border-strong)",
            display: "flex",
            flexDirection: "column",
            padding: "22px 16px",
          }}
        >
          <Link
            href="/cities"
            style={{
              font: "var(--w-semibold) 12px/1 var(--font)",
              color: "var(--text-muted)",
              textDecoration: "none",
              marginBottom: 18,
              display: "inline-block",
            }}
          >
            ‹ All cities
          </Link>
          <div
            style={{
              font: "var(--w-bold) 11px/1 var(--font)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
              padding: "0 8px 8px",
            }}
          >
            {city.active ? "active city" : "inactive city"}
          </div>
          {NAV.map((n) => {
            const count =
              n.key === "Events"
                ? String(events.length)
                : n.key === "Activity"
                  ? String(decisions.length + issues.length)
                  : n.key === "People"
                    ? String(roster.length)
                    : undefined;
            const countTone = n.key === "Activity" && openIssues.length > 0 ? "alert" : n.key === "Events" ? "accent" : "faint";
            return (
              <NavItem
                key={n.key}
                icon={n.icon}
                label={n.key}
                count={count}
                countTone={countTone}
                active={tab === n.key}
                onClick={() => setTab(n.key)}
              />
            );
          })}
          <div
            style={{
              marginTop: "auto",
              padding: 12,
              borderRadius: "var(--r-md)",
              background: "var(--surface)",
              border: "1px solid var(--border-strong)",
            }}
          >
            <div style={{ font: "var(--w-bold) 12px/1.3 var(--font)" }}>{user.name}</div>
            <div style={{ font: "var(--w-medium) 11.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 1 }}>
              Staff · {roleLabel}
            </div>
          </div>
        </aside>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {tab === "Overview" ? (
            <div style={{ padding: "34px 40px 0" }}>
              <div
                style={{
                  font: "var(--w-bold) 12px/1 var(--font)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--text-faint)",
                }}
              >
                {venues.length} venues
              </div>
              <h2 style={{ font: "var(--w-black) 46px/1 var(--font)", letterSpacing: "-0.03em", margin: "10px 0 6px" }}>
                {city.name}
              </h2>
              <div style={{ font: "var(--w-medium) 15px/1.4 var(--font)", color: "var(--text-muted)" }}>
                {venues.map((v) => v.name).join(" · ") || "No venues yet"}
              </div>
              <div style={{ display: "flex", gap: 12, marginTop: 22 }}>
                <StatCard value={completedEvents.length} label="nights run" />
                <StatCard value={upcomingEvents.length} label="upcoming" accent />
                <StatCard value={venues.length} label="venues" />
              </div>
            </div>
          ) : (
            <div style={{ padding: "28px 40px 0" }}>
              <h2 style={{ font: "var(--w-black) 24px/1 var(--font)", letterSpacing: "-0.02em", margin: 0 }}>{tab}</h2>
            </div>
          )}

          <div style={{ padding: "30px 40px 40px" }}>
            {tab === "Overview" && (
              <OverviewTab
                events={events}
                cityId={cityId}
                roster={roster}
                venues={venues}
                canManageOrg={user.role === "founder" || user.role === "city_lead"}
                onChanged={refresh}
              />
            )}
            {tab === "Events" && (
              <EventsTab
                events={events}
                venues={venues}
                cityId={cityId}
                staff={staff}
                canCreate={user.role === "founder" || user.role === "city_lead"}
                onChanged={refresh}
              />
            )}
            {tab === "Activity" && (
              <ActivityTab decisions={decisions} issues={issues} venues={venues} cityId={cityId} onChanged={refresh} />
            )}
            {tab === "People" && (
              <PeopleTab
                people={roster}
                staff={staff}
                cityId={cityId}
                userRole={user.role}
                onChanged={refresh}
              />
            )}
          </div>
        </div>

        {tab === "Overview" ? (
          <aside
            style={{
              width: 340,
              flexShrink: 0,
              background: "var(--surface)",
              borderLeft: "1px solid var(--border-strong)",
              overflowY: "auto",
              padding: "34px 26px",
            }}
          >
            {needsYou ? (
              <div
                style={{
                  background: "var(--accent-tint-2)",
                  border: "1px solid var(--accent-tint-border)",
                  borderRadius: "var(--r-lg)",
                  padding: "16px 18px",
                  marginBottom: 28,
                }}
              >
                <div
                  style={{
                    font: "var(--w-black) 11px/1 var(--font)",
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--accent-ink)",
                    marginBottom: 6,
                  }}
                >
                  Needs you
                </div>
                <div style={{ font: "var(--w-bold) 16px/1.35 var(--font)", letterSpacing: "-0.01em" }}>{needsYou.title}</div>
                <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 5 }}>
                  {needsYou.sub}
                </div>
              </div>
            ) : null}

            <div style={{ font: "var(--w-black) 15px/1 var(--font)", letterSpacing: "-0.01em", marginBottom: 12 }}>
              Decisions
            </div>
            {decisions.length === 0 ? (
              <EmptyNote>No decisions logged yet.</EmptyNote>
            ) : (
              decisions.slice(0, 5).map((d) => (
                <div key={d.id} style={{ padding: "13px 0", borderBottom: "1px solid var(--border-faint)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                    <span style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-faint)" }}>{d.decided_at}</span>
                  </div>
                  <div style={{ font: "var(--w-semibold) 14.5px/1.4 var(--font)", letterSpacing: "-0.01em" }}>{d.title}</div>
                  <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>
                    {d.body}
                  </div>
                </div>
              ))
            )}

            <div style={{ font: "var(--w-black) 15px/1 var(--font)", letterSpacing: "-0.01em", margin: "26px 0 12px" }}>
              Open issues
            </div>
            {openIssues.length === 0 ? (
              <EmptyNote>No open issues.</EmptyNote>
            ) : (
              openIssues.map((i) => (
                <div key={i.id} style={{ display: "flex", gap: 11, padding: "12px 0", borderBottom: "1px solid var(--border-faint)" }}>
                  <span
                    style={{
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: issueAgeDays(i.created_at) > 7 ? "var(--priority-high)" : "var(--priority-low)",
                      marginTop: 6,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ font: "var(--w-semibold) 14.5px/1.4 var(--font)" }}>{i.title}</div>
                  </div>
                </div>
              ))
            )}
          </aside>
        ) : null}
      </div>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>{children}</div>;
}

function CredentialRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "10px 14px",
        borderRadius: "var(--r-md)",
        background: "var(--surface-sunken)",
        border: "1px solid var(--border-strong)",
      }}
    >
      <span style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-faint)" }}>{label}</span>
      <span style={{ font: "var(--w-bold) 14px/1 var(--font-mono, var(--font))", letterSpacing: "0.02em" }}>{value}</span>
    </div>
  );
}

function generateLoginCredentials(phone: string): { loginIdentifier: string; password: string } {
  const digits = phone.replace(/\D/g, "");
  const loginIdentifier = digits || phone.trim();
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = new Uint32Array(10);
  if (typeof window !== "undefined" && window.crypto) window.crypto.getRandomValues(bytes);
  else for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 4294967296);
  const password = Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
  return { loginIdentifier, password };
}

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        borderBottom: "2px solid var(--ink)",
        paddingBottom: 8,
        marginBottom: 8,
      }}
    >
      <span style={{ font: "var(--w-black) 15px/1 var(--font)", letterSpacing: "-0.01em" }}>{title}</span>
      {sub ? <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{sub}</span> : null}
    </div>
  );
}

function OverviewTab({
  events,
  cityId,
  roster,
  venues,
  canManageOrg,
  onChanged,
}: {
  events: Event[];
  cityId: number;
  roster: Volunteer[];
  venues: Venue[];
  canManageOrg: boolean;
  onChanged: () => void;
}) {
  const upcoming = events.filter((e) => e.status === "published" || e.status === "started");
  const latest = events.filter((e) => e.status === "closed")[0];

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <SectionHeader title="Coming up" sub={`${upcoming.length} scheduled`} />
        {upcoming.length === 0 ? (
          <EmptyNote>Nothing scheduled yet.</EmptyNote>
        ) : (
          upcoming.slice(0, 3).map((e) => <EventRow key={e.id} event={e} cityId={cityId} compact />)
        )}
      </div>

      {latest ? (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="Most recently finished" />
          <EventRow event={latest} cityId={cityId} />
        </div>
      ) : null}

      {canManageOrg ? (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="Venues" sub={`${venues.length} in this city`} />
          <VenuesPanel venues={venues} cityId={cityId} onChanged={onChanged} />
        </div>
      ) : null}

      <div>
        <SectionHeader title="Roster" sub={`${roster.length} volunteers`} />
        {roster.length === 0 ? (
          <EmptyNote>No volunteers assigned yet.</EmptyNote>
        ) : (
          roster.map((p) => (
            <div key={p.id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border-faint)" }}>
              <span style={{ font: "var(--w-semibold) 14.5px/1 var(--font)" }}>{p.name}</span>
              <span style={{ font: "var(--w-medium) 13px/1 var(--font)", color: "var(--text-faint)" }}>{p.cached_score}% reliability</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function VenuesPanel({ venues, cityId, onChanged }: { venues: Venue[]; cityId: number; onChanged: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [capacity, setCapacity] = useState("50");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !address.trim()) return;
    setSubmitting(true);
    try {
      await createVenue({ name: name.trim(), city_id: cityId, address: address.trim(), capacity: Number(capacity) || 1 });
      setName("");
      setAddress("");
      setCapacity("50");
      setShowForm(false);
      toastSuccess(`Venue "${name.trim()}" added.`);
      onChanged();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't create this venue.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {venues.length === 0 ? <EmptyNote>No venues yet.</EmptyNote> : null}
      {venues.map((v) => (
        <Link
          key={v.id}
          href={`/cities/${cityId}/venues/${v.id}`}
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "10px 0",
            borderBottom: "1px solid var(--border-faint)",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          <span style={{ font: "var(--w-semibold) 14.5px/1 var(--font)" }}>{v.name}</span>
          <span style={{ font: "var(--w-medium) 13px/1 var(--font)", color: "var(--text-faint)" }}>
            {v.address} · capacity {v.capacity}
          </span>
        </Link>
      ))}
      <div style={{ marginTop: 12 }}>
        <Button size="sm" variant="secondary" onClick={() => setShowForm(true)}>
          + Add venue
        </Button>
      </div>
      {showForm ? (
        <Modal title="Add venue" onClose={() => setShowForm(false)} width={420}>
          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Venue name">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Venue name…" autoFocus style={fieldStyle} />
            </Field>
            <Field label="Address">
              <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Address…" style={fieldStyle} />
            </Field>
            <Field label="Capacity">
              <input
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
                type="number"
                min={1}
                placeholder="Capacity"
                style={fieldStyle}
              />
            </Field>
            <ModalActions>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !name.trim() || !address.trim()}>
                Add venue
              </Button>
            </ModalActions>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

const inputStyle: CSSProperties = {
  font: "var(--w-medium) 14px/1 var(--font)",
  padding: "10px 12px",
  border: "1px solid var(--border-strong)",
  borderRadius: "var(--r-md)",
  background: "var(--surface)",
  color: "var(--ink)",
};

const fieldStyle: CSSProperties = { ...inputStyle, width: "100%", boxSizing: "border-box" };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-faint)" }}>{label}</span>
      {children}
    </label>
  );
}

function ModalActions({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 6 }}>{children}</div>;
}

function EventsTab({
  events,
  venues,
  cityId,
  staff,
  canCreate,
  onChanged,
}: {
  events: Event[];
  venues: Venue[];
  cityId: number;
  staff: Staff[];
  canCreate: boolean;
  onChanged: () => void;
}) {
  const upcoming = events.filter(
    (e) => e.status === "published" || e.status === "started" || e.status === "awaiting_review"
  );
  const drafts = events.filter((e) => e.status === "draft");
  const past = events.filter((e) => e.status === "closed" || e.status === "cancelled");
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      {canCreate ? (
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
          <Button size="sm" onClick={() => setShowForm(true)}>
            + Add event
          </Button>
        </div>
      ) : null}
      {showForm ? (
        <Modal title="Add event" onClose={() => setShowForm(false)} width={520}>
          <NewEventForm
            venues={venues}
            cityId={cityId}
            staff={staff}
            onCreated={() => {
              onChanged();
              setShowForm(false);
            }}
            onCancel={() => setShowForm(false)}
          />
        </Modal>
      ) : null}
      <div style={{ marginBottom: 28 }}>
        <SectionHeader title="Upcoming" sub={`${upcoming.length} scheduled`} />
        {upcoming.length === 0 ? <EmptyNote>Nothing scheduled yet.</EmptyNote> : upcoming.map((e) => <EventRow key={e.id} event={e} venues={venues} cityId={cityId} />)}
      </div>
      {drafts.length > 0 ? (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="Drafts" sub={`${drafts.length}`} />
          {drafts.map((e) => <EventRow key={e.id} event={e} venues={venues} cityId={cityId} />)}
        </div>
      ) : null}
      <div>
        <SectionHeader title="Past" sub={`${past.length} finished`} />
        {past.length === 0 ? <EmptyNote>No finished events yet.</EmptyNote> : past.map((e) => <EventRow key={e.id} event={e} venues={venues} cityId={cityId} />)}
      </div>
    </div>
  );
}

const CATEGORIES: EventCategory[] = ["art", "social", "wellness", "cooking"];

function NewEventForm({
  venues,
  cityId,
  staff,
  onCreated,
  onCancel,
}: {
  venues: Venue[];
  cityId: number;
  staff: Staff[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const leads = staff.filter((s) => s.role === "event_lead" || s.role === "city_lead" || s.role === "founder");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<EventCategory>("social");
  const [venueId, setVenueId] = useState<string>("");
  const [leadId, setLeadId] = useState<string>("");
  const [startsAt, setStartsAt] = useState("");
  const [capacity, setCapacity] = useState("30");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !venueId || !leadId || !startsAt) return;
    setSubmitting(true);
    try {
      await createEvent({
        title: title.trim(),
        category,
        city_id: cityId,
        venue_id: Number(venueId),
        starts_at: new Date(startsAt).toISOString(),
        capacity: Number(capacity) || 1,
        lead_id: Number(leadId),
      });
      const createdTitle = title.trim();
      setTitle("");
      setStartsAt("");
      setCapacity("30");
      toastSuccess(`"${createdTitle}" created as a draft.`);
      onCreated();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't create this event.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Field label="Event title">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Event title…" autoFocus style={fieldStyle} />
      </Field>
      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1 }}>
          <Field label="Category">
            <select value={category} onChange={(e) => setCategory(e.target.value as EventCategory)} style={fieldStyle}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div style={{ flex: 1 }}>
          <Field label="Venue">
            <select value={venueId} onChange={(e) => setVenueId(e.target.value)} style={fieldStyle}>
              <option value="">Venue…</option>
              {venues.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </div>
      <Field label="Lead">
        <select value={leadId} onChange={(e) => setLeadId(e.target.value)} style={fieldStyle}>
          <option value="">Lead…</option>
          {leads.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </Field>
      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 2 }}>
          <Field label="Starts at">
            <input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} style={fieldStyle} />
          </Field>
        </div>
        <div style={{ flex: 1 }}>
          <Field label="Capacity">
            <input
              type="number"
              min={1}
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              placeholder="Capacity"
              style={fieldStyle}
            />
          </Field>
        </div>
      </div>
      <ModalActions>
        <Button type="button" size="sm" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={submitting || !title.trim() || !venueId || !leadId || !startsAt}>
          Create draft
        </Button>
      </ModalActions>
    </form>
  );
}

function EventRow({ event: e, venues, cityId, compact = false }: { event: Event; venues?: Venue[]; cityId: number; compact?: boolean }) {
  const venueName = venues?.find((v) => v.id === e.venue_id)?.name;
  return (
    <Link
      href={`/cities/${cityId}/events/${e.id}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: compact ? "12px 0" : "16px 0",
        borderBottom: "1px solid var(--border)",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ font: `var(--w-bold) ${compact ? "16px" : "18px"}/1.2 var(--font)`, letterSpacing: "-0.01em" }}>{e.title}</span>
          <Badge tone={STATUS_TONE[e.status]}>{STATUS_LABEL[e.status]}</Badge>
        </div>
        <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-muted)", marginTop: 4 }}>
          {venueName ? `${venueName} · ` : ""}
          {fmtDate(e.starts_at)} · capacity {e.capacity}
        </div>
      </div>
      <span style={{ font: "var(--w-bold) 16px/1 var(--font)", color: "var(--text-faint)" }}>›</span>
    </Link>
  );
}

function issueAgeDays(createdAt: string): number {
  return Math.floor((Date.now() - new Date(createdAt).getTime()) / 86_400_000);
}

function DecisionRow({ decision: d, venues }: { decision: Decision; venues: Venue[] }) {
  const edited = new Date(d.updated_at).getTime() - new Date(d.created_at).getTime() > 60_000;
  return (
    <div style={{ display: "flex", gap: 14, padding: "18px 0", borderBottom: "1px solid var(--border)" }}>
      <Badge tone="staff">decision</Badge>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
          <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{d.decided_at}</span>
          {d.category ? <Badge tone="staff">{d.category}</Badge> : null}
          {d.venue_id ? <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{venues.find((v) => v.id === d.venue_id)?.name}</span> : null}
          {edited ? <span style={{ font: "var(--w-medium) 12px/1 var(--font)", color: "var(--text-faint)" }}>edited</span> : null}
        </div>
        <div style={{ font: "var(--w-bold) 17px/1.4 var(--font)", letterSpacing: "-0.01em" }}>{d.title}</div>
        <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 4 }}>{d.body}</div>
      </div>
    </div>
  );
}

function IssueRow({
  issue: i,
  venues,
  resolvingId,
  resolutionNote,
  onResolutionNoteChange,
  onEscalate,
  onStartResolve,
  onResolve,
}: {
  issue: Issue;
  venues: Venue[];
  resolvingId: number | null;
  resolutionNote: string;
  onResolutionNoteChange: (note: string) => void;
  onEscalate: (id: number) => void;
  onStartResolve: (id: number) => void;
  onResolve: (id: number) => void;
}) {
  const age = issueAgeDays(i.created_at);
  return (
    <div style={{ display: "flex", gap: 14, padding: "18px 0", borderBottom: "1px solid var(--border)" }}>
      <span
        style={{
          width: 11,
          height: 11,
          borderRadius: "50%",
          background: i.status === "open" && age > 7 ? "var(--priority-high)" : "var(--priority-low)",
          marginTop: 6,
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
          <Badge tone="open">issue</Badge>
          <span style={{ font: "var(--w-semibold) 16px/1.4 var(--font)" }}>{i.title}</span>
          <Badge tone={i.status === "resolved" ? "decided" : "open"}>{i.status}</Badge>
          <Badge tone="staff">{i.current_level.replace("_", " ")}</Badge>
          {i.venue_id ? <span style={{ font: "var(--w-medium) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{venues.find((v) => v.id === i.venue_id)?.name}</span> : null}
        </div>
        <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-faint)" }}>{i.body}</div>
        <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: age > 7 ? "var(--priority-high)" : "var(--text-faint)", marginTop: 4 }}>
          open {age} {age === 1 ? "day" : "days"}
        </div>
        {i.status === "resolved" && i.resolution_note ? (
          <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--good-ink)", marginTop: 4 }}>{i.resolution_note}</div>
        ) : null}
        {i.status === "open" ? (
          <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {i.current_level !== "founder" ? (
              <Button size="sm" variant="secondary" onClick={() => onEscalate(i.id)}>
                Escalate
              </Button>
            ) : null}
            {resolvingId === i.id ? (
              <>
                <input
                  value={resolutionNote}
                  onChange={(e) => onResolutionNoteChange(e.target.value)}
                  placeholder="Resolution note…"
                  autoFocus
                  style={{
                    font: "var(--w-medium) 13px/1 var(--font)",
                    padding: "8px 10px",
                    border: "1px solid var(--border-strong)",
                    borderRadius: "var(--r-md)",
                    background: "var(--surface)",
                    color: "var(--ink)",
                  }}
                />
                <Button size="sm" disabled={!resolutionNote.trim()} onClick={() => onResolve(i.id)}>
                  Confirm resolve
                </Button>
              </>
            ) : (
              <Button size="sm" variant="secondary" onClick={() => onStartResolve(i.id)}>
                Resolve
              </Button>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

type ActivityEntry = { ts: number } & ({ type: "decision"; decision: Decision } | { type: "issue"; issue: Issue });

function ActivityTab({
  decisions,
  issues,
  venues,
  cityId,
  onChanged,
}: {
  decisions: Decision[];
  issues: Issue[];
  venues: Venue[];
  cityId: number;
  onChanged: () => void;
}) {
  const [showDecisionForm, setShowDecisionForm] = useState(false);
  const [showIssueForm, setShowIssueForm] = useState(false);
  const [decisionTitle, setDecisionTitle] = useState("");
  const [decisionBody, setDecisionBody] = useState("");
  const [issueTitle, setIssueTitle] = useState("");
  const [issueBody, setIssueBody] = useState("");
  const [issueVenueId, setIssueVenueId] = useState<number | "">(venues[0]?.id ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");

  async function onSubmitDecision(e: FormEvent) {
    e.preventDefault();
    if (!decisionTitle.trim() || !decisionBody.trim()) return;
    setSubmitting(true);
    try {
      await createDecision({
        city_id: cityId,
        title: decisionTitle.trim(),
        body: decisionBody.trim(),
        decided_at: new Date().toISOString().slice(0, 10),
      });
      setDecisionTitle("");
      setDecisionBody("");
      setShowDecisionForm(false);
      toastSuccess("Decision logged.");
      onChanged();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't raise this decision.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onSubmitIssue(e: FormEvent) {
    e.preventDefault();
    if (!issueTitle.trim() || !issueBody.trim() || !issueVenueId) return;
    setSubmitting(true);
    try {
      await createIssue({ title: issueTitle.trim(), body: issueBody.trim(), venue_id: Number(issueVenueId) });
      setIssueTitle("");
      setIssueBody("");
      setShowIssueForm(false);
      toastSuccess("Issue raised.");
      onChanged();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't raise this issue.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onEscalate(id: number) {
    try {
      await escalateIssue(id);
      toastSuccess("Issue escalated.");
      onChanged();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't escalate this issue.");
    }
  }

  async function onResolve(id: number) {
    if (!resolutionNote.trim()) return;
    try {
      await resolveIssue(id, resolutionNote.trim());
      setResolvingId(null);
      setResolutionNote("");
      toastSuccess("Issue resolved.");
      onChanged();
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Couldn't resolve this issue.");
    }
  }

  const feed: ActivityEntry[] = [
    ...decisions.map((decision) => ({ type: "decision" as const, decision, ts: new Date(decision.created_at).getTime() })),
    ...issues.map((issue) => ({ type: "issue" as const, issue, ts: new Date(issue.created_at).getTime() })),
  ].sort((a, b) => b.ts - a.ts);

  return (
    <>
      <SectionHeader title="Activity" sub="decisions & issues, most recent first" />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, margin: "12px 0 20px" }}>
        <Button size="sm" variant="secondary" onClick={() => setShowIssueForm(true)}>
          + Add issue
        </Button>
        <Button size="sm" onClick={() => setShowDecisionForm(true)}>
          + Add decision
        </Button>
      </div>
      {showDecisionForm ? (
        <Modal title="Add decision" onClose={() => setShowDecisionForm(false)} width={480}>
          <form onSubmit={onSubmitDecision} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Title">
              <input value={decisionTitle} onChange={(e) => setDecisionTitle(e.target.value)} placeholder="Decision title…" autoFocus style={fieldStyle} />
            </Field>
            <Field label="Why? (the reasoning behind it)">
              <input value={decisionBody} onChange={(e) => setDecisionBody(e.target.value)} placeholder="What was decided and why…" style={fieldStyle} />
            </Field>
            <ModalActions>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowDecisionForm(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !decisionTitle.trim() || !decisionBody.trim()}>
                Raise
              </Button>
            </ModalActions>
          </form>
        </Modal>
      ) : null}
      {showIssueForm ? (
        <Modal title="Add issue" onClose={() => setShowIssueForm(false)} width={480}>
          <form onSubmit={onSubmitIssue} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Title">
              <input value={issueTitle} onChange={(e) => setIssueTitle(e.target.value)} placeholder="Issue title…" autoFocus style={fieldStyle} />
            </Field>
            <Field label="What's going on?">
              <input value={issueBody} onChange={(e) => setIssueBody(e.target.value)} placeholder="Describe the issue…" style={fieldStyle} />
            </Field>
            <Field label="Venue">
              <select
                value={issueVenueId}
                onChange={(e) => setIssueVenueId(e.target.value ? Number(e.target.value) : "")}
                style={fieldStyle}
              >
                {venues.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </Field>
            <ModalActions>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowIssueForm(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !issueTitle.trim() || !issueBody.trim() || !issueVenueId}>
                Raise
              </Button>
            </ModalActions>
          </form>
        </Modal>
      ) : null}
      {feed.length === 0 ? (
        <EmptyNote>No decisions or issues logged yet.</EmptyNote>
      ) : (
        feed.map((entry) =>
          entry.type === "decision" ? (
            <DecisionRow key={`decision-${entry.decision.id}`} decision={entry.decision} venues={venues} />
          ) : (
            <IssueRow
              key={`issue-${entry.issue.id}`}
              issue={entry.issue}
              venues={venues}
              resolvingId={resolvingId}
              resolutionNote={resolutionNote}
              onResolutionNoteChange={setResolutionNote}
              onEscalate={onEscalate}
              onStartResolve={(id) => {
                setResolvingId(id);
                setResolutionNote("");
              }}
              onResolve={onResolve}
            />
          )
        )
      )}
    </>
  );
}

function PeopleTab({
  people,
  staff,
  cityId,
  userRole,
  onChanged,
}: {
  people: Volunteer[];
  staff: Staff[];
  cityId: number;
  userRole: StaffRole | null;
  onChanged: () => void;
}) {
  const canManageOrg = userRole === "founder" || userRole === "city_lead";
  const [showForm, setShowForm] = useState(false);
  const [credentials, setCredentials] = useState<{ name: string; loginIdentifier: string; password: string } | null>(null);

  return (
    <>
      {canManageOrg ? (
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
          <Button size="sm" onClick={() => setShowForm(true)}>
            + Add staff
          </Button>
        </div>
      ) : null}
      {showForm ? (
        <Modal title="Add staff" onClose={() => setShowForm(false)} width={460}>
          <AddPersonForm
            cityId={cityId}
            userRole={userRole}
            onCreated={(created) => {
              onChanged();
              setShowForm(false);
              setCredentials(created);
            }}
            onCancel={() => setShowForm(false)}
          />
        </Modal>
      ) : null}
      {credentials ? (
        <Modal title="Account created" onClose={() => setCredentials(null)} width={420}>
          <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-muted)", marginBottom: 16 }}>
            Share these login details with {credentials.name} — this password won&apos;t be shown again.
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
            <CredentialRow label="Username" value={credentials.loginIdentifier} />
            <CredentialRow label="Password" value={credentials.password} />
          </div>
          <ModalActions>
            <Button size="sm" onClick={() => setCredentials(null)}>
              Done
            </Button>
          </ModalActions>
        </Modal>
      ) : null}

      {canManageOrg ? (
        <div style={{ marginBottom: 28 }}>
          <SectionHeader title="Staff" sub={`${staff.length} in this city`} />
          {staff.length === 0 ? (
            <EmptyNote>No staff assigned yet.</EmptyNote>
          ) : (
            staff.map((s) => (
              <div key={s.id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border-faint)" }}>
                <span style={{ font: "var(--w-semibold) 14.5px/1 var(--font)" }}>{s.name}</span>
                <span style={{ font: "var(--w-medium) 13px/1 var(--font)", color: "var(--text-faint)" }}>
                  {s.role.replace("_", " ")}
                </span>
              </div>
            ))
          )}
        </div>
      ) : null}

      <SectionHeader title="People" sub={`${people.length} volunteers`} />
      {people.length === 0 ? (
        <EmptyNote>No volunteers in this city yet.</EmptyNote>
      ) : (
        people.map((p) => {
          const initials = p.name
            .split(" ")
            .map((s) => s[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
          return (
            <Link
              key={p.id}
              href={`/cities/${cityId}/people/${p.id}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "16px 0",
                borderBottom: "1px solid var(--border)",
                textDecoration: "none",
                color: "inherit",
                cursor: "pointer",
              }}
            >
              <span
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  background: "var(--accent-tint)",
                  color: "var(--accent-ink)",
                  font: "var(--w-bold) 15px/1 var(--font)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {initials}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ font: "var(--w-semibold) 16px/1.2 var(--font)" }}>{p.name}</div>
                <div style={{ font: "var(--w-medium) 13px/1.2 var(--font)", color: "var(--text-faint)", marginTop: 2 }}>
                  {p.skills.join(", ") || "no skills listed"}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ font: "var(--w-bold) 15px/1 var(--font)" }}>{p.events_done} nights</div>
                <div style={{ font: "var(--w-medium) 12px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>
                  {p.cached_score}% reliability · staff only
                </div>
              </div>
              <span style={{ font: "var(--w-bold) 16px/1 var(--font)", color: "var(--text-faint)", marginLeft: 4 }}>›</span>
            </Link>
          );
        })
      )}
    </>
  );
}

const SKILLS: EventCategory[] = ["art", "social", "wellness", "cooking"];

type PersonType = "staff" | "volunteer";

function AddPersonForm({
  cityId,
  userRole,
  onCreated,
  onCancel,
}: {
  cityId: number;
  userRole: StaffRole | null;
  onCreated: (created: { name: string; loginIdentifier: string; password: string }) => void;
  onCancel: () => void;
}) {
  const [type, setType] = useState<PersonType>("staff");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<StaffRole>("event_lead");
  const [skills, setSkills] = useState<EventCategory[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleSkill(s: EventCategory) {
    setSkills((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !phone.trim()) return;
    setSubmitting(true);
    setError(null);
    const { loginIdentifier, password } = generateLoginCredentials(phone);
    try {
      if (type === "staff") {
        await createStaff({
          name: name.trim(),
          phone: phone.trim(),
          login_identifier: loginIdentifier,
          password,
          role: userRole === "founder" ? role : "event_lead",
          city_id: cityId,
        });
      } else {
        await createVolunteer({
          name: name.trim(),
          phone: phone.trim(),
          login_identifier: loginIdentifier,
          password,
          city_id: cityId,
          skills,
        });
      }
      onCreated({ name: name.trim(), loginIdentifier, password });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Couldn't create this ${type === "staff" ? "staff member" : "volunteer"}.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Field label="Type">
        <div style={{ display: "flex", gap: 6 }}>
          {(["staff", "volunteer"] as PersonType[]).map((t) => (
            <button
              type="button"
              key={t}
              onClick={() => setType(t)}
              style={{
                flex: 1,
                font: "var(--w-semibold) 13px/1 var(--font)",
                padding: "10px 12px",
                borderRadius: "var(--r-md)",
                border: `1px solid ${type === t ? "var(--accent)" : "var(--border-strong)"}`,
                background: type === t ? "var(--accent-tint)" : "var(--surface)",
                color: type === t ? "var(--accent-ink)" : "var(--text-muted)",
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </Field>
      <Field label="Name">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name…" autoFocus style={fieldStyle} />
      </Field>
      <Field label="Phone">
        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone…" style={fieldStyle} />
      </Field>
      {type === "staff" ? (
        userRole === "founder" ? (
          <Field label="Role">
            <select value={role} onChange={(e) => setRole(e.target.value as StaffRole)} style={fieldStyle}>
              <option value="event_lead">event lead</option>
              <option value="city_lead">city lead</option>
            </select>
          </Field>
        ) : (
          <div style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>Role: event lead</div>
        )
      ) : (
        <Field label="Tags (optional)">
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {SKILLS.map((s) => (
              <button
                type="button"
                key={s}
                onClick={() => toggleSkill(s)}
                style={{
                  font: "var(--w-semibold) 12px/1 var(--font)",
                  padding: "9px 10px",
                  borderRadius: "var(--r-md)",
                  border: `1px solid ${skills.includes(s) ? "var(--accent)" : "var(--border-strong)"}`,
                  background: skills.includes(s) ? "var(--accent-tint)" : "var(--surface)",
                  color: skills.includes(s) ? "var(--accent-ink)" : "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </Field>
      )}
      {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)" }}>{error}</div> : null}
      <ModalActions>
        <Button type="button" size="sm" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={submitting || !name.trim() || !phone.trim()}>
          {type === "staff" ? "Add staff" : "Add volunteer"}
        </Button>
      </ModalActions>
    </form>
  );
}
