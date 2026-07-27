"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { logout, type CurrentUser } from "@/lib/api";
import { Avatar } from "@/components/ui/Avatar";
import { NotificationsBell } from "@/components/NotificationsBell";

const ROLE_LABEL: Record<string, string> = {
  founder: "Founder",
  city_lead: "City lead",
  event_lead: "Event lead",
};

export function StaffHeader({ user }: { user: CurrentUser }) {
  const router = useRouter();

  async function onSignOut() {
    await logout();
    router.push("/login");
  }

  const initials = user.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 32px",
        background: "var(--surface)",
        borderBottom: "1px solid var(--border-strong)",
      }}
    >
      <Link href="/cities" style={{ display: "flex", alignItems: "center", gap: 9, textDecoration: "none" }}>
        <span style={{ width: 15, height: 15, borderRadius: "50%", background: "var(--accent)" }} />
        <span style={{ font: "var(--w-black) 15px/1 var(--font)", letterSpacing: "0.01em", color: "var(--ink)" }}>
          Small World
        </span>
      </Link>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <Link
          href="/today"
          style={{
            font: "var(--w-bold) 12.5px/1 var(--font)",
            color: "var(--text-body)",
            textDecoration: "none",
            padding: "8px 12px",
            borderRadius: "var(--r-md)",
            background: "var(--surface-sunken)",
          }}
        >
          Today
        </Link>
        {user.role === "founder" ? (
          <Link
            href="/metrics"
            style={{
              font: "var(--w-bold) 12.5px/1 var(--font)",
              color: "var(--text-body)",
              textDecoration: "none",
              padding: "8px 12px",
              borderRadius: "var(--r-md)",
              background: "var(--surface-sunken)",
            }}
          >
            Metrics
          </Link>
        ) : null}
        <NotificationsBell />
        <div style={{ textAlign: "right" }}>
          <div style={{ font: "var(--w-bold) 13px/1.3 var(--font)", color: "var(--ink)" }}>{user.name}</div>
          <div style={{ font: "var(--w-medium) 11.5px/1.3 var(--font)", color: "var(--text-faint)" }}>
            {ROLE_LABEL[user.role ?? ""] ?? "Staff"}
          </div>
        </div>
        <Avatar initials={initials} size={36} />
        <button
          onClick={onSignOut}
          style={{
            font: "var(--w-semibold) 12.5px/1 var(--font)",
            color: "var(--text-muted)",
            background: "transparent",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-md)",
            padding: "8px 12px",
            cursor: "pointer",
          }}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
