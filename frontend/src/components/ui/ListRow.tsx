interface ListRowProps {
  name: string;
  sub?: string;
  subDone?: string;
  initials?: string;
  checked?: boolean;
  onToggle?: () => void;
  variant?: "door" | "roster";
}

/**
 * Door-mode / roster row. The whole row is the tap target. Checked rows
 * recede (dim + muted ink). A left color bar marks state on the door variant.
 */
export function ListRow({ name, sub, subDone, initials, checked = false, onToggle, variant = "door" }: ListRowProps) {
  const door = variant === "door";
  return (
    <div
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: door ? 14 : 13,
        padding: door ? "16px 24px" : "13px 22px",
        borderBottom: "1px solid var(--border)",
        background: checked ? "var(--accent-wash-row)" : door ? "var(--surface-sunken)" : "var(--surface)",
        opacity: checked && door ? 0.55 : 1,
        cursor: "pointer",
      }}
    >
      {door ? (
        <span
          style={{ width: 5, alignSelf: "stretch", borderRadius: 5, background: checked ? "var(--accent)" : "transparent" }}
        />
      ) : (
        <span
          style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            flexShrink: 0,
            background: "var(--accent-tint)",
            color: "var(--accent-ink)",
            font: "var(--w-bold) 15px/1 var(--font)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {initials}
        </span>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            font: `${door ? "var(--w-bold) 21px" : "var(--w-semibold) 16.5px"}/1.2 var(--font)`,
            letterSpacing: door ? "-0.02em" : "-0.01em",
            color: checked && door ? "var(--text-body)" : "var(--ink)",
          }}
        >
          {name}
        </div>
        {sub != null ? (
          <div style={{ font: "var(--w-medium) 13px/1.2 var(--font)", color: "var(--text-faint)", marginTop: 2 }}>
            {checked && subDone ? subDone : sub}
          </div>
        ) : null}
      </div>
      {door ? (
        <span style={{ font: "var(--w-black) 22px/1 var(--font)", color: "var(--accent-ink)", flexShrink: 0 }}>
          {checked ? "✓" : ""}
        </span>
      ) : (
        <span
          style={{
            width: 30,
            height: 30,
            borderRadius: "50%",
            flexShrink: 0,
            border: `2px solid ${checked ? "var(--accent)" : "#d3d8e0"}`,
            background: checked ? "var(--accent)" : "transparent",
            color: "#fff",
            font: "var(--w-black) 16px/1 var(--font)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {checked ? "✓" : ""}
        </span>
      )}
    </div>
  );
}
