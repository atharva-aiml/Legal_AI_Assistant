"use client";

import { useEffect, useRef, useState } from "react";
import { SeeAllLink } from "@/components/see-all-link";

type IconName = "matters" | "deadlines" | "notifications";
type Tone = "primary" | "warning" | "info";

const ICONS: Record<IconName, React.ReactNode> = {
  matters: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 3v5a1 1 0 0 0 1 1h5" />
      <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
      <path d="M9 13h6M9 17h6" />
    </svg>
  ),
  deadlines: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="4.5" width="17" height="16" rx="2" />
      <path d="M3.5 9.5h17M8 3v3M16 3v3" />
      <path d="M8.5 13.5h2M8.5 17h2M13.5 13.5h2M13.5 17h2" />
    </svg>
  ),
  notifications: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
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

const COUNT_UP_MS = 600;

/** Animates 0 -> target once on mount/whenever target changes; skips straight to target for non-numbers (the "—" error state) or if the user prefers reduced motion. */
function useCountUp(target: string | number): string | number {
  const [display, setDisplay] = useState<string | number>(typeof target === "number" ? 0 : target);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    if (typeof target !== "number" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(target);
      return;
    }
    const start = performance.now();
    function tick(now: number) {
      const progress = Math.min((now - start) / COUNT_UP_MS, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * (target as number)));
      if (progress < 1) frame.current = requestAnimationFrame(tick);
    }
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [target]);

  return display;
}

/** Dashboard quick-stat tile: value + icon badge on top, label + "See all" link below. */
export function QuickStatCard({
  value,
  label,
  icon,
  tone,
  onSeeAll,
}: {
  value: string | number;
  label: string;
  icon: IconName;
  tone: Tone;
  /** Opens the tile's "see all" popup (Active Matters / Deadlines / Notifications) — not a navigation. */
  onSeeAll: () => void;
}) {
  const { bg, fg } = TONE_TOKENS[tone];
  const displayValue = useCountUp(value);

  return (
    <div className="card stat-card-hover" style={{ padding: "var(--space-3)", alignSelf: "start" }}>
      <div className="stat-card-glow" aria-hidden="true" style={{ color: fg }} />
      <div className="stat-card-border" aria-hidden="true" style={{ color: fg }} />
      <div className="row-between" style={{ alignItems: "flex-start" }}>
        <div className="stat-value" style={{ fontFamily: "var(--font-family-heading)", fontSize: "var(--font-size-xl)", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
          {displayValue}
        </div>
        <div
          aria-hidden="true"
          className="stat-icon-badge"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            borderRadius: "var(--radius-sm)",
            background: bg,
            color: fg,
            flexShrink: 0,
          }}
        >
          {ICONS[icon]}
        </div>
      </div>
      <div className="row-between" style={{ marginTop: "var(--space-1)", gap: "var(--space-3)" }}>
        <span className="text-tertiary text-xs">{label}</span>
        <SeeAllLink onClick={onSeeAll} iconOnly style={{ flexShrink: 0 }} />
      </div>
    </div>
  );
}
