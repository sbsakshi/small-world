import type { ReactNode } from "react";

type Tone = "good" | "warn" | "accent" | "plain";

const TONES: Record<Tone, { bg: string; ink: string }> = {
  good: { bg: "var(--good-bg)", ink: "var(--good-ink)" },
  warn: { bg: "var(--warn-bg)", ink: "var(--warn-ink)" },
  accent: { bg: "var(--accent-tint)", ink: "var(--accent-ink)" },
  plain: { bg: "var(--plain-bg)", ink: "var(--plain-ink)" },
};

export function Tag({ children, tone = "plain" }: { children: ReactNode; tone?: Tone }) {
  const t = TONES[tone];
  return (
    <span
      style={{
        font: "var(--w-bold) 12px/1 var(--font)",
        padding: "6px 12px",
        borderRadius: "var(--r-pill)",
        background: t.bg,
        color: t.ink,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}
