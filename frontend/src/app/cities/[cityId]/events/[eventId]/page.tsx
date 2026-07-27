"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  getEvent,
  listVenues,
  listVolunteers,
  listAssignments,
  listBookings,
  listContacts,
  getAutopsy,
  submitAutopsy,
  publishEvent,
  cancelEvent,
  closeDoor,
  createAssignment,
  createManualBooking,
  importBookingsCsv,
  ApiError,
  type Event,
  type Venue,
  type Volunteer,
  type Assignment,
  type EventAutopsy,
  type Booking,
  type Contact,
} from "@/lib/api";
import { StaffHeader } from "@/components/StaffHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

const fieldStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  font: "var(--w-medium) 14px/1 var(--font)",
  padding: "10px 12px",
  border: "1px solid var(--border-strong)",
  borderRadius: "var(--r-md)",
  background: "var(--surface)",
  color: "var(--ink)",
};

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
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [autopsy, setAutopsy] = useState<EventAutopsy | null>(null);
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
        const [venues, assigns, vols, bks, cts] = await Promise.all([
          listVenues(),
          listAssignments({ event_id: eventId }),
          listVolunteers(cityId),
          listBookings({ event_id: eventId }),
          listContacts(cityId),
        ]);
        if (cancelled) return;
        setVenue(venues.find((v) => v.id === e.venue_id));
        setAssignments(assigns);
        setVolunteers(vols);
        setBookings(bks);
        setContacts(cts);
        if (e.status === "awaiting_review" || e.status === "closed") {
          try {
            setAutopsy(await getAutopsy(eventId));
          } catch {
            setAutopsy(null);
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
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <Link
            href={`/cities/${cityId}`}
            style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-muted)", textDecoration: "none" }}
          >
            ‹ Back to city
          </Link>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {event.status === "draft" ? (
              <Button size="sm" onClick={() => runAction(() => publishEvent(event.id))}>
                Publish
              </Button>
            ) : null}
            {event.status === "published" || event.status === "started" ? (
              <Button size="sm" variant="dark" onClick={() => runAction(() => closeDoor(event.id))}>
                Close the door
              </Button>
            ) : null}
            {event.status === "draft" || event.status === "published" || event.status === "started" ? (
              <Button size="sm" variant="secondary" onClick={() => runAction(() => cancelEvent(event.id))}>
                Cancel event
              </Button>
            ) : null}
          </div>
        </div>
        {actionError ? (
          <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginTop: 12 }}>{actionError}</div>
        ) : null}

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
        <div style={{ font: "var(--w-medium) 15px/1.4 var(--font)", color: "var(--text-muted)", marginBottom: 28 }}>
          {venue?.name} · {venue?.address} · {fmtDate(event.starts_at)} · capacity {event.capacity}
        </div>

        {event.status === "awaiting_review" || event.status === "closed" ? (
          <AutopsyBox
            eventId={event.id}
            autopsy={autopsy}
            assignments={assignments}
            volunteers={volunteers}
            onCreated={refresh}
          />
        ) : (
          <div
            style={{
              background:
                event.status === "published" || event.status === "started" ? "var(--accent-tint-2)" : "var(--surface)",
              border: `1px solid ${event.status === "published" || event.status === "started" ? "var(--accent-tint-border)" : "var(--border)"}`,
              borderRadius: "var(--r-lg)",
              padding: "18px 20px",
              marginBottom: 28,
              font: "var(--w-medium) 14px/1.5 var(--font)",
              color: "var(--text-body)",
            }}
          >
            {event.status === "published"
              ? "This event is published. The assigned volunteer can check people in from their shift view once it starts."
              : event.status === "started"
                ? "Check-in is underway. Once the last guest is in, close the door to prompt the lead for a review."
                : event.status === "cancelled"
                  ? "This event was cancelled."
                  : "This event hasn't been published yet — no report until it's checked in and closed out."}
          </div>
        )}

        <div style={{ marginBottom: 28 }}>
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
          {event.status === "draft" || event.status === "published" || event.status === "started" ? (
            <div style={{ marginTop: 12 }}>
              <AssignVolunteerForm
                eventId={event.id}
                volunteers={volunteers}
                alreadyAssignedIds={assignedVolunteers.map((x) => x.volunteer!.id)}
                onAssigned={refresh}
              />
            </div>
          ) : null}
        </div>

        {event.status === "published" || event.status === "started" ? (
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
              Bookings
            </div>
            <BookingsPanel eventId={event.id} bookings={bookings} contacts={contacts} onChanged={refresh} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function AssignVolunteerForm({
  eventId,
  volunteers,
  alreadyAssignedIds,
  onAssigned,
}: {
  eventId: number;
  volunteers: Volunteer[];
  alreadyAssignedIds: number[];
  onAssigned: () => void;
}) {
  const available = volunteers.filter((v) => !alreadyAssignedIds.includes(v.id));
  const [showForm, setShowForm] = useState(false);
  const [volunteerId, setVolunteerId] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!volunteerId) return;
    setSubmitting(true);
    setError(null);
    try {
      await createAssignment({ event_id: eventId, volunteer_id: Number(volunteerId), coordinator_note: note.trim() || null });
      setVolunteerId("");
      setNote("");
      setShowForm(false);
      onAssigned();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't assign this volunteer.");
    } finally {
      setSubmitting(false);
    }
  }

  if (available.length === 0) {
    return null;
  }

  return (
    <>
      <Button size="sm" variant="secondary" onClick={() => setShowForm(true)}>
        + Assign volunteer
      </Button>
      {showForm ? (
        <Modal title="Assign volunteer" onClose={() => setShowForm(false)} width={440}>
          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Volunteer">
              <select value={volunteerId} onChange={(e) => setVolunteerId(e.target.value)} autoFocus style={fieldStyle}>
                <option value="">Assign a volunteer…</option>
                {available.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Note (optional)">
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note for this assignment…" style={fieldStyle} />
            </Field>
            {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)" }}>{error}</div> : null}
            <ModalActions>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !volunteerId}>
                Assign
              </Button>
            </ModalActions>
          </form>
        </Modal>
      ) : null}
    </>
  );
}

