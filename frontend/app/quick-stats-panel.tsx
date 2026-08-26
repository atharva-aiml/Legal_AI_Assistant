"use client";

import { useState } from "react";
import Link from "next/link";
import { initials } from "@/lib/initials";
import { StatusBadge } from "@/components/status-badge";
import { QuickStatCard } from "@/components/ui/quick-stat-card";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Deadline = { id: string; matterId: string; title: string; dueDate: string; status: "open" | "complete" };
type NotificationItem = { id: string; deadlineId: string; message: string; readAt: string | null; createdAt: string };
type PopupKind = "matters" | "deadlines" | "notifications";

type StatTile = {
  label: string;
  value: number | string;
  ok: boolean;
  icon: "matters" | "deadlines" | "notifications";
  tone: "primary" | "warning" | "info";
  popup: PopupKind;
};

/** "Due in 5d" / "Due today" / "Overdue by 2d" / "No deadline" — mirrors app/page.tsx's dueLabel. */
function dueLabel(iso: string | undefined, today: string): string {
  if (!iso) return "No deadline";
  const diffMs = new Date(`${iso}T00:00:00`).getTime() - new Date(`${today}T00:00:00`).getTime();
  const diffDays = Math.round(diffMs / 86_400_000);
  if (diffDays < 0) return `Overdue by ${Math.abs(diffDays)}d`;
  if (diffDays === 0) return "Due today";
  return `Due in ${diffDays}d`;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

const POPUP_TITLES: Record<PopupKind, string> = {
  matters: "Open Matters",
  deadlines: "Deadlines this week",
  notifications: "Unread notifications",
};

/**
 * Quick Stat Cards + the "see all" popup each one opens — reuses the
 * calendar's own overlay chrome (.cal-overlay-backdrop/.cal-overlay-panel)
 * so it reads as the same interaction, not a new one-off dialog.
 */
export function QuickStatsPanel({
  statTiles,
  activeMatters,
  weekDeadlines,
  unreadNotifications,
  clientNameById,
  matterTitleById,
  today,
}: {
  statTiles: StatTile[];
  activeMatters: Matter[];
  weekDeadlines: Deadline[];
  unreadNotifications: NotificationItem[];
  clientNameById: Record<string, string>;
  matterTitleById: Record<string, string>;
  today: string;
}) {
  const [popup, setPopup] = useState<PopupKind | "none">("none");

  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-3)" }}>
        {statTiles.map((tile) => (
          <QuickStatCard
            key={tile.label}
            value={tile.ok ? tile.value : "—"}
            label={tile.label}
            icon={tile.icon}
            tone={tile.tone}
            onSeeAll={() => setPopup(tile.popup)}
          />
        ))}
      </div>

      {popup !== "none" && (
        <div
          className="cal-overlay-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setPopup("none");
          }}
        >
          <div className="cal-overlay-panel cal-view-enter" role="dialog" aria-modal="true" aria-label={POPUP_TITLES[popup]}>
            <div className="row-between" style={{ marginBottom: "var(--space-4)" }}>
              <h2 style={{ fontSize: "var(--font-size-lg)", margin: 0 }}>{POPUP_TITLES[popup]}</h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm cal-icon-btn cal-close-btn"
                onClick={() => setPopup("none")}
                aria-label="Close"
                style={{ width: 32, padding: 0 }}
              >
                ✕
                <TooltipBubble label="Close" />
              </button>
            </div>

            {popup === "matters" && (
              <div className="stack">
                {activeMatters.length === 0 ? (
                  <div className="text-secondary">No active matters.</div>
                ) : (
                  activeMatters.map((m) => (
                    <Link
                      key={m.id}
                      href={`/matters?selected=${m.id}`}
                      className="card cal-day-matter-row"
                      style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", justifyContent: "space-between" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", minWidth: 0 }}>
                        <span className="matter-avatar">{initials(m.title)}</span>
                        <div style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          <div style={{ fontWeight: 500 }}>{m.title}</div>
                          <div className="text-tertiary text-sm">{clientNameById[m.clientId] ?? "—"}</div>
                        </div>
                      </div>
                      <StatusBadge status={m.status} />
                    </Link>
                  ))
                )}
              </div>
            )}

            {popup === "deadlines" && (
              <div className="stack">
                {weekDeadlines.length === 0 ? (
                  <div className="text-secondary">No deadlines this week.</div>
                ) : (
                  weekDeadlines.map((d) => (
                    <Link
                      key={d.id}
                      href={`/matters?selected=${d.matterId}#panel-deadlines`}
                      className="card cal-day-matter-row"
                      style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", justifyContent: "space-between" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", minWidth: 0 }}>
                        <span className="matter-avatar">{initials(matterTitleById[d.matterId] ?? "?")}</span>
                        <div style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          <div style={{ fontWeight: 500 }}>{matterTitleById[d.matterId] ?? "Matter"}</div>
                          <div className="text-tertiary text-sm">{d.title}</div>
                        </div>
                      </div>
                      <span className="text-tertiary text-xs mono" style={{ flexShrink: 0 }}>{dueLabel(d.dueDate, today)}</span>
                    </Link>
                  ))
                )}
              </div>
            )}

            {popup === "notifications" && (
              <div className="stack">
                {unreadNotifications.length === 0 ? (
                  <div className="text-secondary">No unread notifications.</div>
                ) : (
                  unreadNotifications.map((n) => (
                    <Link key={n.id} href="/notifications" className="card">
                      <div style={{ fontWeight: 600 }}>{n.message}</div>
                      <div className="text-tertiary text-sm">{formatTimestamp(n.createdAt)}</div>
                    </Link>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
