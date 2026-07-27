"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  getEvent,
  listDoorRoster,
  checkInBooking,
  closeDoor,
  ApiError,
  type Event,
  type DoorRosterEntry,
} from "@/lib/api";
import { ListRow } from "@/components/ui/ListRow";
import { Button } from "@/components/ui/Button";

export default function VolunteerCheckinPage() {
  const params = useParams<{ eventId: string }>();
  const router = useRouter();
  const eventId = Number(params.eventId);
  const { user, ready } = useRequireAuth("volunteer");

  const [event, setEvent] = useState<Event | null | undefined>(undefined);
  const [roster, setRoster] = useState<DoorRosterEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    Promise.all([getEvent(eventId), listDoorRoster(eventId)])
      .then(([e, r]) => {
        if (cancelled) return;
        setEvent(e);
        setRoster(r);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setEvent(null);
        else if (err instanceof ApiError && err.status === 403) setForbidden(true);
        else setError("Couldn't load this event.");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, eventId]);

  if (ready && event === null) notFound();

  if (!ready || !user || (event === undefined && !forbidden && !error)) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }

  if (forbidden) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--canvas)", display: "flex", justifyContent: "center", padding: "24px 0" }}>
        <div style={{ width: 380, padding: "60px 24px", textAlign: "center" }}>
          <div style={{ font: "var(--w-bold) 16px/1.4 var(--font)", color: "var(--text-muted)" }}>
            You&apos;re not assigned to this event, or haven&apos;t accepted the assignment yet.
          </div>
          <Link href="/volunteer" style={{ font: "var(--w-bold) 13px/1 var(--font)", color: "var(--accent-link)" }}>
            ‹ Back to your shifts
          </Link>
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--canvas)", padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
        {error ?? "Couldn't load this event."}
      </div>
    );
  }

  async function toggle(entry: DoorRosterEntry) {
    if (entry.status === "checked_in") return;
    setPending(entry.booking_id);
    try {
      await checkInBooking(eventId, entry.booking_id);
      setRoster((rs) => rs.map((r) => (r.booking_id === entry.booking_id ? { ...r, status: "checked_in" } : r)));
    } catch {
      // best-effort: leave the row as-is, the tap can be retried
    } finally {
      setPending(null);
    }
  }

  async function onCloseDoor() {
    setClosing(true);
    try {
      await closeDoor(eventId);
      router.push("/volunteer");
    } catch {
      setClosing(false);
    }
  }

  const count = roster.filter((r) => r.status === "checked_in").length;
  const remain = event.capacity - count;
  const canCloseDoor = event.status === "published" || event.status === "started";

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
          <Link href="/volunteer" style={{ font: "var(--w-bold) 13px/1 var(--font)", color: "var(--text-muted)", textDecoration: "none" }}>
            ‹ Back
          </Link>
          {canCloseDoor ? (
            <Button size="sm" variant="dark" disabled={closing} onClick={onCloseDoor}>
              Close the door
            </Button>
          ) : null}
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
            {event.title} · door
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
          {roster.length === 0 ? (
            <div style={{ padding: "24px", font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>
              No bookings for this event yet.
            </div>
          ) : (
            roster
              .filter((r) => r.status === "confirmed" || r.status === "checked_in")
              .map((r) => (
                <ListRow
                  key={r.booking_id}
                  variant="door"
                  name={r.name}
                  sub={r.phone}
                  subDone="checked in"
                  checked={r.status === "checked_in"}
                  onToggle={() => toggle(r)}
                />
              ))
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
            not in yet — marked <strong style={{ fontWeight: 700 }}>no-show</strong> once the lead reviews the night.
          </span>
        </div>
      </div>
    </div>
  );
}
