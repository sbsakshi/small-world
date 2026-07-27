// Categorical + sequential chart hues — validated for CVD separation and
// contrast against this app's light surfaces (see dataviz skill palette).
// Chrome (surfaces, ink, gridlines) stays on the app's own design tokens;
// only the data-mark hues below are new.

export const CATEGORICAL = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
];

export function seriesColor(i: number): string {
  return CATEGORICAL[i % CATEGORICAL.length];
}

// Single-hue sequential ramp (blue), light -> dark, for nominal magnitude bars.
export const SEQUENTIAL_BLUE = "#3987e5";
export const SEQUENTIAL_BLUE_SOFT = "#9ec5f4";

// Before/after dumbbell: muted "before", accent "after" (one hue, two shades).
export const DUMBBELL_BEFORE = "#9ec5f4";
export const DUMBBELL_AFTER = "#184f95";

export const GRID = "var(--border-divider)";
export const AXIS_TEXT = "var(--text-faint)";
export const VALUE_TEXT = "var(--ink)";
export const MUTED_TEXT = "var(--text-muted)";
