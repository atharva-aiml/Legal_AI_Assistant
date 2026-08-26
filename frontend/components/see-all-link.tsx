import Link from "next/link";
import type { CSSProperties } from "react";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";

function ArrowIcon() {
  return (
    <svg className="see-all-arrow" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

/** Small list glyph — used by the icon-only variant (Quick Stat Cards), hinting "see the full list". */
function ViewAllIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="4.5" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="4.5" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="4.5" cy="18" r="1" fill="currentColor" stroke="none" />
      <path d="M9 6h11M9 12h11M9 18h11" />
    </svg>
  );
}

/** Bare ">" chevron — used by Active Matters / Recent Matters, where a plain directional glyph reads better than the list icon. */
function ChevronIcon() {
  return (
    <svg className="see-all-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

const ICON_ONLY_GLYPHS = { list: ViewAllIcon, chevron: ChevronIcon };

/** The "See all" link shared by Quick Stat Cards, Active Matters, and Recent Matters. */
export function SeeAllLink({
  href,
  onClick,
  style,
  iconOnly,
  icon = "list",
}: {
  /** A destination to navigate to. Omit when passing `onClick` instead (e.g. opening a popup rather than routing). */
  href?: string;
  /** Renders as a <button> instead of a <Link> — used when "see all" opens a popup rather than navigating. */
  onClick?: () => void;
  style?: CSSProperties;
  /** Renders as a bare icon (no "See all" text) — used on Quick Stat Cards, and Active/Recent Matters, where the label would be redundant with the widget's own heading. */
  iconOnly?: boolean;
  /** Which glyph to use when `iconOnly` — "list" (Quick Stat Cards) or "chevron" (Active/Recent Matters). */
  icon?: "list" | "chevron";
}) {
  if (iconOnly) {
    const className = "link-quiet see-all-link see-all-link-icon";
    const Glyph = ICON_ONLY_GLYPHS[icon];
    return onClick ? (
      <button type="button" className={className} aria-label="See all" style={style} onClick={onClick}>
        <Glyph />
        <TooltipBubble label="See all" />
      </button>
    ) : (
      <Link href={href!} className={className} aria-label="See all" style={style}>
        <Glyph />
        <TooltipBubble label="See all" />
      </Link>
    );
  }
  return (
    <Link href={href!} className="text-xs link-quiet see-all-link" style={{ display: "inline-flex", alignItems: "center", gap: "2px", ...style }}>
      See all
      <ArrowIcon />
    </Link>
  );
}
