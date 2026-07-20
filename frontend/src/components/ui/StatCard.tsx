import type { ReactNode } from "react";

interface StatCardProps {
  value: ReactNode;
  label: string;
  accent?: boolean;
  note?: string;
}

export function StatCard({ value, label, accent = false, note }: StatCardProps) {
  return (
    <div
      style={{
        flex: 1,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "16px 18px",
      }}
    >
      <div
        style={{
          font: "var(--w-black) 30px/1 var(--font)",
          letterSpacing: "-0.02em",
          color: accent ? "var(--accent-ink)" : "var(--ink)",
        }}
      >
        {value}
      </div>
      <div style={{ font: "var(--w-semibold) 12.5px/1.3 var(--font)", color: "var(--text-muted)", marginTop: 4 }}>
        {label}
        {note ? <span style={{ color: "var(--text-ghost)" }}> · {note}</span> : null}
      </div>
    </div>
  );
}
