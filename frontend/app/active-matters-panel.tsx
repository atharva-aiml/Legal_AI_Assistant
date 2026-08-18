"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { SortDropdown } from "@/components/sort-dropdown";
import { SeeAllLink } from "@/components/see-all-link";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type SortMode = "default" | "nextDeadline";

/** A dashboard widget, not the full Matters list — same cap the page has always shown. */
const DISPLAY_LIMIT = 8;

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "default", label: "Default order" },
  { value: "nextDeadline", label: "Upcoming deadline" },
];

function FolderIcon() {
  return (
    <svg className="active-matter-folder-icon" width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {/* Bright folder-yellow, not --color-warning-base — this is the reference logo's own color, not a semantic warning indicator. */}
      <path
        d="M3 7.5A2.5 2.5 0 0 1 5.5 5h4.05c.58 0 1.14.22 1.56.63L12.5 7H18.5A2.5 2.5 0 0 1 21 9.5V17a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17V7.5Z"
        fill="#FFC93C"
      />
    </svg>
  );
}

/** Generic "has a client" indicator next to the title — decorative, mirrors the reference image. */
function ClientIcon() {
  return (
    <svg className="active-matter-client-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />
      <circle cx="10" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

/** "Due in 5d" / "Due today" / "Overdue by 2d" / "No deadline" — mirrors app/page.tsx's dueLabel. */
function dueLabel(iso: string | undefined, today: string): string {
  if (!iso) return "No deadline";
  const diffMs = new Date(`${iso}T00:00:00`).getTime() - new Date(`${today}T00:00:00`).getTime();
  const diffDays = Math.round(diffMs / 86_400_000);
  if (diffDays < 0) return `Overdue by ${Math.abs(diffDays)}d`;
  if (diffDays === 0) return "Due today";
  return `Due in ${diffDays}d`;
}

/**
 * Sort mirrors matters-list.tsx's existing two-mode pattern (Default order /
 * Next deadline) — a pure client-side re-order, no extra fetch. Sorting runs
 * over every open Matter, THEN the top 8 are shown, so "Next deadline" surfaces
 * the true 8 most-urgent Matters rather than just re-ordering a static top-8.
 */
export function ActiveMattersPanel({
  matters,
  nextDeadlineById,
  clientNameById,
  today,
}: {
  matters: Matter[];
  nextDeadlineById: Record<string, string>;
  clientNameById: Record<string, string>;
  today: string;
}) {
  const [sortMode, setSortMode] = useState<SortMode>("default");

  const sorted = useMemo(() => {
    if (sortMode !== "nextDeadline") return matters;
    return [...matters].sort((a, b) => {
      const aDate = nextDeadlineById[a.id] ?? "9999-12-31";
      const bDate = nextDeadlineById[b.id] ?? "9999-12-31";
      return aDate.localeCompare(bDate);
    });
  }, [matters, sortMode, nextDeadlineById]);

  const visible = sorted.slice(0, DISPLAY_LIMIT);
  const sortedByDeadline = sortMode === "nextDeadline";

  return (
    <div className="dashboard-panel" style={{ flex: 1 }}>
      <div className="row-between" style={{ marginBottom: "var(--space-2)" }}>
        <h2 style={{ fontSize: "var(--font-size-lg)", margin: 0 }}>Active Matters</h2>
        <div className="row" style={{ gap: "var(--space-3)" }}>
          <SortDropdown
            value={sortMode}
            options={SORT_OPTIONS}
            onChange={setSortMode}
            buttonLabel={sortedByDeadline ? "By deadline" : "Sort"}
            menuLabel="Sort Active Matters"
          />
          <SeeAllLink href="/matters?status=open" />
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="card text-secondary">
          No active matters — <Link href="/matters/new">start one</Link>.
        </div>
      ) : (
        <div className="active-matters-grid">
          {visible.map((matter) => (
            <Link key={matter.id} href={`/matters/${matter.id}`} className="card active-matter-row">
              <div className="row-between">
                <FolderIcon />
                <StatusBadge status={matter.status} />
              </div>
              <div className="row" style={{ gap: "var(--space-1)" }}>
                <span className="active-matter-card-title">{matter.title}</span>
                <ClientIcon />
              </div>
              <div className="active-matter-subtext mono">
                {clientNameById[matter.clientId] ?? "—"} · {dueLabel(nextDeadlineById[matter.id], today)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
