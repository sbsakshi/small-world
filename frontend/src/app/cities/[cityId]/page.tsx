"use client";

import { useEffect, useState, type FormEvent } from "react";
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
  createDecision,
  createIssue,
  decideDecision,
  resolveIssue,
  ApiError,
  type City,
  type Venue,
  type Event,
  type Decision,
  type Issue,
  type Volunteer,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { NavItem } from "@/components/ui/NavItem";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

type Tab = "Overview" | "Events" | "Decisions" | "Issues" | "People";

const NAV: { key: Tab; icon: string }[] = [
  { key: "Overview", icon: "◎" },
  { key: "Events", icon: "❏" },
  { key: "Decisions", icon: "⚑" },
  { key: "Issues", icon: "◆" },
  { key: "People", icon: "☷" },
];

const STATUS_LABEL: Record<string, string> = { draft: "draft", published: "upcoming", completed: "completed", cancelled: "cancelled" };
const STATUS_TONE: Record<string, "decided" | "open" | "staff"> = {
  completed: "decided",
  published: "open",
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
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      listCities(),
      listVenues(),
      listEvents({ city_id: cityId }),
      listDecisions(cityId),
      listIssues(cityId),
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
  const openDecisions = decisions.filter((d) => d.status === "open");
  const openIssues = issues.filter((i) => i.status === "open");
  const upcomingEvents = events.filter((e) => e.status === "published");
  const completedEvents = events.filter((e) => e.status === "completed");
  const roleLabel = user.role === "founder" ? "full access" : user.role === "city_lead" ? "city lead" : "event lead";

  const highIssue = openIssues.find((i) => i.priority === "high");
  const needsYou = openDecisions[0]
    ? { title: openDecisions[0].text, sub: openDecisions[0].note ?? "open decision" }
    : highIssue
      ? { title: highIssue.text, sub: "high priority · open" }
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
                : n.key === "Decisions"
                  ? String(openDecisions.length)
                  : n.key === "Issues"
                    ? String(openIssues.length)
                    : n.key === "People"
                      ? String(roster.length)
                      : undefined;
            const countTone = n.key === "Issues" ? "alert" : n.key === "Events" ? "accent" : "faint";
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
            {tab === "Overview" && <OverviewTab events={events} cityId={cityId} roster={roster} />}
            {tab === "Events" && <EventsTab events={events} venues={venues} cityId={cityId} />}
            {tab === "Decisions" && (
              <DecisionsTab decisions={decisions} venues={venues} cityId={cityId} onChanged={refresh} />
            )}
            {tab === "Issues" && <IssuesTab issues={issues} venues={venues} cityId={cityId} onChanged={refresh} />}
            {tab === "People" && <PeopleTab people={roster} cityId={cityId} />}
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
                    <Badge tone={d.status === "decided" ? "decided" : "open"}>{d.status}</Badge>
                  </div>
                  <div style={{ font: "var(--w-semibold) 14.5px/1.4 var(--font)", letterSpacing: "-0.01em" }}>{d.text}</div>
                  {d.note ? (
                    <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>
                      {d.note}
                    </div>
                  ) : null}
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
                      background: i.priority === "high" ? "var(--priority-high)" : "var(--priority-low)",
                      marginTop: 6,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ font: "var(--w-semibold) 14.5px/1.4 var(--font)" }}>{i.text}</div>
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

