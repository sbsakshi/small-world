"use client";

import { useState } from "react";
import type { ReactNode } from "react";

interface NavItemProps {
  icon: ReactNode;
  label: string;
  count?: string;
  active?: boolean;
  countTone?: "faint" | "accent" | "alert";
  onClick?: () => void;
}

export function NavItem({ icon, label, count, active = false, countTone = "faint", onClick }: NavItemProps) {
  const [hover, setHover] = useState(false);
  const countColor =
    countTone === "alert" ? "var(--priority-high)" : countTone === "accent" ? "var(--accent-ink)" : "var(--text-faint)";
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 11,
        padding: "10px",
        borderRadius: "var(--r-sm)",
        cursor: "pointer",
        font: `${active ? "var(--w-bold)" : "var(--w-medium)"} 14.5px/1 var(--font)`,
        color: active ? "var(--accent-ink)" : "var(--text-body)",
        background: active ? "var(--accent-tint)" : hover ? "var(--border-faint)" : "transparent",
      }}
    >
      <span aria-hidden style={{ fontSize: 15, width: 18, textAlign: "center" }}>
        {icon}
      </span>
      <span style={{ flex: 1 }}>{label}</span>
      {count != null && count !== "" ? (
        <span style={{ font: "var(--w-bold) 11px/1 var(--font)", color: active ? "var(--accent-ink)" : countColor }}>
          {count}
        </span>
      ) : null}
    </div>
  );
}
