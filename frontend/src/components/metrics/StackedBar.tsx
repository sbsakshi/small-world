"use client";

import { useState } from "react";
import { ChartLegend } from "./BarChart";

export interface StackSegmentDef {
  key: string;
  label: string;
  color: string;
}

interface StackedBarProps {
  rows: { key: string; values: Record<string, number> }[];
  segments: StackSegmentDef[];
  emptyLabel?: string;
}

function textOnFill(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? "#1b2330" : "#ffffff";
}

export function StackedBar({ rows, segments, emptyLabel = "No data for this selection." }: StackedBarProps) {
  const [hoverRow, setHoverRow] = useState<string | null>(null);
  if (rows.length === 0) {
    return <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)", padding: "8px 0" }}>{emptyLabel}</div>;
  }
  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {rows.map((row) => (
          <div
            key={row.key}
            onMouseEnter={() => setHoverRow(row.key)}
            onMouseLeave={() => setHoverRow(null)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "5px 8px",
              borderRadius: "var(--r-sm)",
              background: hoverRow === row.key ? "var(--surface-sunken)" : "transparent",
            }}
          >
            <div
              title={row.key}
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
              {row.key}
            </div>
            <div style={{ flex: 1, display: "flex", height: 22, borderRadius: "var(--r-chip)", overflow: "hidden", gap: 2 }}>
              {segments.map((seg) => {
                const v = row.values[seg.key] ?? 0;
                if (v <= 0) return null;
                // Comfortable width for a "NN.N%" label at 11px bold is ~18% of a
                // typical card's stacked track — below that it clips (see
                // dataviz skill: never crop a label, drop to tooltip instead).
                const showLabel = v >= 18;
                return (
                  <div
                    key={seg.key}
                    title={`${seg.label}: ${v}%`}
                    style={{
                      width: `${v}%`,
                      background: seg.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      overflow: "hidden",
                      minWidth: v > 0 ? 3 : 0,
                    }}
                  >
                    {showLabel ? (
                      <span style={{ font: "var(--w-bold) 11px/1 var(--font)", color: textOnFill(seg.color), whiteSpace: "nowrap" }}>{v}%</span>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <ChartLegend items={segments.map((s) => ({ label: s.label, color: s.color }))} />
    </div>
  );
}
