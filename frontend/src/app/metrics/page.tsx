"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { listCities, listEvents, listVolunteers, type City, type Event, type Volunteer } from "@/lib/api";
import {
  SECTIONS,
  TIME_RANGES,
  monthLabels,
  entityTrend,
  entityValue,
  entityComposition,
  entityDumbbell,
  mockEventsForCity,
  type EntityLite,
  type SectionKey,
  type TimeRangeKey,
} from "@/lib/mockMetrics";
import { StaffHeader } from "@/components/StaffHeader";
import { FilterBar } from "@/components/metrics/FilterBar";
import { MetricCard } from "@/components/metrics/MetricCard";
import { BarChart } from "@/components/metrics/BarChart";
import { StackedBar } from "@/components/metrics/StackedBar";
import { LineChart } from "@/components/metrics/LineChart";
import { Dumbbell } from "@/components/metrics/Dumbbell";
import { MiniSparkline } from "@/components/metrics/MiniSparkline";
import { CATEGORICAL, seriesColor } from "@/components/metrics/colors";

export default function MetricsPlaygroundPage() {
  const { user, ready } = useRequireAuth("staff");

  const [cities, setCities] = useState<City[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [loadError, setLoadError] = useState(false);

  const [selectedCityIds, setSelectedCityIds] = useState<Set<number>>(new Set());
  const [compareBy, setCompareBy] = useState<"city" | "event">("city");
  const [timeRange, setTimeRange] = useState<TimeRangeKey>("12mo");
  const [section, setSection] = useState<SectionKey>("outcomes");

  useEffect(() => {
    if (!ready) return;
    Promise.all([listCities(), listEvents(), listVolunteers()])
      .then(([c, e, v]) => {
        setCities(c);
        setEvents(e);
        setVolunteers(v);
        setSelectedCityIds(new Set(c.slice(0, 4).map((city) => city.id)));
      })
      .catch(() => setLoadError(true));
  }, [ready]);

  const months = useMemo(() => monthLabels(TIME_RANGES.find((r) => r.key === timeRange)!.months), [timeRange]);

  const activeCities = useMemo(() => cities.filter((c) => selectedCityIds.has(c.id)), [cities, selectedCityIds]);

  const cityEntities: EntityLite[] = useMemo(() => activeCities.map((c) => ({ id: c.id, name: c.name })), [activeCities]);

  const eventEntities: EntityLite[] = useMemo(() => {
    const out: EntityLite[] = [];
    for (const c of activeCities) {
      const real = events.filter((e) => e.city_id === c.id).slice(0, 3);
      if (real.length > 0) {
        out.push(...real.map((e) => ({ id: e.id, name: e.title, cityId: c.id })));
      } else {
        out.push(...mockEventsForCity(c.id, c.name, 3));
      }
    }
    return out;
  }, [activeCities, events]);

  const entities = compareBy === "city" ? cityEntities : eventEntities;
  const cityColorIndex = useMemo(() => {
    const m = new Map<number, number>();
    activeCities.forEach((c, i) => m.set(c.id, i));
    return m;
  }, [activeCities]);

  if (!ready || !user) {
    return <div style={{ minHeight: "100vh", background: "var(--canvas)" }} />;
  }

  if (user.role !== "founder") {
    return (
      <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
        <StaffHeader user={user} />
        <div style={{ padding: "60px 40px", textAlign: "center" }}>
          <div style={{ font: "var(--w-bold) 16px/1.4 var(--font)", color: "var(--text-muted)" }}>
            The metrics playground is available to founders only.
          </div>
          <Link href="/cities" style={{ font: "var(--w-bold) 13px/1 var(--font)", color: "var(--accent-link)" }}>
            ‹ Back to cities
          </Link>
        </div>
      </div>
    );
  }

  const headline = {
    ownedDb: cityEntities.map((e) => entityTrend("owned_db", e, 12, { band: [22, 38], driftBand: [8, 22], noise: 2.5, min: 0, max: 100 })),
    conversion: cityEntities.map((e) => entityValue("vol_conversion", e, [8, 28])),
    autopsy: cityEntities.map((e) => entityValue("autopsy_completion", e, [45, 95])),
    costDelta: cityEntities.map((e) => entityDumbbell("cost_delta", e, [1400, 2600], [0.14, 0.34])),
  };
  const avg = (arr: number[]) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);
  const ownedDbSeries12 = months.length >= 2 ? averageSeries(headline.ownedDb.map((s) => s.slice(-months.length))) : [];
  const ownedDbLatest = ownedDbSeries12.length ? ownedDbSeries12[ownedDbSeries12.length - 1] : 0;
  const conversionAvg = avg(headline.conversion);
  const autopsyAvg = avg(headline.autopsy);
  const costBeforeAvg = avg(headline.costDelta.map((d) => d.before));
  const costAfterAvg = avg(headline.costDelta.map((d) => d.after));
  const costSavedPct = costBeforeAvg > 0 ? ((costBeforeAvg - costAfterAvg) / costBeforeAvg) * 100 : 0;

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-sunken)" }}>
      <StaffHeader user={user} />
      <div style={{ padding: "32px 40px 56px" }}>
        <div style={{ marginBottom: 22 }}>
          <div style={{ font: "var(--w-bold) 11px/1 var(--font)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-faint)" }}>
            Founder view · mocked data
          </div>
          <h1 style={{ font: "var(--w-black) 30px/1.15 var(--font)", letterSpacing: "-0.02em", margin: "6px 0 4px" }}>Metrics playground</h1>
          <p style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-muted)", margin: 0, maxWidth: 640 }}>
            Slice every KPI that proves the OS is working — by city, by event, over time. Numbers here are simulated for the walkthrough.
          </p>
        </div>

        {loadError ? (
          <div style={{ font: "var(--w-medium) 13px/1.5 var(--font)", color: "var(--warn-ink)", marginBottom: 16 }}>
            Couldn&apos;t load cities/events from the API — showing the playground with sample names only.
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12, marginBottom: 20 }}>
          <HeadlineTile
            label="Owned-database share"
            value={`${Math.round(ownedDbLatest)}%`}
            note="of attendees, avg across selected cities"
            sparkline={ownedDbSeries12}
          />
          <HeadlineTile label="Superfan → volunteer conversion" value={`${conversionAvg.toFixed(1)}%`} note="of superfan cohort" />
          <HeadlineTile label="Autopsy completion (48h)" value={`${Math.round(autopsyAvg)}%`} note="of completed events" />
          <HeadlineTile
            label="Cost per event, after OS"
            value={`₹${Math.round(costAfterAvg).toLocaleString("en-IN")}`}
            note={`${costSavedPct >= 0 ? "down" : "up"} ${Math.abs(Math.round(costSavedPct))}% vs before`}
            tone={costSavedPct >= 0 ? "good" : "warn"}
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <FilterBar
            cities={cities}
            selectedCityIds={selectedCityIds}
            onToggleCity={(id) =>
              setSelectedCityIds((prev) => {
                const next = new Set(prev);
                if (next.has(id)) next.delete(id);
                else next.add(id);
                return next;
              })
            }
            onSelectAllCities={() => setSelectedCityIds(new Set(cities.map((c) => c.id)))}
            compareBy={compareBy}
            onCompareByChange={setCompareBy}
            timeRange={timeRange}
            onTimeRangeChange={setTimeRange}
          />
        </div>

        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => setSection(s.key)}
              style={{
                font: "var(--w-bold) 13px/1 var(--font)",
                padding: "10px 16px",
                borderRadius: "var(--r-md)",
                border: "1px solid var(--border-strong)",
                background: section === s.key ? "var(--ink)" : "var(--surface)",
                color: section === s.key ? "#fff" : "var(--text-body)",
                cursor: "pointer",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {activeCities.length === 0 ? (
          <div style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-faint)", padding: "24px 0" }}>
            Select at least one city above to see its metrics.
          </div>
        ) : (
          <SectionGrid
            section={section}
            entities={entities}
            compareBy={compareBy}
            months={months}
            cityColorIndex={cityColorIndex}
            activeCities={activeCities}
            volunteers={volunteers.filter((v) => selectedCityIds.has(v.city_id))}
          />
        )}
      </div>
    </div>
  );
}