function OverviewTab({ events, cityId, roster }: { events: Event[]; cityId: number; roster: Volunteer[] }) {
  const upcoming = events.filter((e) => e.status === "published");
  const latest = events.filter((e) => e.status === "completed")[0];

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

function EventsTab({ events, venues, cityId }: { events: Event[]; venues: Venue[]; cityId: number }) {
  const upcoming = events.filter((e) => e.status === "published");
  const drafts = events.filter((e) => e.status === "draft");
  const past = events.filter((e) => e.status === "completed" || e.status === "cancelled");

  return (
    <div>
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

function DecisionsTab({
  decisions,
  venues,
  cityId,
  onChanged,
}: {
  decisions: Decision[];
  venues: Venue[];
  cityId: number;
  onChanged: () => void;
}) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createDecision({ city_id: cityId, text: text.trim() });
      setText("");
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't raise this decision.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onDecide(id: number) {
    try {
      await decideDecision(id);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't mark this decided.");
    }
  }

  return (
    <>
      <SectionHeader title="Decision log" sub="most recent first" />
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, margin: "12px 0 20px" }}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Raise a decision…"
          style={{
            flex: 1,
            font: "var(--w-medium) 14px/1 var(--font)",
            padding: "10px 12px",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-md)",
            background: "var(--surface)",
            color: "var(--ink)",
          }}
        />
        <Button type="submit" size="sm" disabled={submitting || !text.trim()}>
          Raise
        </Button>
      </form>
      {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginBottom: 12 }}>{error}</div> : null}
      {decisions.length === 0 ? (
        <EmptyNote>No decisions logged yet.</EmptyNote>
      ) : (
        decisions.map((d) => (
          <div key={d.id} style={{ padding: "18px 0", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
              <Badge tone={d.status === "decided" ? "decided" : "open"}>{d.status}</Badge>
              {d.staff_only ? <Badge tone="staff">staff only</Badge> : null}
              {d.venue_id ? <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{venues.find((v) => v.id === d.venue_id)?.name}</span> : null}
            </div>
            <div style={{ font: "var(--w-bold) 17px/1.4 var(--font)", letterSpacing: "-0.01em" }}>{d.text}</div>
            {d.note ? <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 4 }}>{d.note}</div> : null}
            {d.status === "open" ? (
              <div style={{ marginTop: 10 }}>
                <Button size="sm" variant="secondary" onClick={() => onDecide(d.id)}>
                  Mark decided
                </Button>
              </div>
            ) : null}
          </div>
        ))
      )}
    </>
  );
}

function IssuesTab({
  issues,
  venues,
  cityId,
  onChanged,
}: {
  issues: Issue[];
  venues: Venue[];
  cityId: number;
  onChanged: () => void;
}) {
  const [text, setText] = useState("");
  const [priority, setPriority] = useState<"high" | "low">("low");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createIssue({ city_id: cityId, text: text.trim(), priority });
      setText("");
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't raise this issue.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onResolve(id: number) {
    try {
      await resolveIssue(id);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't resolve this issue.");
    }
  }

  return (
    <>
      <SectionHeader title="Open issues" />
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, margin: "12px 0 20px" }}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Raise an issue…"
          style={{
            flex: 1,
            font: "var(--w-medium) 14px/1 var(--font)",
            padding: "10px 12px",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-md)",
            background: "var(--surface)",
            color: "var(--ink)",
          }}
        />
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as "high" | "low")}
          style={{ font: "var(--w-medium) 14px/1 var(--font)", padding: "10px 12px", borderRadius: "var(--r-md)", border: "1px solid var(--border-strong)" }}
        >
          <option value="low">low</option>
          <option value="high">high</option>
        </select>
        <Button type="submit" size="sm" disabled={submitting || !text.trim()}>
          Raise
        </Button>
      </form>
      {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginBottom: 12 }}>{error}</div> : null}
      {issues.length === 0 ? (
        <EmptyNote>No open issues.</EmptyNote>
      ) : (
        issues.map((i) => (
          <div key={i.id} style={{ display: "flex", gap: 14, padding: "18px 0", borderBottom: "1px solid var(--border)" }}>
            <span
              style={{
                width: 11,
                height: 11,
                borderRadius: "50%",
                background: i.priority === "high" ? "var(--priority-high)" : "var(--priority-low)",
                marginTop: 6,
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ font: "var(--w-semibold) 16px/1.4 var(--font)" }}>{i.text}</span>
                {i.venue_id ? <span style={{ font: "var(--w-medium) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>{venues.find((v) => v.id === i.venue_id)?.name}</span> : null}
              </div>
              <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-faint)" }}>
                {i.priority} priority{i.due_date ? ` · due ${i.due_date}` : ""} · {i.status}
              </div>
              {i.status === "open" ? (
                <div style={{ marginTop: 8 }}>
                  <Button size="sm" variant="secondary" onClick={() => onResolve(i.id)}>
                    Resolve
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        ))
      )}
    </>
  );
}

function PeopleTab({ people, cityId }: { people: Volunteer[]; cityId: number }) {
  return (
    <>
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
