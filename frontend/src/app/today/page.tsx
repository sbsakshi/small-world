"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { listEvents, listCities, listVenues, ApiError, type Event, type City, type Venue } from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { Badge } from "@/components/ui/Badge";

const STATUS_LABEL: Record<string, string> = {
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
  cancelled: "staff",
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}

export default function TodayPage() {
  const { user, ready } = useRequireAuth("staff");
  const [events, setEvents] = useState<Event[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    Promise.all([listEvents(), listCities(), listVenues()])
      .then(([e, c, v]) => {
        setEvents(e);
        setCities(c);
        setVenues(v);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load today's events."));
  }, [ready]);

  if (!ready || !user) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }

  const todays = events
    .filter((e) => e.status !== "draft" && isToday(e.starts_at))
    .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());

  const todayLabel = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
      <StaffHeader user={user} />
      <div style={{ maxWidth: 760, margin: "0 auto", padding: "36px 40px" }}>
        <div
          style={{
            font: "var(--w-bold) 12px/1 var(--font)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-faint)",
          }}
        >
          {todayLabel}
        </div>
        <h1 style={{ font: "var(--w-black) 38px/1.15 var(--font)", letterSpacing: "-0.02em", margin: "10px 0 24px" }}>
          Today&apos;s events
        </h1>

        {error ? (
          <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)" }}>{error}</div>
        ) : todays.length === 0 ? (
          <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-faint)" }}>
            Nothing on the calendar for today.
          </div>
        ) : (
          todays.map((e) => {
            const city = cities.find((c) => c.id === e.city_id);
            const venue = venues.find((v) => v.id === e.venue_id);
            return (
              <Link
                key={e.id}
                href={`/cities/${e.city_id}/events/${e.id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: "16px 0",
                  borderBottom: "1px solid var(--border)",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <div
                  style={{
                    font: "var(--w-black) 16px/1 var(--font)",
                    color: "var(--text-faint)",
                    width: 68,
                    flexShrink: 0,
                  }}
                >
                  {fmtTime(e.starts_at)}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <span style={{ font: "var(--w-bold) 18px/1.2 var(--font)", letterSpacing: "-0.01em" }}>{e.title}</span>
                    <Badge tone={STATUS_TONE[e.status] ?? "staff"}>{STATUS_LABEL[e.status] ?? e.status}</Badge>
                  </div>
                  <div style={{ font: "var(--w-medium) 13px/1.3 var(--font)", color: "var(--text-muted)", marginTop: 4 }}>
                    {city?.name ?? "—"} · {venue?.name ?? "—"}
                  </div>
                </div>
                <span style={{ font: "var(--w-bold) 16px/1 var(--font)", color: "var(--text-faint)" }}>›</span>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
