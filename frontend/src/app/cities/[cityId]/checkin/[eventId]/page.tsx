"use client";

import { useEffect, useState } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { getEvent, listVenues, listBookings, listContacts, checkInBooking, ApiError, type Event, type Venue, type Booking, type Contact } from "@/lib/api";
import { ListRow } from "@/components/ui/ListRow";

export default function CheckinPage() {
  const params = useParams<{ cityId: string; eventId: string }>();
  const cityId = Number(params.cityId);
  const eventId = Number(params.eventId);
  const { user, ready } = useRequireAuth("staff");

  const [event, setEvent] = useState<Event | null | undefined>(undefined);
  const [venue, setVenue] = useState<Venue | undefined>(undefined);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    getEvent(eventId)
      .then(async (e) => {
        if (cancelled) return;
        if (e.city_id !== cityId) {
          setEvent(null);
          return;
        }
        setEvent(e);
        const [venues, bookingList, contactList] = await Promise.all([
          listVenues(),
          listBookings({ event_id: eventId }),
          listContacts(),
        ]);
        if (cancelled) return;
        setVenue(venues.find((v) => v.id === e.venue_id));
        setBookings(bookingList);
        setContacts(contactList);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setEvent(null);
        else setError("Couldn't load this event.");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, cityId, eventId]);

  if (ready && event === null) notFound();

  if (!ready || !user || event === undefined) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }
  if (error || !event) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--canvas)", padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
        {error ?? "Couldn't load this event."}
      </div>
    );
  }

  async function toggle(booking: Booking) {
    if (booking.status === "checked_in") return;
    setPending(booking.id);
    try {
      const updated = await checkInBooking(eventId, booking.id);
      setBookings((bs) => bs.map((b) => (b.id === updated.id ? updated : b)));
    } catch {
      // best-effort: leave the row as-is, the tap can be retried
    } finally {
      setPending(null);
    }
  }

  const count = bookings.filter((b) => b.status === "checked_in").length;
  const remain = event.capacity - count;

  return (
    <div style={{ minHeight: "100vh", background: "var(--canvas)", display: "flex", justifyContent: "center", padding: "24px 0" }}>
      <div
        style={{
          width: 380,
          height: 780,
          background: "var(--surface-sunken)",
          borderRadius: "var(--r-phone)",
          boxShadow: "var(--shadow-phone)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 24px 0" }}>
          <Link href={`/cities/${cityId}/events/${eventId}`} style={{ font: "var(--w-bold) 13px/1 var(--font)", color: "var(--text-muted)", textDecoration: "none" }}>
            ‹ Back
          </Link>
        </div>
        <div style={{ padding: "10px 24px 14px" }}>
          <div
            style={{
              font: "var(--w-bold) 11px/1 var(--font)",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            {event.title} · {venue?.name} · door
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, marginTop: 6 }}>
            <span style={{ font: "var(--w-black) 62px/0.9 var(--font)", letterSpacing: "-0.04em", color: "var(--accent-ink)" }}>
              {count}
            </span>
            <span style={{ font: "var(--w-bold) 26px/1 var(--font)", color: "var(--text-ghost-2)", letterSpacing: "-0.02em", paddingBottom: 6 }}>
              / {event.capacity}
            </span>
            <span style={{ font: "var(--w-semibold) 13px/1 var(--font)", color: "var(--text-muted)", paddingBottom: 9, marginLeft: 2 }}>
              checked in
            </span>
          </div>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {bookings.length === 0 ? (
            <div style={{ padding: "24px", font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>
              No bookings for this event yet.
            </div>
          ) : (
            bookings
              .filter((b) => b.status === "confirmed" || b.status === "checked_in")
              .map((b) => {
                const contact = contacts.find((c) => c.id === b.contact_id);
                return (
                  <ListRow
                    key={b.id}
                    variant="door"
                    name={contact?.name ?? `Booking #${b.id}`}
                    sub={contact?.phone ?? b.source}
                    subDone="checked in"
                    checked={b.status === "checked_in"}
                    onToggle={() => toggle(b)}
                  />
                );
              })
          )}
        </div>
        <div
          style={{
            padding: "14px 22px",
            background: "var(--accent-panel-2)",
            borderTop: "1px solid var(--border-strong)",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <span style={{ font: "var(--w-black) 26px/1 var(--font)", color: "var(--accent-ink)" }}>{Math.max(remain, 0)}</span>
          <span style={{ font: "var(--w-medium) 12.5px/1.35 var(--font)", color: "var(--text-body)" }}>
            not in yet — marked <strong style={{ fontWeight: 700 }}>no-show</strong> automatically when the event is closed out.
          </span>
        </div>
      </div>
    </div>
  );
}
