import type { ReactNode } from "react";

interface MetricCardProps {
  title: string;
  subtitle?: string;
  tag?: string;
  children: ReactNode;
  wide?: boolean;
}

export function MetricCard({ title, subtitle, tag, children, wide }: MetricCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "20px 22px 22px",
        gridColumn: wide ? "1 / -1" : undefined,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10, marginBottom: 16 }}>
        <div>
          <div style={{ font: "var(--w-bold) 15px/1.3 var(--font)", letterSpacing: "-0.01em", color: "var(--ink)" }}>{title}</div>
          {subtitle ? (
            <div style={{ font: "var(--w-medium) 12.5px/1.4 var(--font)", color: "var(--text-faint)", marginTop: 3 }}>{subtitle}</div>
          ) : null}
        </div>
        {tag ? (
          <span
            style={{
              font: "var(--w-bold) 11px/1 var(--font)",
              color: "var(--accent-ink)",
              background: "var(--accent-tint)",
              padding: "5px 10px",
              borderRadius: "var(--r-pill)",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            {tag}
          </span>
        ) : null}
      </div>
      {children}
    </div>
  );
}