function averageSeries(series: number[][]): number[] {
  if (series.length === 0) return [];
  const len = series[0].length;
  const out: number[] = [];
  for (let i = 0; i < len; i++) {
    out.push(series.reduce((a, s) => a + (s[i] ?? 0), 0) / series.length);
  }
  return out;
}

function HeadlineTile({
  label,
  value,
  note,
  sparkline,
  tone = "accent",
}: {
  label: string;
  value: string;
  note?: string;
  sparkline?: number[];
  tone?: "accent" | "good" | "warn";
}) {
  const ink = tone === "good" ? "var(--good-ink)" : tone === "warn" ? "var(--warn-ink)" : "var(--accent-ink)";
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: "16px 18px" }}>
      <div style={{ font: "var(--w-semibold) 12px/1.3 var(--font)", color: "var(--text-muted)", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ font: "var(--w-black) 26px/1 var(--font)", letterSpacing: "-0.02em", color: ink }}>{value}</div>
          {note ? <div style={{ font: "var(--w-medium) 11.5px/1.3 var(--font)", color: "var(--text-faint)", marginTop: 4 }}>{note}</div> : null}
        </div>
        {sparkline && sparkline.length >= 2 ? <MiniSparkline values={sparkline} color="var(--accent)" /> : null}
      </div>
    </div>
  );
}

