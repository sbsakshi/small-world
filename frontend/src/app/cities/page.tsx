"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { listCities, listVenues, listEvents, listIssues, type City, type Venue, type Event, type Issue } from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";

export default function CitiesPage() {
  const { user, ready } = useRequireAuth("staff");
  const [cities, setCities] = useState<City[] | null>(null);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    Promise.all([listCities(), listVenues(), listEvents(), listIssues()])
      .then(([c, v, e, i]) => {
        setCities(c);
        setVenues(v);
        setEvents(e);
        setIssues(i);
      })
      .catch(() => setError("Couldn't load cities. Try refreshing."));
  }, [ready]);

  if (!ready || !user) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
      <StaffHeader user={user} />
      <div style={{ padding: "36px 40px" }}>
        <h1 style={{ font: "var(--w-black) 30px/1.15 var(--font)", letterSpacing: "-0.02em", margin: "0 0 4px" }}>
          Cities
        </h1>
        <p style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-muted)", margin: "0 0 28px" }}>
          Every city you run nights in — venues, events, decisions and issues, all in one place.
        </p>

        {error ? <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>{error}</div> : null}
        {!error && cities === null ? (
          <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-faint)" }}>Loading…</div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {(cities ?? []).map((c) => {
            const cityVenues = venues.filter((v) => v.city_id === c.id);
            const cityEvents = events.filter((e) => e.city_id === c.id);
            const upcoming = cityEvents.filter((e) => e.status === "published").length;
            const openIssues = issues.filter((i) => i.city_id === c.id && i.status === "open").length;
            return (
              <Link
                key={c.id}
                href={`/cities/${c.id}`}
                style={{
                  display: "block",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--r-lg)",
                  padding: "20px 22px",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <div
                  style={{
                    font: "var(--w-bold) 11px/1 var(--font)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "var(--text-faint)",
                  }}
                >
                  {c.active ? "active" : "inactive"}
                </div>
                <div style={{ font: "var(--w-black) 26px/1.2 var(--font)", letterSpacing: "-0.02em", margin: "8px 0 14px" }}>
                  {c.name}
                </div>
                <div style={{ display: "flex", gap: 20 }}>
                  <Stat value={cityVenues.length} label="venues" />
                  <Stat value={upcoming} label="upcoming" />
                  <Stat value={cityEvents.length} label="total events" accent />
                  {openIssues > 0 ? <Stat value={openIssues} label="open issues" alert /> : null}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label, accent, alert }: { value: string | number; label: string; accent?: boolean; alert?: boolean }) {
  return (
    <div>
      <div
        style={{
          font: "var(--w-black) 18px/1 var(--font)",
          color: alert ? "var(--priority-high)" : accent ? "var(--accent-ink)" : "var(--ink)",
        }}
      >
        {value}
      </div>
      <div style={{ font: "var(--w-semibold) 11px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>{label}</div>
    </div>
  );
}
