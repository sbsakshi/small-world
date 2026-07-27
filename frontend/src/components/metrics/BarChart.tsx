"use client";

import { useState } from "react";
import { SEQUENTIAL_BLUE } from "./colors";

export interface BarDatum {
  key: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: BarDatum[];
  unit?: string;
  formatValue?: (v: number) => string;
  legend?: { label: string; color: string }[];
  sort?: boolean;
  emptyLabel?: string;
}

export function BarChart({ data, unit = "", formatValue, legend, sort = true, emptyLabel = "No data for this selection." }: BarChartProps) {
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  if (data.length === 0) {
    return <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)", padding: "8px 0" }}>{emptyLabel}</div>;
  }
  const rows = sort ? [...data].sort((a, b) => b.value - a.value) : data;
  const max = Math.max(1, ...rows.map((d) => d.value)) * 1.12;
  const fmt = formatValue ?? ((v: number) => `${Math.round(v * 10) / 10}${unit}`);

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {rows.map((d) => {
          const pct = Math.max(1, Math.min(100, (d.value / max) * 100));
          const hovered = hoverKey === d.key;
          return (
            <div
              key={d.key}
              onMouseEnter={() => setHoverKey(d.key)}
              onMouseLeave={() => setHoverKey(null)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "5px 8px",
                borderRadius: "var(--r-sm)",
                background: hovered ? "var(--surface-sunken)" : "transparent",
                transition: "background var(--dur-fast) var(--ease)",
              }}
            >
              <div
                title={d.key}
                style={{
                  width: 138,
                  flexShrink: 0,
                  font: "var(--w-semibold) 12.5px/1.3 var(--font)",
                  color: "var(--text-body)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {d.key}
              </div>
              <div style={{ flex: 1, position: "relative", height: 18, background: "var(--border-faint)", borderRadius: "var(--r-chip)" }}>
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${pct}%`,
                    background: d.color ?? SEQUENTIAL_BLUE,
                    borderRadius: "0 var(--r-chip) var(--r-chip) 0",
                    transition: "width var(--dur) var(--ease)",
                  }}
                />
              </div>
              <div style={{ width: 58, textAlign: "right", font: "var(--w-bold) 13px/1 var(--font)", color: "var(--ink)" }}>
                {fmt(d.value)}
              </div>
            </div>
          );
        })}
      </div>
      {legend ? <ChartLegend items={legend} /> : null}
    </div>
  );
}

export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border-faint)" }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 9, height: 9, borderRadius: "50%", background: it.color, flexShrink: 0 }} />
          <span style={{ font: "var(--w-semibold) 12px/1 var(--font)", color: "var(--text-muted)" }}>{it.label}</span>
        </div>
      ))}
    </div>
  );
}
