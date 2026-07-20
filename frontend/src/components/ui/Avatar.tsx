interface AvatarProps {
  initials: string;
  shape?: "circle" | "squircle";
  size?: number;
}

export function Avatar({ initials, shape = "circle", size = 44 }: AvatarProps) {
  return (
    <span
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: shape === "squircle" ? "var(--r-avatar)" : "50%",
        background: shape === "squircle" ? "var(--surface)" : "var(--accent-tint)",
        border: shape === "squircle" ? "1px solid var(--border-strong)" : "none",
        color: "var(--accent-ink)",
        font: `var(--w-bold) ${Math.round(size * 0.34)}px/1 var(--font)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {initials}
    </span>
  );
}
