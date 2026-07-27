"use client";

import { useEffect, useState } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  getVenue,
  listEvents,
  listVenueAutopsies,
  ApiError,
  type Venue,
  type Event,
  type EventAutopsy,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function VenueDetailPage() {
  const params = useParams<{ cityId: string; venueId: string }>();
  const cityId = Number(params.cityId);
  const venueId = Number(params.venueId);
  const { user, ready } = useRequireAuth("staff");

  const [venue, setVenue] = useState<Venue | null | undefined>(undefined);
  const [pastEvents, setPastEvents] = useState<Event[]>([]);
  const [autopsies, setAutopsies] = useState<EventAutopsy[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    getVenue(venueId)
      .then(async (v) => {
        if (cancelled) return;
        if (v.city_id !== cityId) {
          setVenue(null);
          return;
        }
        setVenue(v);
        const [events, autopsyList] = await Promise.all([
          listEvents({ venue_id: venueId, status_: "closed" }),
          listVenueAutopsies(venueId),
        ]);
        if (cancelled) return;
        setPastEvents(events);
        setAutopsies(autopsyList);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 404 || err.status === 403)) setVenue(null);
        else setError("Couldn't load this venue. Try refreshing.");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, cityId, venueId]);

  if (ready && venue === null) notFound();

  if (!ready || !user || venue === undefined) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }
  if (error || !venue) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
        <StaffHeader user={user} />
        <div style={{ padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
          {error ?? "Couldn't load this venue."}
        </div>
      </div>
    );
  }

  const sortedEvents = [...pastEvents].sort(
    (a, b) => new Date(b.starts_at).getTime() - new Date(a.starts_at).getTime()
  );
  const avgVenueRating =
    autopsies.length > 0 ? autopsies.reduce((sum, a) => sum + a.venue_rating, 0) / autopsies.length : null;

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

        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "20px 0 6px", flexWrap: "wrap" }}>
          <Badge tone={venue.active ? "decided" : "staff"}>{venue.active ? "active" : "inactive"}</Badge>
        </div>
        <h1 style={{ font: "var(--w-black) 38px/1.15 var(--font)", letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          {venue.name}
        </h1>
        <div style={{ font: "var(--w-medium) 15px/1.4 var(--font)", color: "var(--text-muted)", marginBottom: 24 }}>
          {venue.address} · capacity {venue.capacity}
        </div>

        <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
          <StatCard value={pastEvents.length} label="events held" />
          <StatCard value={autopsies.length} label="autopsies filed" />
          <StatCard value={avgVenueRating != null ? `${avgVenueRating.toFixed(1)}/5` : "—"} label="avg venue rating" accent />
        </div>

        <div
          style={{
            font: "var(--w-black) 15px/1 var(--font)",
            letterSpacing: "-0.01em",
            borderBottom: "2px solid var(--ink)",
            paddingBottom: 8,
            marginBottom: 8,
          }}
        >
          Past events
        </div>
        {sortedEvents.length === 0 ? (
          <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)", padding: "16px 0" }}>
            No closed-out events at this venue yet.
          </div>
        ) : (
          sortedEvents.map((e) => {
            const autopsy = autopsies.find((a) => a.event_id === e.id);
            return (
              <Link
                key={e.id}
                href={`/cities/${cityId}/events/${e.id}`}
                style={{
                  display: "block",
                  padding: "16px 0",
                  borderBottom: "1px solid var(--border)",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                  <span style={{ font: "var(--w-bold) 17px/1.2 var(--font)", letterSpacing: "-0.01em" }}>{e.title}</span>
                  <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-faint)" }}>
                    {fmtDate(e.starts_at)}
                  </span>
                </div>
                {autopsy ? (
                  <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 6 }}>
                    {autopsy.attendance_actual} attended · venue {autopsy.venue_rating}/5 —{" "}
                    <span style={{ color: "var(--text-body)" }}>{autopsy.what_worked}</span>
                  </div>
                ) : (
                  <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--text-faint)", marginTop: 6 }}>
                    No autopsy filed for this event.
                  </div>
                )}
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
