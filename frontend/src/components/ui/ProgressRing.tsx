interface ProgressRingProps {
  value: number;
  total: number;
  size?: number;
  label?: string;
}

export function ProgressRing({ value, total, size = 156, label }: ProgressRingProps) {
  const pct = total > 0 ? value / total : 0;
  const deg = Math.round(pct * 360);
  const inner = Math.round(size * 0.78);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `conic-gradient(var(--accent) ${deg}deg, var(--border-divider) ${deg}deg)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: inner,
          height: inner,
          borderRadius: "50%",
          background: "var(--accent-panel-2)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span style={{ font: `var(--w-black) ${Math.round(size * 0.26)}px/1 var(--font)`, letterSpacing: "-0.03em" }}>
          {value}
        </span>
        {label ? (
          <span style={{ font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-muted)", marginTop: 4 }}>
            {label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
