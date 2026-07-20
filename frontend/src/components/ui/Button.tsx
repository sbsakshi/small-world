"use client";

import { useState } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "dark" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

const TONES: Record<Variant, { bg: string; ink: string; border: string; hover: string }> = {
  primary: { bg: "var(--accent)", ink: "#fff", border: "transparent", hover: "var(--accent-hover)" },
  dark: { bg: "var(--ink)", ink: "#fff", border: "transparent", hover: "#0c0e13" },
  secondary: { bg: "var(--surface)", ink: "var(--ink)", border: "var(--border-strong)", hover: "var(--surface-sunken)" },
  ghost: { bg: "transparent", ink: "var(--text-muted)", border: "transparent", hover: "var(--border-faint)" },
};

const SIZES: Record<Size, { padding: string; font: string }> = {
  sm: { padding: "8px 14px", font: "13.5px" },
  md: { padding: "11px 18px", font: "15px" },
  lg: { padding: "13px 20px", font: "16px" },
};

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "size"> {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  block?: boolean;
  icon?: ReactNode;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  block = false,
  disabled = false,
  icon,
  ...rest
}: ButtonProps) {
  const t = TONES[variant];
  const s = SIZES[size];
  const [hover, setHover] = useState(false);
  return (
    <button
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        font: `var(--w-bold) ${s.font}/1 var(--font)`,
        display: block ? "flex" : "inline-flex",
        width: block ? "100%" : "auto",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        padding: s.padding,
        borderRadius: "var(--r-lg)",
        background: hover && !disabled ? t.hover : t.bg,
        color: t.ink,
        border: `1px solid ${t.border}`,
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.45 : 1,
        letterSpacing: "-0.01em",
        transition: "background var(--dur) var(--ease)",
      }}
      {...rest}
    >
      {icon ? (
        <span aria-hidden style={{ fontSize: "1.1em" }}>
          {icon}
        </span>
      ) : null}
      {children}
    </button>
  );
}
