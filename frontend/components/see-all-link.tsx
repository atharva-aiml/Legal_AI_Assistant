import Link from "next/link";
import type { CSSProperties } from "react";

function ArrowIcon() {
  return (
    <svg className="see-all-arrow" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

/** The "See all" link shared by Quick Stat Cards, Active Matters, and Recent Matters. */
export function SeeAllLink({ href, style }: { href: string; style?: CSSProperties }) {
  return (
    <Link href={href} className="text-xs link-quiet see-all-link" style={{ display: "inline-flex", alignItems: "center", gap: "2px", ...style }}>
      See all
      <ArrowIcon />
    </Link>
  );
}
