import type { ReactNode } from "react";

type Tone = "open" | "decided" | "staff";

const TONES: Record<Tone, { bg: string; ink: string }> = {
  open: { bg: "var(--accent-tint)", ink: "var(--accent-ink)" },
  decided: { bg: "var(--good-bg)", ink: "var(--good-ink)" },
  staff: { bg: "var(--plain-bg)", ink: "var(--plain-ink)" },
};

export function Badge({ children, tone = "open" }: { children: ReactNode; tone?: Tone }) {
  const t = TONES[tone];
  return (
    <span
      style={{
        font: "var(--w-black) 11px/1 var(--font)",
        letterSpacing: "0.02em",
        textTransform: "uppercase",
        padding: "3px 8px",
        borderRadius: "var(--r-chip)",
        background: t.bg,
        color: t.ink,
      }}
    >
      {children}
    </span>
  );
}
