// Deterministic mock data for the founder metrics playground.
// Every number here is generated, not fetched — city/event names are the only
// real data (pulled from the API); the KPI values are seeded pseudo-random so
// they stay stable across re-renders and filter changes within a session.

export interface EntityLite {
  id: number | string;
  name: string;
  cityId?: number;
}

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function rngFor(...parts: (string | number)[]) {
  return mulberry32(hashStr(parts.join("|")));
}

function round1(n: number) {
  return Math.round(n * 10) / 10;
}

export function monthLabels(n: number): string[] {
  const anchor = new Date();
  const out: string[] = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(anchor.getFullYear(), anchor.getMonth() - i, 1);
    out.push(d.toLocaleString("en-US", { month: "short" }));
  }
  return out;
}

/** A single trending series with noise, clamped to [min, max]. */
export function trendSeries(
  seedKey: string,
  months: number,
  opts: { start: number; end: number; noise: number; min?: number; max?: number }
): number[] {
  const rng = rngFor(seedKey, "wobble");
  const { start, end, noise, min = -Infinity, max = Infinity } = opts;
  const out: number[] = [];
  for (let i = 0; i < months; i++) {
    const t = months === 1 ? 1 : i / (months - 1);
    const base = start + (end - start) * t;
    const wobble = (rng() - 0.5) * 2 * noise;
    out.push(round1(Math.min(max, Math.max(min, base + wobble))));
  }
  return out;
}

/** A per-entity trend, banded so each entity lands somewhere plausible & distinct. */
export function entityTrend(
  metric: string,
  entity: EntityLite,
  months: number,
  opts: { band: [number, number]; driftBand: [number, number]; noise: number; min?: number; max?: number }
): number[] {
  const r = rngFor(metric, entity.id, "params");
  const start = opts.band[0] + r() * (opts.band[1] - opts.band[0]);
  const drift = opts.driftBand[0] + r() * (opts.driftBand[1] - opts.driftBand[0]);
  return trendSeries(`${metric}|${entity.id}`, months, {
    start,
    end: start + drift,
    noise: opts.noise,
    min: opts.min,
    max: opts.max,
  });
}

/** A single current value per entity (bar-chart magnitude comparisons). */
export function entityValue(metric: string, entity: EntityLite, band: [number, number]): number {
  const r = rngFor(metric, entity.id, "value");
  return round1(band[0] + r() * (band[1] - band[0]));
}

export interface Segment {
  key: string;
  label: string;
  color: string;
  weight: number;
}

/** Part-to-whole composition per entity — jittered around fixed weights, summing to 100. */
export function entityComposition(
  metric: string,
  entity: EntityLite,
  segments: Segment[]
): Record<string, number> {
  const r = rngFor(metric, entity.id, "mix");
  const raw = segments.map((s) => Math.max(0.02, s.weight + (r() - 0.5) * 0.3 * s.weight));
  const sum = raw.reduce((a, b) => a + b, 0);
  const pct = raw.map((v) => round1((v / sum) * 100));
  // force an exact 100 by folding the rounding remainder into the largest segment
  const diff = round1(100 - pct.reduce((a, b) => a + b, 0));
  const maxIdx = pct.indexOf(Math.max(...pct));
  pct[maxIdx] = round1(pct[maxIdx] + diff);
  const out: Record<string, number> = {};
  segments.forEach((s, i) => (out[s.key] = pct[i]));
  return out;
}

export interface DumbbellDatum {
  key: string;
  before: number;
  after: number;
}

export function entityDumbbell(
  metric: string,
  entity: EntityLite,
  beforeBand: [number, number],
  reductionBand: [number, number]
): DumbbellDatum {
  const r = rngFor(metric, entity.id, "dumbbell");
  const before = Math.round(beforeBand[0] + r() * (beforeBand[1] - beforeBand[0]));
  const reduction = reductionBand[0] + r() * (reductionBand[1] - reductionBand[0]);
  const after = Math.round(before * (1 - reduction));
  return { key: entity.name, before, after };
}

// ---- Mock event names, used when the real API returns too few events ----

const CATEGORY_LABEL: Record<string, string> = {
  art: "Art Night",
  social: "Social Mixer",
  wellness: "Wellness Circle",
  cooking: "Cooking Jam",
};
const CATEGORIES = ["art", "social", "wellness", "cooking"];

export function mockEventsForCity(cityId: number, cityName: string, count: number): EntityLite[] {
  const out: EntityLite[] = [];
  for (let i = 0; i < count; i++) {
    const cat = CATEGORIES[(cityId + i) % CATEGORIES.length];
    out.push({ id: `mock-${cityId}-${i}`, name: `${CATEGORY_LABEL[cat]} #${i + 1}`, cityId });
  }
  return out;
}

export const TIME_RANGES = [
  { key: "30d", label: "Last 30 days", months: 2 },
  { key: "90d", label: "Last 90 days", months: 3 },
  { key: "6mo", label: "Last 6 months", months: 6 },
  { key: "12mo", label: "Last 12 months", months: 12 },
] as const;
export type TimeRangeKey = (typeof TIME_RANGES)[number]["key"];

export const SECTIONS = [
  { key: "outcomes", label: "Business outcomes", note: "the ones that justify the spend" },
  { key: "funnel", label: "Attendee funnel health", note: "booking → check-in" },
  { key: "volunteer", label: "Volunteer ops health", note: "assignment → reliability" },
  { key: "memory", label: "Institutional memory", note: "autopsies & pattern flags" },
  { key: "adoption", label: "System adoption", note: "the metric that kills or saves the engagement" },
] as const;
export type SectionKey = (typeof SECTIONS)[number]["key"];
