"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  getEvent,
  listVenues,
  listVolunteers,
  listAssignments,
  getEventReport,
  createEventReport,
  publishEvent,
  cancelEvent,
  completeEvent,
  ApiError,
  type Event,
  type Venue,
  type Volunteer,
  type Assignment,
  type EventReport,
  type ReportTag,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { Tag } from "@/components/ui/Tag";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const STATUS_LABEL: Record<string, string> = { draft: "draft", published: "upcoming", completed: "completed", cancelled: "cancelled" };
const STATUS_TONE: Record<string, "decided" | "open" | "staff"> = {
  completed: "decided",
  published: "open",
  draft: "staff",
  cancelled: "staff",
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function EventDetailPage() {
  const params = useParams<{ cityId: string; eventId: string }>();
  const cityId = Number(params.cityId);
  const eventId = Number(params.eventId);
  const { user, ready } = useRequireAuth("staff");

  const [event, setEvent] = useState<Event | null | undefined>(undefined);
  const [venue, setVenue] = useState<Venue | undefined>(undefined);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [report, setReport] = useState<EventReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

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
        const [venues, assigns, vols] = await Promise.all([
          listVenues(),
          listAssignments({ event_id: eventId }),
          listVolunteers(cityId),
        ]);
        if (cancelled) return;
        setVenue(venues.find((v) => v.id === e.venue_id));
        setAssignments(assigns);
        setVolunteers(vols);
        if (e.status === "completed") {
          try {
            setReport(await getEventReport(eventId));
          } catch {
            setReport(null);
          }
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setEvent(null);
        else setError("Couldn't load this event. Try refreshing.");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, cityId, eventId, refreshKey]);

  if (ready && event === null) notFound();

  if (!ready || !user || event === undefined) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }
  if (error || !event) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
        <StaffHeader user={user} />
        <div style={{ padding: 40, font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--warn-ink)" }}>
          {error ?? "Couldn't load this event."}
        </div>
      </div>
    );
  }

  const refresh = () => setRefreshKey((k) => k + 1);

  async function runAction(fn: () => Promise<unknown>) {
    setActionError(null);
    try {
      await fn();
      refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "That action didn't go through.");
    }
  }

  const assignedVolunteers = assignments
    .map((a) => ({ assignment: a, volunteer: volunteers.find((v) => v.id === a.volunteer_id) }))
    .filter((x) => x.volunteer);

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
          <Badge tone={STATUS_TONE[event.status]}>{STATUS_LABEL[event.status]}</Badge>
          <span
            style={{
              font: "var(--w-bold) 11px/1 var(--font)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            {event.category}
          </span>
        </div>
        <h1 style={{ font: "var(--w-black) 38px/1.15 var(--font)", letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          {event.title}
        </h1>
        <div style={{ font: "var(--w-medium) 15px/1.4 var(--font)", color: "var(--text-muted)", marginBottom: 20 }}>
          {venue?.name} · {venue?.address} · {fmtDate(event.starts_at)} · capacity {event.capacity}
        </div>

        <div style={{ display: "flex", gap: 10, marginBottom: 28, flexWrap: "wrap" }}>
          {event.status === "draft" ? (
            <Button size="sm" onClick={() => runAction(() => publishEvent(event.id))}>
              Publish
            </Button>
          ) : null}
          {event.status === "published" ? (
            <Button size="sm" variant="dark" onClick={() => runAction(() => completeEvent(event.id))}>
              Close out event
            </Button>
          ) : null}
          {event.status === "draft" || event.status === "published" ? (
            <Button size="sm" variant="secondary" onClick={() => runAction(() => cancelEvent(event.id))}>
              Cancel event
            </Button>
          ) : null}
        </div>
        {actionError ? (
          <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginBottom: 16 }}>{actionError}</div>
        ) : null}

        {event.status === "completed" ? (
          <ReportBox eventId={event.id} report={report} onCreated={refresh} />
        ) : (
          <div
            style={{
              background: event.status === "published" ? "var(--accent-tint-2)" : "var(--surface)",
              border: `1px solid ${event.status === "published" ? "var(--accent-tint-border)" : "var(--border)"}`,
              borderRadius: "var(--r-lg)",
              padding: "18px 20px",
              marginBottom: 28,
              font: "var(--w-medium) 14px/1.5 var(--font)",
              color: "var(--text-body)",
            }}
          >
            {event.status === "published"
              ? "This event is published. The assigned volunteer can check people in from their shift view once it starts."
              : event.status === "cancelled"
                ? "This event was cancelled."
                : "This event hasn't been published yet — no report until it's checked in and closed out."}
          </div>
        )}

        <div>
          <div
            style={{
              font: "var(--w-black) 15px/1 var(--font)",
              letterSpacing: "-0.01em",
              borderBottom: "2px solid var(--ink)",
              paddingBottom: 8,
              marginBottom: 8,
            }}
          >
            Assigned volunteers
          </div>
          {assignedVolunteers.length === 0 ? (
            <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>
              No volunteers assigned to this event.
            </div>
          ) : (
            assignedVolunteers.map(({ assignment, volunteer }) => (
              <Link
                key={assignment.id}
                href={`/cities/${cityId}/people/${volunteer!.id}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 0",
                  borderBottom: "1px solid var(--border)",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <span style={{ font: "var(--w-semibold) 15px/1.3 var(--font)" }}>{volunteer!.name}</span>
                <Badge tone={assignment.status === "accepted" ? "decided" : assignment.status === "declined" ? "staff" : "open"}>
                  {assignment.status}
                </Badge>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ReportBox({ eventId, report, onCreated }: { eventId: number; report: EventReport | null; onCreated: () => void }) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createEventReport(eventId, { note: note.trim() });
      setNote("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save this report.");
    } finally {
      setSubmitting(false);
    }
  }

  if (report) {
    return (
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-lg)",
          padding: "20px 22px",
          marginBottom: 28,
        }}
      >
        <div style={{ font: "var(--w-black) 15px/1 var(--font)", marginBottom: 10 }}>Event report</div>
        <p style={{ font: "var(--w-regular) 15px/1.6 var(--font)", color: "var(--text-body)", margin: "0 0 14px" }}>
          {report.note}
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(report.tags ?? []).map((t: ReportTag, i: number) => (
            <Tag key={i} tone={t.tone}>
              {t.label}
            </Tag>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "18px 20px",
        marginBottom: 28,
      }}
    >
      <div style={{ font: "var(--w-black) 15px/1 var(--font)", marginBottom: 10 }}>No report yet</div>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 8 }}>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="How did it go?"
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
        <Button type="submit" size="sm" disabled={submitting || !note.trim()}>
          Save report
        </Button>
      </form>
      {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginTop: 10 }}>{error}</div> : null}
    </div>
  );
}
