"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useRequireAuth";
import {
  logout,
  myAssignments,
  myWeeklyAvailability,
  setMyWeeklyAvailability,
  respondToAssignment,
  ApiError,
  type Assignment,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { NotificationsBell } from "@/components/NotificationsBell";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function VolunteerPage() {
  const router = useRouter();
  const { user, ready } = useRequireAuth("volunteer");
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    if (!ready) return;
    Promise.all([myAssignments(), myWeeklyAvailability()])
      .then(([a, w]) => {
        setAssignments(a);
        setDays(w.days);
      })
      .catch(() => setError("Couldn't load your shifts. Try refreshing."));
  }, [ready]);

  if (!ready || !user) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }

  const initials = user.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const firstName = user.name.split(" ")[0];

  async function onSignOut() {
    await logout();
    router.push("/login");
  }

  async function respond(assignment: Assignment, accept: boolean) {
    setBusyId(assignment.id);
    try {
      const updated = await respondToAssignment(assignment.id, accept);
      setAssignments((as) => as.map((a) => (a.id === updated.id ? updated : a)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't record your response.");
    } finally {
      setBusyId(null);
    }
  }

  function toggleDay(day: number) {
    const next = days.includes(day) ? days.filter((d) => d !== day) : [...days, day];
    setDays(next);
    setMyWeeklyAvailability(next).catch(() => setError("Couldn't save your availability."));
  }

  const pending = assignments.filter((a) => a.status === "pending");
  const decided = assignments.filter((a) => a.status !== "pending");

  return (
    <div style={{ minHeight: "100vh", background: "var(--canvas)", display: "flex", justifyContent: "center", padding: "24px 0" }}>
      <div
        style={{
          width: 380,
          minHeight: 780,
          background: "var(--surface-sunken)",
          borderRadius: "var(--r-phone)",
          boxShadow: "var(--shadow-phone)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "8px 24px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 13, height: 13, borderRadius: "50%", background: "var(--accent)" }} />
            <span style={{ font: "var(--w-black) 13px/1 var(--font)" }}>Small World</span>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
              <NotificationsBell />
              <button
                onClick={onSignOut}
                style={{
                  font: "var(--w-semibold) 11px/1 var(--font)",
                  color: "var(--text-faint)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Sign out
              </button>
              <Avatar initials={initials} size={30} />
            </div>
          </div>
          <div style={{ font: "var(--w-medium) 15px/1 var(--font)", color: "var(--text-muted)", marginTop: 20 }}>
            Hi {firstName} —
          </div>
          <div style={{ font: "var(--w-black) 27px/1.15 var(--font)", letterSpacing: "-0.025em", marginTop: 2 }}>
            here&apos;s what&apos;s on your plate.
          </div>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px" }}>
          {error ? (
            <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--warn-ink)", marginBottom: 14 }}>{error}</div>
          ) : null}

          <div style={{ font: "var(--w-black) 13px/1 var(--font)", letterSpacing: "0.02em", color: "var(--text-muted)", margin: "4px 4px 10px" }}>
            Needs your response
          </div>
          {pending.length === 0 ? (
            <EmptyCard>Nothing waiting on you right now.</EmptyCard>
          ) : (
            pending.map((a) => (
              <div
                key={a.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--r-lg)",
                  padding: "16px 18px",
                  marginBottom: 10,
                }}
              >
                <div style={{ font: "var(--w-bold) 16px/1.3 var(--font)" }}>Event #{a.event_id}</div>
                {a.coordinator_note ? (
                  <div style={{ font: "var(--w-medium) 13px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 4 }}>
                    {a.coordinator_note}
                  </div>
                ) : null}
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <Button size="sm" variant="primary" disabled={busyId === a.id} onClick={() => respond(a, true)}>
                    Accept
                  </Button>
                  <Button size="sm" variant="secondary" disabled={busyId === a.id} onClick={() => respond(a, false)}>
                    Decline
                  </Button>
                </div>
              </div>
            ))
          )}

          <div style={{ font: "var(--w-black) 13px/1 var(--font)", letterSpacing: "0.02em", color: "var(--text-muted)", margin: "20px 4px 10px" }}>
            Your shifts
          </div>
          {decided.length === 0 ? (
            <EmptyCard>No shifts yet.</EmptyCard>
          ) : (
            decided.map((a) => (
              <div
                key={a.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 16px",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--r-lg)",
                  marginBottom: 8,
                }}
              >
                <span style={{ font: "var(--w-semibold) 14.5px/1.3 var(--font)" }}>Event #{a.event_id}</span>
                <Badge tone={a.status === "accepted" ? "decided" : "staff"}>{a.status}</Badge>
              </div>
            ))
          )}

          <div style={{ font: "var(--w-black) 13px/1 var(--font)", letterSpacing: "0.02em", color: "var(--text-muted)", margin: "20px 4px 10px" }}>
            Weekly availability
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {DAY_LABELS.map((label, day) => {
              const on = days.includes(day);
              return (
                <button
                  key={day}
                  onClick={() => toggleDay(day)}
                  style={{
                    font: "var(--w-bold) 12.5px/1 var(--font)",
                    padding: "10px 12px",
                    borderRadius: "var(--r-md)",
                    border: `1px solid ${on ? "var(--accent)" : "var(--border-strong)"}`,
                    background: on ? "var(--accent-tint)" : "var(--surface)",
                    color: on ? "var(--accent-ink)" : "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        font: "var(--w-medium) 13px/1.5 var(--font)",
        color: "var(--text-faint)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "16px 18px",
        marginBottom: 10,
      }}
    >
      {children}
    </div>
  );
}
