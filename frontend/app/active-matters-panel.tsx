"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { SeeAllLink } from "@/components/see-all-link";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";
import { usePersistedState } from "@/lib/use-persisted-state";

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

function SortTriggerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 7h10M4 12h7M4 17h4" />
      <path d="M17 6v13M17 19l-3-3M17 19l3-3" />
    </svg>
  );
}

function DefaultOrderIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function DeadlineOrderIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

/**
 * "Split button" sort trigger — clicking the icon morphs it into a row of
 * option pills (icon and row occupy the same spot, scale/blur/fade between
 * each other with a bounce-eased transform) instead of a disclosure growing
 * open in-line or a dropdown opening below.
 */
function SortDisclosure({
  sortMode,
  onChange,
}: {
  sortMode: SortMode;
  onChange: (value: SortMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={ref} className={`am-sort-toggle${open ? " am-sort-toggle-open" : ""}`}>
      <button
        type="button"
        className={`am-sort-icon-btn${open ? " am-sort-icon-btn-open" : ""}${sortMode === "nextDeadline" ? " am-sort-icon-btn-active" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Sort Active Matters"
        onClick={() => setOpen(true)}
      >
        <SortTriggerIcon />
        <TooltipBubble label="Sort Active Matters" />
      </button>
      <div className={`am-sort-row${open ? " am-sort-row-open" : ""}`} role="listbox" aria-label="Sort Active Matters">
        <button type="button" className="am-sort-back" onClick={() => setOpen(false)} aria-label="Close">
          <SortTriggerIcon />
          <TooltipBubble label="Close" />
        </button>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            role="option"
            aria-selected={opt.value === sortMode}
            className={`am-sort-pill${opt.value === sortMode ? " am-sort-pill-active" : ""}`}
            onClick={() => {
              onChange(opt.value);
              setOpen(false);
            }}
          >
            {opt.value === "nextDeadline" ? <DeadlineOrderIcon /> : <DefaultOrderIcon />}
            <span>{opt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
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
  const [sortMode, setSortMode] = usePersistedState<SortMode>("dashboard:activeMattersSortMode", "default");

  const sorted = useMemo(() => {
    if (sortMode !== "nextDeadline") return matters;
    return [...matters].sort((a, b) => {
      const aDate = nextDeadlineById[a.id] ?? "9999-12-31";
      const bDate = nextDeadlineById[b.id] ?? "9999-12-31";
      return aDate.localeCompare(bDate);
    });
  }, [matters, sortMode, nextDeadlineById]);

  const visible = sorted.slice(0, DISPLAY_LIMIT);

  return (
    <div className="active-matters-panel-shell" style={{ flex: 1 }}>
      <div className="row-between" style={{ marginBottom: "var(--space-2)", flexShrink: 0 }}>
        <h2 style={{ fontSize: "var(--font-size-lg)", margin: 0 }}>Active Matters</h2>
        <div className="row" style={{ gap: "var(--space-3)" }}>
          <SortDisclosure sortMode={sortMode} onChange={setSortMode} />
          <SeeAllLink href="/matters?status=open" iconOnly icon="chevron" />
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="card text-secondary">
          No active matters — <Link href="/matters/new">start one</Link>.
        </div>
      ) : (
        <div className="active-matters-scroll">
          <div className="active-matters-grid">
            {visible.map((matter) => (
              <Link key={matter.id} href={`/matters?selected=${matter.id}`} className="card active-matter-row">
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
        </div>
      )}
    </div>
  );
}
