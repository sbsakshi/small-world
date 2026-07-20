"use client";

import { useEffect, useRef, useState } from "react";
import { listNotifications, markNotificationRead, type Notification } from "@/lib/api";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function NotificationsBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = () => listNotifications().then(setNotifications).catch(() => {});

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const unread = notifications.filter((n) => !n.read_at);

  async function onOpen() {
    setOpen((v) => !v);
  }

  async function onRead(n: Notification) {
    if (n.read_at) return;
    try {
      const updated = await markNotificationRead(n.id);
      setNotifications((ns) => ns.map((x) => (x.id === updated.id ? updated : x)));
    } catch {
      // best-effort
    }
  }

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={onOpen}
        aria-label="Notifications"
        style={{
          position: "relative",
          width: 36,
          height: 36,
          borderRadius: "50%",
          border: "1px solid var(--border-strong)",
          background: "var(--surface)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          font: "16px/1 var(--font)",
        }}
      >
        🔔
        {unread.length > 0 ? (
          <span
            style={{
              position: "absolute",
              top: -2,
              right: -2,
              minWidth: 16,
              height: 16,
              padding: "0 3px",
              borderRadius: "var(--r-pill)",
              background: "var(--priority-high)",
              color: "#fff",
              font: "var(--w-bold) 10px/16px var(--font)",
              textAlign: "center",
            }}
          >
            {unread.length}
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          style={{
            position: "absolute",
            top: 44,
            right: 0,
            width: 340,
            maxHeight: 420,
            overflowY: "auto",
            background: "var(--surface)",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-lg)",
            boxShadow: "var(--shadow-window)",
            zIndex: 20,
          }}
        >
          <div
            style={{
              padding: "12px 16px",
              borderBottom: "1px solid var(--border)",
              font: "var(--w-black) 12px/1 var(--font)",
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            Notifications
          </div>
          {notifications.length === 0 ? (
            <div style={{ padding: "18px 16px", font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)" }}>
              Nothing yet.
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                onClick={() => onRead(n)}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border-faint)",
                  cursor: n.read_at ? "default" : "pointer",
                  background: n.read_at ? "transparent" : "var(--accent-tint-2)",
                }}
              >
                <div style={{ font: "var(--w-bold) 13.5px/1.35 var(--font)" }}>{n.title}</div>
                <div style={{ font: "var(--w-medium) 12.5px/1.4 var(--font)", color: "var(--text-muted)", marginTop: 3 }}>
                  {n.body}
                </div>
                <div style={{ font: "var(--w-medium) 11px/1 var(--font)", color: "var(--text-faint)", marginTop: 5 }}>
                  {fmtDate(n.created_at)}
                </div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
