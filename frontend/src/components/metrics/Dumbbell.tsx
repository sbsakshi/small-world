"use client";

import { DUMBBELL_AFTER, DUMBBELL_BEFORE } from "./colors";
import { ChartLegend } from "./BarChart";

export interface DumbbellRow {
  key: string;
  before: number;
  after: number;
}

interface DumbbellProps {
  rows: DumbbellRow[];
  unit?: string;
  formatValue?: (v: number) => string;
  lowerIsBetter?: boolean;
  emptyLabel?: string;
}

export function Dumbbell({ rows, unit = "", formatValue, lowerIsBetter = true, emptyLabel = "No data for this selection." }: DumbbellProps) {
  if (rows.length === 0) {
    return <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)", padding: "8px 0" }}>{emptyLabel}</div>;
  }
  const fmt = formatValue ?? ((v: number) => `${unit === "₹" ? "₹" : ""}${Math.round(v).toLocaleString("en-IN")}${unit !== "₹" ? unit : ""}`);
  const max = Math.max(...rows.flatMap((r) => [r.before, r.after])) * 1.08;

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {rows.map((r) => {
          const beforePct = (r.before / max) * 100;
          const afterPct = (r.after / max) * 100;
          const left = Math.min(beforePct, afterPct);
          const width = Math.abs(afterPct - beforePct);
          const delta = r.before === 0 ? 0 : ((r.after - r.before) / r.before) * 100;
          const isGood = lowerIsBetter ? delta < 0 : delta > 0;
          return (
            <div key={r.key} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                title={r.key}
                style={{
                  width: 130,
                  flexShrink: 0,
                  font: "var(--w-semibold) 12.5px/1.3 var(--font)",
                  color: "var(--text-body)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {r.key}
              </div>
              <div style={{ flex: 1, position: "relative", height: 20 }}>
                <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 1, background: "var(--border-divider)" }} />
                <div
                  style={{
                    position: "absolute",
                    left: `${left}%`,
                    width: `${width}%`,
                    top: "50%",
                    height: 2,
                    background: "var(--text-ghost)",
                    transform: "translateY(-50%)",
                  }}
                />
                <Dot pct={beforePct} color={DUMBBELL_BEFORE} />
                <Dot pct={afterPct} color={DUMBBELL_AFTER} />
              </div>
              <div style={{ width: 150, textAlign: "right", display: "flex", alignItems: "baseline", justifyContent: "flex-end", gap: 6 }}>
                <span style={{ font: "var(--w-medium) 12px/1 var(--font)", color: "var(--text-faint)", textDecoration: "line-through" }}>{fmt(r.before)}</span>
                <span style={{ font: "var(--w-bold) 13px/1 var(--font)", color: "var(--ink)" }}>{fmt(r.after)}</span>
                <span style={{ font: "var(--w-bold) 11.5px/1 var(--font)", color: isGood ? "var(--good-ink)" : "var(--warn-ink)" }}>
                  {delta > 0 ? "+" : ""}
                  {Math.round(delta)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <ChartLegend items={[{ label: "Before OS", color: DUMBBELL_BEFORE }, { label: "After OS", color: DUMBBELL_AFTER }]} />
    </div>
  );
}

function Dot({ pct, color }: { pct: number; color: string }) {
  return (
    <div
      style={{
        position: "absolute",
        left: `${pct}%`,
        top: "50%",
        width: 12,
        height: 12,
        borderRadius: "50%",
        background: color,
        border: "2px solid var(--surface)",
        boxShadow: "0 0 0 1px var(--border-strong)",
        transform: "translate(-50%, -50%)",
      }}
    />
  );
}
