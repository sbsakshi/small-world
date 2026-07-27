"use client";

import { useEffect, useState } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  getVolunteer,
  listAssignments,
  listEvents,
  listVenues,
  ApiError,
  type Volunteer,
  type Assignment,
  type Event,
  type Venue,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { Avatar } from "@/components/ui/Avatar";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function PersonProfilePage() {
  const params = useParams<{ cityId: string; volunteerId: string }>();
  const cityId = Number(params.cityId);
  const volunteerId = Number(params.volunteerId);
  const { user, ready } = useRequireAuth("staff");

  const [person, setPerson] = useState<Volunteer | null | undefined>(undefined);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    getVolunteer(volunteerId)
      .then(async (v) => {
        if (cancelled) return;
        if (v.city_id !== cityId) {
          setPerson(null);
          return;
        }
        setPerson(v);
        const [assigns, eventList, venueList] = await Promise.all([
          listAssignments({ volunteer_id: volunteerId }),
          listEvents({ city_id: cityId }),
          listVenues(),
        ]);
        if (cancelled) return;
        setAssignments(assigns);
        setEvents(eventList);
        setVenues(venueList);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setPerson(null);
        else setError("Couldn't load this person.");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, cityId, volunteerId]);

  if (ready && person === null) notFound();

  if (!ready || !user || person === undefined) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }
  if (error || !person) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
        <StaffHeader user={user} />
        <div style={{ padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
          {error ?? "Couldn't load this person."}
        </div>
      </div>
    );
  }

  const initials = person.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const withEvent = assignments
    .map((a) => ({ assignment: a, event: events.find((e) => e.id === a.event_id) }))
    .filter((x) => x.event) as { assignment: Assignment; event: Event }[];
  const upcoming = withEvent.filter(
    (x) => x.event.status === "published" || x.event.status === "draft" || x.event.status === "started"
  );
  const history = withEvent.filter(
    (x) => x.event.status === "closed" || x.event.status === "awaiting_review" || x.event.status === "cancelled"
  );

  function venueName(id: number): string {
    return venues.find((v) => v.id === id)?.name ?? "";
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
      <StaffHeader user={user} />
      <div style={{ maxWidth: 760, margin: "0 auto", padding: "36px 40px" }}>
        <Link
          href={`/cities/${cityId}`}
          style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-muted)", textDecoration: "none" }}
        >
          ‹ Back to city
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: 18, margin: "20px 0 28px" }}>
          <Avatar initials={initials} size={64} />
          <div>
            <h1 style={{ font: "var(--w-black) 28px/1.2 var(--font)", letterSpacing: "-0.02em", margin: 0 }}>{person.name}</h1>
            <div style={{ font: "var(--w-medium) 14px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 2 }}>
              {person.skills.join(", ") || "no skills listed"} · {person.active ? "active" : "inactive"}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, marginBottom: 28 }}>
          <StatCard value={person.events_done} label="nights done" />
          <StatCard value={`${person.cached_score}%`} label="reliability" note="staff only" accent />
          <StatCard value={upcoming.length} label="upcoming shifts" />
        </div>

        <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
          <div style={{ flex: 1, font: "var(--w-medium) 13px/1 var(--font)", color: "var(--text-faint)" }}>
            <div style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-muted)", marginBottom: 4 }}>Phone</div>
            {person.phone}
          </div>
          <div style={{ flex: 1, font: "var(--w-medium) 13px/1 var(--font)", color: "var(--text-faint)" }}>
            <div style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-muted)", marginBottom: 4 }}>Email</div>
            {person.email ?? "—"}
          </div>
        </div>

        {person.remarks ? (
          <div
            style={{
              background: "var(--plain-bg)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--r-lg)",
              padding: "14px 18px",
              margin: "20px 0 28px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <Badge tone="staff">staff only</Badge>
              <span style={{ font: "var(--w-bold) 12px/1 var(--font)", color: "var(--text-muted)" }}>Coordinator remarks</span>
            </div>
            <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-body)" }}>{person.remarks}</div>
          </div>
        ) : null}

        {upcoming.length > 0 ? (
          <div style={{ marginBottom: 28 }}>
            <SectionTitle>Upcoming shifts</SectionTitle>
            {upcoming.map(({ assignment, event }) => (
              <div key={assignment.id} style={{ display: "flex", justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <div style={{ font: "var(--w-semibold) 15px/1.3 var(--font)" }}>{event.title}</div>
                  <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 2 }}>
                    {venueName(event.venue_id)} · {fmtDate(event.starts_at)}
                  </div>
                </div>
                <Badge tone={assignment.status === "accepted" ? "decided" : assignment.status === "declined" ? "staff" : "open"}>
                  {assignment.status}
                </Badge>
              </div>
            ))}
          </div>
        ) : null}

        <div>
          <SectionTitle>Shift history</SectionTitle>
          {history.length === 0 ? (
            <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>No shifts yet.</div>
          ) : (
            history.map(({ assignment, event }) => (
              <div key={assignment.id} style={{ display: "flex", justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <div style={{ font: "var(--w-semibold) 15px/1.3 var(--font)" }}>{event.title}</div>
                  <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 2 }}>
                    {venueName(event.venue_id)} · {fmtDate(event.starts_at)}
                  </div>
                </div>
                <Badge tone={assignment.status === "accepted" ? "decided" : assignment.status === "declined" ? "staff" : "open"}>
                  {assignment.status}
                </Badge>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        font: "var(--w-black) 15px/1 var(--font)",
        letterSpacing: "-0.01em",
        borderBottom: "2px solid var(--ink)",
        paddingBottom: 8,
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}