function BookingsPanel({
  eventId,
  bookings,
  contacts,
  onChanged,
}: {
  eventId: number;
  bookings: Booking[];
  contacts: Contact[];
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !phone.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createManualBooking({ event_id: eventId, name: name.trim(), phone: phone.trim() });
      setName("");
      setPhone("");
      setShowForm(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add this booking.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    setImportError(null);
    try {
      const result = await importBookingsCsv(eventId, file);
      setImportResult(`${result.created} added, ${result.skipped_duplicate} already existed, ${result.errors.length} error(s).`);
      onChanged();
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "Couldn't import this file.");
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
        <Button size="sm" variant="secondary" onClick={() => setShowForm(true)}>
          + Add booking
        </Button>
        <label
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            font: "var(--w-semibold) 12.5px/1 var(--font)",
            color: "var(--text-muted)",
            cursor: "pointer",
          }}
        >
          <span
            style={{
              padding: "8px 12px",
              borderRadius: "var(--r-md)",
              border: "1px solid var(--border-strong)",
              background: "var(--surface)",
            }}
          >
            {importing ? "Importing…" : "Import bookings CSV"}
          </span>
          <input type="file" accept=".csv" onChange={onFile} disabled={importing} style={{ display: "none" }} />
        </label>
      </div>
      {showForm ? (
        <Modal title="Add booking" onClose={() => setShowForm(false)} width={420}>
          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Name">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name…" autoFocus style={fieldStyle} />
            </Field>
            <Field label="Phone">
              <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone…" style={fieldStyle} />
            </Field>
            {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)" }}>{error}</div> : null}
            <ModalActions>
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !name.trim() || !phone.trim()}>
                Add booking
              </Button>
            </ModalActions>
          </form>
        </Modal>
      ) : null}
      {importResult ? (
        <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 8 }}>{importResult}</div>
      ) : null}
      {importError ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginTop: 8 }}>{importError}</div> : null}

      <div style={{ marginTop: 16, font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-muted)" }}>
        {bookings.length} booking{bookings.length === 1 ? "" : "s"} so far.
      </div>
      {bookings.length > 0 ? (
        <div style={{ marginTop: 8 }}>
          {bookings.map((b) => {
            const contact = contacts.find((c) => c.id === b.contact_id);
            return (
              <div key={b.id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border-faint)" }}>
                <div>
                  <div style={{ font: "var(--w-semibold) 14.5px/1 var(--font)" }}>{contact?.name ?? `Booking #${b.id}`}</div>
                  <div style={{ font: "var(--w-medium) 12.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 2 }}>
                    {contact?.phone ?? ""} · {b.source}
                  </div>
                </div>
                <Badge tone={b.status === "checked_in" ? "decided" : b.status === "cancelled" || b.status === "no_show" ? "staff" : "open"}>
                  {b.status}
                </Badge>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function AutopsyBox({
  eventId,
  autopsy,
  assignments,
  volunteers,
  onCreated,
}: {
  eventId: number;
  autopsy: EventAutopsy | null;
  assignments: Assignment[];
  volunteers: Volunteer[];
  onCreated: () => void;
}) {
  const acceptedAssignments = assignments.filter((a) => a.status === "accepted");

  const [attendance, setAttendance] = useState("");
  const [venueRating, setVenueRating] = useState("5");
  const [whatWorked, setWhatWorked] = useState("");
  const [whatDidnt, setWhatDidnt] = useState("");
  const [volunteerRatings, setVolunteerRatings] = useState<Record<number, string>>({});
  const [volunteerNotes, setVolunteerNotes] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!attendance.trim() || !whatWorked.trim() || !whatDidnt.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitAutopsy(eventId, {
        attendance_actual: Number(attendance),
        venue_rating: Number(venueRating),
        what_worked: whatWorked.trim(),
        what_didnt: whatDidnt.trim(),
        volunteer_ratings: acceptedAssignments
          .filter((a) => volunteerRatings[a.id])
          .map((a) => ({
            assignment_id: a.id,
            rating: Number(volunteerRatings[a.id]),
            coordinator_note: volunteerNotes[a.id]?.trim() || null,
          })),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save this autopsy.");
    } finally {
      setSubmitting(false);
    }
  }

  if (autopsy) {
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
        <div style={{ font: "var(--w-black) 15px/1 var(--font)", marginBottom: 10 }}>Autopsy</div>
        <div style={{ display: "flex", gap: 20, marginBottom: 14 }}>
          <div>
            <div style={{ font: "var(--w-black) 20px/1 var(--font)" }}>{autopsy.attendance_actual}</div>
            <div style={{ font: "var(--w-semibold) 11px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>attendance</div>
          </div>
          <div>
            <div style={{ font: "var(--w-black) 20px/1 var(--font)" }}>{autopsy.venue_rating}/5</div>
            <div style={{ font: "var(--w-semibold) 11px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>venue rating</div>
          </div>
        </div>
        <div style={{ font: "var(--w-bold) 13px/1.3 var(--font)", marginBottom: 4 }}>What worked</div>
        <p style={{ font: "var(--w-regular) 15px/1.6 var(--font)", color: "var(--text-body)", margin: "0 0 14px" }}>
          {autopsy.what_worked}
        </p>
        <div style={{ font: "var(--w-bold) 13px/1.3 var(--font)", marginBottom: 4 }}>What didn&rsquo;t</div>
        <p style={{ font: "var(--w-regular) 15px/1.6 var(--font)", color: "var(--text-body)", margin: 0 }}>
          {autopsy.what_didnt}
        </p>
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
      <div style={{ font: "var(--w-black) 15px/1 var(--font)", marginBottom: 10 }}>Fill the autopsy</div>
      <form onSubmit={onSubmit}>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <input
            type="number"
            min={0}
            value={attendance}
            onChange={(e) => setAttendance(e.target.value)}
            placeholder="Attendance"
            style={{ width: 120, font: "var(--w-medium) 14px/1 var(--font)", padding: "10px 12px", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", background: "var(--surface)", color: "var(--ink)" }}
          />
          <select
            value={venueRating}
            onChange={(e) => setVenueRating(e.target.value)}
            style={{ font: "var(--w-medium) 14px/1 var(--font)", padding: "10px 12px", borderRadius: "var(--r-md)", border: "1px solid var(--border-strong)" }}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}/5 venue</option>
            ))}
          </select>
        </div>
        <textarea
          value={whatWorked}
          onChange={(e) => setWhatWorked(e.target.value)}
          placeholder="What worked?"
          rows={2}
          style={{ width: "100%", font: "var(--w-medium) 14px/1.4 var(--font)", padding: "10px 12px", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", background: "var(--surface)", color: "var(--ink)", marginBottom: 8, resize: "vertical" }}
        />
        <textarea
          value={whatDidnt}
          onChange={(e) => setWhatDidnt(e.target.value)}
          placeholder="What didn't?"
          rows={2}
          style={{ width: "100%", font: "var(--w-medium) 14px/1.4 var(--font)", padding: "10px 12px", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", background: "var(--surface)", color: "var(--ink)", marginBottom: 14, resize: "vertical" }}
        />

        {acceptedAssignments.length > 0 ? (
          <div style={{ marginBottom: 14 }}>
            <div style={{ font: "var(--w-bold) 13px/1.3 var(--font)", marginBottom: 8 }}>Rate volunteers</div>
            {acceptedAssignments.map((a) => {
              const vol = volunteers.find((v) => v.id === a.volunteer_id);
              return (
                <div key={a.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                  <span style={{ font: "var(--w-semibold) 13.5px/1 var(--font)", width: 140 }}>{vol?.name ?? `Volunteer #${a.volunteer_id}`}</span>
                  <select
                    value={volunteerRatings[a.id] ?? ""}
                    onChange={(e) => setVolunteerRatings((r) => ({ ...r, [a.id]: e.target.value }))}
                    style={{ font: "var(--w-medium) 13px/1 var(--font)", padding: "6px 8px", borderRadius: "var(--r-md)", border: "1px solid var(--border-strong)" }}
                  >
                    <option value="">no rating</option>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>{n}/5</option>
                    ))}
                  </select>
                  <input
                    value={volunteerNotes[a.id] ?? ""}
                    onChange={(e) => setVolunteerNotes((n) => ({ ...n, [a.id]: e.target.value }))}
                    placeholder="Note for next time…"
                    style={{ flex: 1, font: "var(--w-medium) 13px/1 var(--font)", padding: "6px 8px", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", background: "var(--surface)", color: "var(--ink)" }}
                  />
                </div>
              );
            })}
          </div>
        ) : null}

        <Button type="submit" size="sm" disabled={submitting || !attendance.trim() || !whatWorked.trim() || !whatDidnt.trim()}>
          Save autopsy
        </Button>
      </form>
      {error ? <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginTop: 10 }}>{error}</div> : null}
    </div>
  );
}
