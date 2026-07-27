"use client";

import type { ReactNode } from "react";
import { TIME_RANGES, type TimeRangeKey } from "@/lib/mockMetrics";

interface CityOption {
  id: number;
  name: string;
}

interface FilterBarProps {
  cities: CityOption[];
  selectedCityIds: Set<number>;
  onToggleCity: (id: number) => void;
  onSelectAllCities: () => void;
  compareBy: "city" | "event";
  onCompareByChange: (v: "city" | "event") => void;
  timeRange: TimeRangeKey;
  onTimeRangeChange: (v: TimeRangeKey) => void;
}

export function FilterBar({
  cities,
  selectedCityIds,
  onToggleCity,
  onSelectAllCities,
  compareBy,
  onCompareByChange,
  timeRange,
  onTimeRangeChange,
}: FilterBarProps) {
  const allSelected = cities.length > 0 && cities.every((c) => selectedCityIds.has(c.id));

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "14px 22px",
        padding: "16px 20px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
      }}
    >
      <FilterGroup label="Cities">
        <Chip label="All" active={allSelected} onClick={onSelectAllCities} />
        {cities.map((c) => (
          <Chip key={c.id} label={c.name} active={selectedCityIds.has(c.id)} onClick={() => onToggleCity(c.id)} />
        ))}
      </FilterGroup>

      <Divider />

      <FilterGroup label="Compare by">
        <Segmented
          options={[
            { key: "city", label: "City" },
            { key: "event", label: "Event" },
          ]}
          value={compareBy}
          onChange={(v) => onCompareByChange(v as "city" | "event")}
        />
      </FilterGroup>

      <Divider />

      <FilterGroup label="Window">
        <Segmented options={TIME_RANGES.map((r) => ({ key: r.key, label: r.label }))} value={timeRange} onChange={(v) => onTimeRangeChange(v as TimeRangeKey)} />
      </FilterGroup>
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
      <span style={{ font: "var(--w-bold) 11px/1 var(--font)", letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--text-faint)" }}>
        {label}
      </span>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{children}</div>
    </div>
  );
}

function Divider() {
  return <div style={{ width: 1, alignSelf: "stretch", background: "var(--border-strong)" }} />;
}

function Chip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        font: "var(--w-semibold) 12.5px/1 var(--font)",
        padding: "7px 13px",
        borderRadius: "var(--r-pill)",
        border: `1px solid ${active ? "transparent" : "var(--border-strong)"}`,
        background: active ? "var(--accent)" : "var(--surface)",
        color: active ? "#fff" : "var(--text-body)",
        cursor: "pointer",
        transition: "background var(--dur-fast) var(--ease)",
      }}
    >
      {label}
    </button>
  );
}

function Segmented({
  options,
  value,
  onChange,
}: {
  options: { key: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", background: "var(--surface-sunken)", borderRadius: "var(--r-md)", padding: 3, gap: 2 }}>
      {options.map((o) => {
        const active = o.key === value;
        return (
          <button
            key={o.key}
            onClick={() => onChange(o.key)}
            style={{
              font: `var(--w-bold) 12px/1 var(--font)`,
              padding: "6px 11px",
              borderRadius: "var(--r-sm)",
              border: "none",
              background: active ? "var(--surface)" : "transparent",
              color: active ? "var(--accent-ink)" : "var(--text-muted)",
              boxShadow: active ? "0 1px 3px rgba(20,28,44,0.12)" : "none",
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
