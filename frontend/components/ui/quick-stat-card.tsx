import Link from "next/link";

type IconName = "matters" | "deadlines" | "notifications";
type Tone = "primary" | "warning" | "info";

const ICONS: Record<IconName, React.ReactNode> = {
  matters: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 3v5a1 1 0 0 0 1 1h5" />
      <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
      <path d="M9 13h6M9 17h6" />
    </svg>
  ),
  deadlines: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="4.5" width="17" height="16" rx="2" />
      <path d="M3.5 9.5h17M8 3v3M16 3v3" />
      <path d="M8.5 13.5h2M8.5 17h2M13.5 13.5h2M13.5 17h2" />
    </svg>
  ),
  notifications: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </svg>
  ),
};

const TONE_TOKENS: Record<Tone, { bg: string; fg: string }> = {
  primary: { bg: "var(--color-primary-50)", fg: "var(--color-primary-500)" },
  warning: { bg: "var(--color-warning-bg)", fg: "var(--color-warning-base)" },
  info: { bg: "var(--color-info-bg)", fg: "var(--color-info-base)" },
};

/** Dashboard quick-stat tile: value + icon badge on top, label + "See all" link below. */
export function QuickStatCard({
  value,
  label,
  icon,
  tone,
  seeAllHref,
}: {
  value: string | number;
  label: string;
  icon: IconName;
  tone: Tone;
  seeAllHref: string;
}) {
  const { bg, fg } = TONE_TOKENS[tone];

  return (
    <div className="card">
      <div className="row-between" style={{ alignItems: "flex-start" }}>
        <div style={{ fontFamily: "var(--font-family-heading)", fontSize: "var(--font-size-2xl)", fontWeight: 600 }}>
          {value}
        </div>
        <div
          aria-hidden="true"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 40,
            height: 40,
            borderRadius: "var(--radius-md)",
            background: bg,
            color: fg,
            flexShrink: 0,
          }}
        >
          {ICONS[icon]}
        </div>
      </div>
      <div className="row-between" style={{ marginTop: "var(--space-2)", gap: "var(--space-3)" }}>
        <span className="text-tertiary text-sm">{label}</span>
        <Link href={seeAllHref} className="text-sm" style={{ fontWeight: "var(--font-weight-medium)", flexShrink: 0 }}>
          See all
        </Link>
      </div>
    </div>
  );
}
