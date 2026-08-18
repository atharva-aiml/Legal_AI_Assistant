"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { initials } from "@/lib/initials";

type Deadline = { id: string; matterId: string; title: string; dueDate: string; status: "open" | "complete" };

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH_LABELS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function ExpandCalendarIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function dateISO(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}
function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}
function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
/** Monday-first 6-week grid covering the given month. */
function monthGridDays(monthAnchor: Date): Date[] {
  const first = startOfMonth(monthAnchor);
  const firstWeekday = (first.getDay() + 6) % 7; // 0 = Monday
  const gridStart = addDays(first, -firstWeekday);
  return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i));
}

type ByDate = Map<string, Deadline[]>;

/**
 * Dashboard calendar widget: a 7-day strip by default; "View full calendar"
 * and clicking any day both open as an overlay (not a grid reflow) so the
 * single-screen dashboard layout never has to resize around it.
 */
export function DashboardCalendar({ deadlines, matterTitleById }: { deadlines: Deadline[]; matterTitleById: Record<string, string> }) {
  const [overlay, setOverlay] = useState<"none" | "month" | "day">("none");
  const [monthAnchor, setMonthAnchor] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // The week strip's scrollbar is only painted visible while this is true —
  // set on every scroll event, cleared ~500ms after scrolling stops.
  const [stripScrolling, setStripScrolling] = useState(false);
  const stripScrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  function handleStripScroll() {
    setStripScrolling(true);
    if (stripScrollTimeout.current) clearTimeout(stripScrollTimeout.current);
    stripScrollTimeout.current = setTimeout(() => setStripScrolling(false), 500);
  }

  const byDate: ByDate = useMemo(() => {
    const map = new Map<string, Deadline[]>();
    for (const d of deadlines) {
      const list = map.get(d.dueDate) ?? [];
      list.push(d);
      map.set(d.dueDate, list);
    }
    return map;
  }, [deadlines]);

  const today = useMemo(() => new Date(), []);
  const todayISO = dateISO(today);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(today, i)), [today]);

  const monthDeadlineCount = useMemo(() => {
    const y = monthAnchor.getFullYear();
    const m = monthAnchor.getMonth();
    let count = 0;
    for (const d of deadlines) {
      const [dy, dm] = d.dueDate.split("-").map(Number);
      if (dy === y && dm === m + 1) count++;
    }
    return count;
  }, [deadlines, monthAnchor]);

  function openDay(iso: string) {
    setSelectedDate(iso);
    setOverlay("day");
  }

  return (
    <div id="dashboard-calendar" className="card" style={{ display: "flex", flexDirection: "column", padding: "var(--space-3)", alignSelf: "start" }}>
      <div className="row-between" style={{ marginBottom: "var(--space-2)" }}>
        <span className="field-label" style={{ margin: 0 }}>This week</span>
        <button type="button" className="cal-expand-btn" onClick={() => setOverlay("month")} aria-label="View full calendar" title="View full calendar">
          <ExpandCalendarIcon />
        </button>
      </div>

      <div className={`cal-strip${stripScrolling ? " cal-strip-scrolling" : ""}`} onScroll={handleStripScroll}>
        {weekDays.map((d) => {
          const iso = dateISO(d);
          const items = byDate.get(iso) ?? [];
          const isToday = iso === todayISO;
          return (
            <button
              key={iso}
              type="button"
              className={`cal-day-cell${isToday ? " cal-day-today" : ""}`}
              onClick={() => openDay(iso)}
              aria-label={`${d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}${items.length > 0 ? `, ${items.length} deadline(s)` : ""}`}
            >
              <span className="cal-day-label">{WEEKDAY_LABELS[(d.getDay() + 6) % 7]}</span>
              <span className="cal-day-number">{d.getDate()}</span>
              {items.length > 0 && (
                <span className="cal-day-initials" aria-hidden="true">
                  {items.slice(0, 2).map((it) => (
                    <span key={it.id} className="cal-initial-badge">{initials(matterTitleById[it.matterId] ?? "?")}</span>
                  ))}
                  {items.length > 2 && <span className="cal-day-dot" />}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {overlay !== "none" && (
        <div
          className="cal-overlay-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setOverlay("none");
          }}
        >
          <div className="cal-overlay-panel" role="dialog" aria-modal="true" aria-label={overlay === "month" ? "Full calendar" : "Deadlines for the selected day"}>
            {overlay === "month" && (
              <MonthView
                monthAnchor={monthAnchor}
                onPrevMonth={() => setMonthAnchor((d) => addMonths(d, -1))}
                onNextMonth={() => setMonthAnchor((d) => addMonths(d, 1))}
                byDate={byDate}
                matterTitleById={matterTitleById}
                todayISO={todayISO}
                monthDeadlineCount={monthDeadlineCount}
                onSelectDay={openDay}
                onClose={() => setOverlay("none")}
              />
            )}
            {overlay === "day" && selectedDate && (
              <DayView
                dateISOStr={selectedDate}
                items={byDate.get(selectedDate) ?? []}
                matterTitleById={matterTitleById}
                onBack={() => setOverlay("month")}
                onClose={() => setOverlay("none")}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MonthView({
  monthAnchor,
  onPrevMonth,
  onNextMonth,
  byDate,
  matterTitleById,
  todayISO,
  monthDeadlineCount,
  onSelectDay,
  onClose,
}: {
  monthAnchor: Date;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  byDate: ByDate;
  matterTitleById: Record<string, string>;
  todayISO: string;
  monthDeadlineCount: number;
  onSelectDay: (iso: string) => void;
  onClose: () => void;
}) {
  const days = useMemo(() => monthGridDays(monthAnchor), [monthAnchor]);
  const month = monthAnchor.getMonth();
  // Drives which direction the grid slides in from on navigation — purely
  // cosmetic, re-triggered by the `key` change below on every month switch.
  const [navDirection, setNavDirection] = useState<1 | -1>(1);

  return (
    <div className="cal-view-enter">
      <div className="row-between" style={{ marginBottom: "var(--space-4)", flexWrap: "wrap", gap: "var(--space-2)" }}>
        <div className="row" style={{ gap: "var(--space-2)" }}>
          <button type="button" className="btn btn-ghost btn-sm cal-icon-btn" onClick={() => { setNavDirection(-1); onPrevMonth(); }} aria-label="Previous month">‹</button>
          <h2 style={{ fontSize: "var(--font-size-lg)", margin: 0 }}>{MONTH_LABELS[month]} {monthAnchor.getFullYear()}</h2>
          <button type="button" className="btn btn-ghost btn-sm cal-icon-btn" onClick={() => { setNavDirection(1); onNextMonth(); }} aria-label="Next month">›</button>
        </div>
        <div className="row" style={{ gap: "var(--space-3)" }}>
          <span className="text-tertiary text-sm">{monthDeadlineCount} deadline{monthDeadlineCount === 1 ? "" : "s"} this month</span>
          <button type="button" className="btn btn-ghost btn-sm cal-icon-btn cal-close-btn" onClick={onClose} aria-label="Close full calendar" style={{ width: 32, padding: 0 }}>✕</button>
        </div>
      </div>

      <div className="cal-month-grid" style={{ marginBottom: "var(--space-2)" }}>
        {WEEKDAY_LABELS.map((l) => (
          <div key={l} className="text-tertiary text-xs" style={{ textAlign: "center", fontWeight: 600 }}>{l}</div>
        ))}
      </div>
      <div
        key={`${monthAnchor.getFullYear()}-${month}`}
        className={`cal-month-grid ${navDirection === 1 ? "cal-month-slide-next" : "cal-month-slide-prev"}`}
      >
        {days.map((d) => {
          const iso = dateISO(d);
          const items = byDate.get(iso) ?? [];
          const outside = d.getMonth() !== month;
          return (
            <div
              key={iso}
              className={`cal-month-cell${iso === todayISO ? " cal-day-today" : ""}${outside ? " cal-month-outside" : ""}`}
              onClick={() => onSelectDay(iso)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelectDay(iso); }}
            >
              <span className="text-sm">{d.getDate()}</span>
              {items.length > 0 && (
                <span className="cal-day-initials" aria-hidden="true">
                  {items.slice(0, 3).map((it) => (
                    <span key={it.id} className="cal-initial-badge">{initials(matterTitleById[it.matterId] ?? "?")}</span>
                  ))}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DayView({
  dateISOStr,
  items,
  matterTitleById,
  onBack,
  onClose,
}: {
  dateISOStr: string;
  items: Deadline[];
  matterTitleById: Record<string, string>;
  onBack: () => void;
  onClose: () => void;
}) {
  const [y, m, d] = dateISOStr.split("-").map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });

  return (
    <div className="cal-view-enter">
      <div className="row-between" style={{ marginBottom: "var(--space-4)" }}>
        <button type="button" className="btn-link text-sm" onClick={onBack}>← Back to month</button>
        <button type="button" className="btn btn-ghost btn-sm cal-icon-btn cal-close-btn" onClick={onClose} aria-label="Close" style={{ width: 32, padding: 0 }}>✕</button>
      </div>
      <h2 style={{ fontSize: "var(--font-size-lg)", margin: "0 0 var(--space-4)" }}>{label}</h2>

      {items.length === 0 ? (
        <div className="text-secondary">No deadlines on this day.</div>
      ) : (
        <div className="stack">
          {items.map((it) => (
            <Link key={it.id} href={`/matters/${it.matterId}#deadlines`} className="card row cal-day-matter-row" style={{ gap: "var(--space-3)" }}>
              <span className="matter-avatar">{initials(matterTitleById[it.matterId] ?? "?")}</span>
              <div>
                <div style={{ fontWeight: 500 }}>{matterTitleById[it.matterId] ?? "Matter"}</div>
                <div className="text-tertiary text-sm">{it.title}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
