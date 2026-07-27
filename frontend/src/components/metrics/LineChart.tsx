"use client";

import { useEffect, useRef, useState, type MouseEvent } from "react";
import { ChartLegend } from "./BarChart";

export interface LineSeriesDef {
  key: string;
  label: string;
  color: string;
  values: number[];
}

interface LineChartProps {
  months: string[];
  series: LineSeriesDef[];
  unit?: string;
  formatValue?: (v: number) => string;
  height?: number;
  referenceValue?: number;
  referenceLabel?: string;
  yMin?: number;
}

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(560);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr && cr.width > 0) setW(cr.width);
    });
    ro.observe(el);
    setW(el.clientWidth || 560);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(v)));
  const norm = v / magnitude;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * magnitude;
}

export function LineChart({
  months,
  series,
  unit = "",
  formatValue,
  height = 200,
  referenceValue,
  referenceLabel,
  yMin = 0,
}: LineChartProps) {
  const [containerRef, width] = useWidth();
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const fmt = formatValue ?? ((v: number) => `${Math.round(v * 10) / 10}${unit}`);

  if (series.length === 0 || months.length === 0) {
    return <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--text-faint)", padding: "8px 0" }}>No data for this selection.</div>;
  }

  const padL = 34;
  const padR = 14;
  const padT = 16;
  const padB = 24;
  const innerW = Math.max(10, width - padL - padR);
  const innerH = height - padT - padB;

  const allValues = series.flatMap((s) => s.values);
  const rawMax = Math.max(...allValues, referenceValue ?? 0);
  const yMax = niceMax(rawMax * 1.15) || 1;

  const n = months.length;
  const xAt = (i: number) => padL + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin || 1)) * innerH;

  const ticks = 4;
  const gridValues = Array.from({ length: ticks + 1 }, (_, i) => (yMax / ticks) * i);

  function onMove(e: MouseEvent<SVGRectElement>) {
    const rect = (e.target as SVGRectElement).getBoundingClientRect();
    const x = e.clientX - rect.left;
    const idx = Math.round(((x - padL) / innerW) * (n - 1));
    setHoverIdx(Math.max(0, Math.min(n - 1, idx)));
  }

  // End-labels ride the line only when they won't collide — converging series
  // fall back to the legend + hover tooltip instead of stacking illegible text.
  const endYs = series.map((s) => yAt(s.values[s.values.length - 1])).sort((a, b) => a - b);
  const minGap = endYs.slice(1).reduce((min, y, i) => Math.min(min, y - endYs[i]), Infinity);
  const showEndLabels = series.length <= 4 && (series.length === 1 || minGap >= 14);

  return (
    <div>
      <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", overflow: "visible" }}>
          {gridValues.map((gv, i) => (
            <g key={i}>
              <line x1={padL} x2={width - padR} y1={yAt(gv)} y2={yAt(gv)} stroke="var(--border-divider)" strokeWidth={1} />
              <text x={padL - 8} y={yAt(gv)} textAnchor="end" dominantBaseline="middle" style={{ font: "500 10.5px var(--font)", fill: "var(--text-faint)" }}>
                {Math.round(gv)}
                {unit === "%" ? "%" : ""}
              </text>
            </g>
          ))}

          {referenceValue != null ? (
            <g>
              <line
                x1={padL}
                x2={width - padR}
                y1={yAt(referenceValue)}
                y2={yAt(referenceValue)}
                stroke="var(--text-ghost)"
                strokeWidth={1.5}
                strokeDasharray="3 4"
              />
              {referenceLabel ? (
                <text x={width - padR} y={yAt(referenceValue) - 5} textAnchor="end" style={{ font: "600 10.5px var(--font)", fill: "var(--text-faint)" }}>
                  {referenceLabel}
                </text>
              ) : null}
            </g>
          ) : null}

          {months.map((m, i) => (
            <text key={m + i} x={xAt(i)} y={height - 6} textAnchor="middle" style={{ font: "500 10.5px var(--font)", fill: "var(--text-faint)" }}>
              {m}
            </text>
          ))}

          {hoverIdx != null ? (
            <line x1={xAt(hoverIdx)} x2={xAt(hoverIdx)} y1={padT} y2={padT + innerH} stroke="var(--text-ghost-2)" strokeWidth={1} />
          ) : null}

          {series.map((s) => {
            const d = s.values.map((v, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(v)}`).join(" ");
            const last = s.values[s.values.length - 1];
            return (
              <g key={s.key}>
                <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                <circle cx={xAt(n - 1)} cy={yAt(last)} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
                {showEndLabels ? (
                  <text x={xAt(n - 1) + 8} y={yAt(last)} dominantBaseline="middle" style={{ font: "700 11px var(--font)", fill: "var(--ink)" }}>
                    {fmt(last)}
                  </text>
                ) : null}
                {hoverIdx != null ? (
                  <circle cx={xAt(hoverIdx)} cy={yAt(s.values[hoverIdx])} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
                ) : null}
              </g>
            );
          })}

          <rect x={padL} y={padT} width={innerW} height={innerH} fill="transparent" onMouseMove={onMove} onMouseLeave={() => setHoverIdx(null)} />
        </svg>

        {hoverIdx != null ? (
          <div
            style={{
              position: "absolute",
              left: Math.min(Math.max(xAt(hoverIdx) + 10, 8), width - 168),
              top: 4,
              background: "var(--ink)",
              color: "#fff",
              borderRadius: "var(--r-md)",
              padding: "8px 10px",
              minWidth: 140,
              pointerEvents: "none",
              boxShadow: "0 12px 24px -10px rgba(20,28,44,0.5)",
            }}
          >
            <div style={{ font: "var(--w-bold) 11px/1 var(--font)", opacity: 0.65, marginBottom: 6 }}>{months[hoverIdx]}</div>
            {series.map((s) => (
              <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0" }}>
                <span style={{ width: 10, height: 2, background: s.color, borderRadius: 1, flexShrink: 0 }} />
                <span style={{ font: "var(--w-semibold) 11.5px/1.3 var(--font)", opacity: 0.85, flex: 1 }}>{s.label}</span>
                <span style={{ font: "var(--w-bold) 12px/1 var(--font)" }}>{fmt(s.values[hoverIdx])}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {series.length >= 2 ? <ChartLegend items={series.map((s) => ({ label: s.label, color: s.color }))} /> : null}
    </div>
  );
}