function SectionGrid({
  section,
  entities,
  compareBy,
  months,
  cityColorIndex,
  activeCities,
  volunteers,
}: {
  section: SectionKey;
  entities: EntityLite[];
  compareBy: "city" | "event";
  months: string[];
  cityColorIndex: Map<number, number>;
  activeCities: City[];
  volunteers: Volunteer[];
}) {
  const barLegend =
    compareBy === "event"
      ? activeCities.map((c, i) => ({ label: c.name, color: seriesColor(i) }))
      : undefined;

  function barColorFor(e: EntityLite) {
    if (compareBy !== "event") return undefined;
    const idx = e.cityId != null ? cityColorIndex.get(e.cityId) : undefined;
    return idx != null ? seriesColor(idx) : undefined;
  }

  if (section === "outcomes") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
        <MetricCard title="Owned-database share" subtitle="% of attendees identifiable in our own contact database, not platform-only" tag="climbing = working">
          <LineChart
            months={months}
            unit="%"
            referenceValue={60}
            referenceLabel="Target 60%"
            series={activeCities.map((c, i) => ({
              key: String(c.id),
              label: c.name,
              color: seriesColor(i),
              values: entityTrend("owned_db", { id: c.id, name: c.name }, months.length, { band: [22, 38], driftBand: [8, 22], noise: 2.5, min: 0, max: 100 }),
            }))}
          />
        </MetricCard>

        <MetricCard title="Repeat attendance cohort mix" subtitle="First-timer → repeat → superfan, by city" tag={compareBy === "event" ? "by event" : "by city"}>
          <StackedBar
            segments={[
              { key: "first", label: "First-timers", color: CATEGORICAL[0] },
              { key: "repeat", label: "Repeat", color: CATEGORICAL[1] },
              { key: "superfan", label: "Superfans", color: CATEGORICAL[2] },
            ]}
            rows={entities.map((e) => ({
              key: e.name,
              values: entityComposition("repeat_cohort", e, [
                { key: "first", label: "First-timers", color: CATEGORICAL[0], weight: 55 },
                { key: "repeat", label: "Repeat", color: CATEGORICAL[1], weight: 32 },
                { key: "superfan", label: "Superfans", color: CATEGORICAL[2], weight: 13 },
              ]),
            }))}
          />
        </MetricCard>

        <MetricCard title="Volunteer conversion from superfans" subtitle="Share of the superfan cohort who signed up to volunteer">
          <BarChart unit="%" legend={barLegend} data={entities.map((e) => ({ key: e.name, value: entityValue("vol_conversion", e, [8, 28]), color: barColorFor(e) }))} />
        </MetricCard>

        <MetricCard title="Cost per event delivered" subtitle="Before vs after the OS — coordinator time saved, not just infra cost" tag="by city">
          <Dumbbell
            unit="₹"
            rows={activeCities.map((c) => entityDumbbell("cost_delta", { id: c.id, name: c.name }, [1400, 2600], [0.14, 0.34]))}
          />
        </MetricCard>
      </div>
    );
  }

  if (section === "funnel") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
        <MetricCard title="Booking drop-off & nudge recovery" subtitle="Share of started bookings that complete, recover after the 30-min nudge, or stay dropped">
          <StackedBar
            segments={[
              { key: "completed", label: "Completed booking", color: CATEGORICAL[0] },
              { key: "recovered", label: "Recovered after nudge", color: CATEGORICAL[2] },
              { key: "lost", label: "Dropped, not recovered", color: CATEGORICAL[7] },
            ]}
            rows={entities.map((e) => ({
              key: e.name,
              values: entityComposition("dropoff", e, [
                { key: "completed", label: "Completed booking", color: CATEGORICAL[0], weight: 72 },
                { key: "recovered", label: "Recovered after nudge", color: CATEGORICAL[2], weight: 18 },
                { key: "lost", label: "Dropped, not recovered", color: CATEGORICAL[7], weight: 10 },
              ]),
            }))}
          />
        </MetricCard>

        <MetricCard title="No-show rate" subtitle="Confirmed bookings that never checked in">
          <BarChart unit="%" legend={barLegend} data={entities.map((e) => ({ key: e.name, value: entityValue("no_show", e, [6, 22]), color: barColorFor(e) }))} />
        </MetricCard>

        <MetricCard title="Time to first post-event touch" subtitle="Hours from event completion to first follow-up — goal is same-day" tag="by city" wide>
          <LineChart
            months={months}
            unit="h"
            referenceValue={24}
            referenceLabel="Same-day (24h)"
            series={activeCities.map((c, i) => ({
              key: String(c.id),
              label: c.name,
              color: seriesColor(i),
              values: entityTrend("first_touch", { id: c.id, name: c.name }, months.length, { band: [30, 70], driftBand: [-40, -10], noise: 4, min: 2 }),
            }))}
          />
        </MetricCard>
      </div>
    );
  }

  if (section === "volunteer") {
    const rosterBins = [
      { key: "b1", label: "0–39", min: 0, max: 39 },
      { key: "b2", label: "40–59", min: 40, max: 59 },
      { key: "b3", label: "60–74", min: 60, max: 74 },
      { key: "b4", label: "75–89", min: 75, max: 89 },
      { key: "b5", label: "90–100", min: 90, max: 100 },
    ];
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
        <MetricCard title="Assignment acceptance rate" subtitle="First-offer acceptance vs. accepted only after reassignment">
          <StackedBar
            segments={[
              { key: "first", label: "Accepted, first offer", color: CATEGORICAL[0] },
              { key: "reassigned", label: "Accepted after reassignment", color: CATEGORICAL[3] },
            ]}
            rows={entities.map((e) => ({
              key: e.name,
              values: entityComposition("assignment_offer", e, [
                { key: "first", label: "Accepted, first offer", color: CATEGORICAL[0], weight: 68 },
                { key: "reassigned", label: "Accepted after reassignment", color: CATEGORICAL[3], weight: 32 },
              ]),
            }))}
          />
        </MetricCard>

        <MetricCard title="24h expiry vs. explicit response" subtitle="Are volunteers engaged, or ghosting the assignment offer?">
          <StackedBar
            segments={[
              { key: "responded", label: "Explicit response", color: CATEGORICAL[2] },
              { key: "expired", label: "Hit 24h expiry", color: CATEGORICAL[7] },
            ]}
            rows={entities.map((e) => ({
              key: e.name,
              values: entityComposition("expiry_response", e, [
                { key: "responded", label: "Explicit response", color: CATEGORICAL[2], weight: 77 },
                { key: "expired", label: "Hit 24h expiry", color: CATEGORICAL[7], weight: 23 },
              ]),
            }))}
          />
        </MetricCard>

        <MetricCard title="Reliability score distribution" subtitle="Live cached_score of the active roster, bucketed — is reliability concentrated in a few volunteers?" tag="real roster data">
          <BarChart
            unit=" volunteers"
            formatValue={(v) => `${Math.round(v)}`}
            sort={false}
            data={rosterBins.map((b) => ({
              key: b.label,
              value: volunteers.filter((v) => v.cached_score >= b.min && v.cached_score <= b.max).length,
            }))}
          />
        </MetricCard>

        <MetricCard title="Time-to-fill" subtitle="Hours between a lead needing a volunteer and getting one accepted" tag="by city">
          <LineChart
            months={months}
            unit="h"
            series={activeCities.map((c, i) => ({
              key: String(c.id),
              label: c.name,
              color: seriesColor(i),
              values: entityTrend("time_to_fill", { id: c.id, name: c.name }, months.length, { band: [10, 40], driftBand: [-15, 5], noise: 3, min: 1 }),
            }))}
          />
        </MetricCard>
      </div>
    );
  }

  if (section === "memory") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
        <MetricCard title="Autopsy completion rate" subtitle="Completed events with a report filed within 48h — the honesty check on 'institutional memory'">
          <BarChart unit="%" legend={barLegend} data={entities.map((e) => ({ key: e.name, value: entityValue("autopsy_completion", e, [45, 95]), color: barColorFor(e) }))} />
        </MetricCard>

        <MetricCard title="Repeat issues caught by the 60-day pattern flag" subtitle="A leading indicator the system prevents problems, not just logs them" tag="by city">
          <LineChart
            months={months}
            unit=""
            series={activeCities.map((c, i) => ({
              key: String(c.id),
              label: c.name,
              color: seriesColor(i),
              values: entityTrend("pattern_flags", { id: c.id, name: c.name }, months.length, { band: [0, 2], driftBand: [1, 4], noise: 1, min: 0 }).map((v) => Math.round(v)),
            }))}
          />
        </MetricCard>

        <MetricCard
          title="Decision reuse"
          subtitle="New events that viewed a prior autopsy before locking venue/format — a proxy, instrumented as an autopsy-viewed event"
          wide
        >
          <BarChart unit="%" legend={barLegend} data={entities.map((e) => ({ key: e.name, value: entityValue("decision_reuse", e, [20, 60]), color: barColorFor(e) }))} />
        </MetricCard>
      </div>
    );
  }

  // adoption
  const roleSeries = [
    { key: "founder", label: "Founder", band: [1, 1.4] as [number, number], drift: [0, 0.4] as [number, number] },
    { key: "city_lead", label: "City lead", band: [1.5, 3] as [number, number], drift: [0.5, 2] as [number, number] },
    { key: "event_lead", label: "Event lead", band: [2, 6] as [number, number], drift: [2, 6] as [number, number] },
    { key: "volunteer", label: "Volunteer", band: [10, 25] as [number, number], drift: [8, 30] as [number, number] },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
      <MetricCard title="Events created through the OS vs. off-system" subtitle="If coordinators still route around it via WhatsApp or spreadsheets, nothing else matters" tag="by city" wide>
        <LineChart
          months={months}
          unit="%"
          referenceValue={95}
          referenceLabel="Target 95%"
          series={activeCities.map((c, i) => ({
            key: String(c.id),
            label: c.name,
            color: seriesColor(i),
            values: entityTrend("pct_os_created", { id: c.id, name: c.name }, months.length, { band: [15, 45], driftBand: [20, 55], noise: 3, min: 0, max: 100 }),
          }))}
        />
      </MetricCard>

      <MetricCard title="Daily active users by role" subtitle="A system alive only in the founder's head has failed the actual goal" tag="org-wide" wide>
        <LineChart
          months={months}
          unit=""
          series={roleSeries.map((r, i) => ({
            key: r.key,
            label: r.label,
            color: seriesColor(i),
            values: entityTrend("dau_role", { id: r.key, name: r.label }, months.length, { band: r.band, driftBand: r.drift, noise: r.band[1] * 0.15, min: 0 }),
          }))}
        />
      </MetricCard>
    </div>
  );
}
