"use client";

import Link from "next/link";
import { initials } from "@/lib/initials";
import { SeeAllLink } from "@/components/see-all-link";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };

/** "Due in 5d" / "Due today" / "Overdue by 2d" / "No deadline" — mirrors app/page.tsx's dueLabel. */
function dueLabel(iso: string | undefined, today: string): string {
  if (!iso) return "No deadline";
  const diffMs = new Date(`${iso}T00:00:00`).getTime() - new Date(`${today}T00:00:00`).getTime();
  const diffDays = Math.round(diffMs / 86_400_000);
  if (diffDays < 0) return `Overdue by ${Math.abs(diffDays)}d`;
  if (diffDays === 0) return "Due today";
  return `Due in ${diffDays}d`;
}

export function RecentMattersPanel({
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
  return (
    <div className="active-matters-panel-shell" style={{ flex: 1, transform: "translateY(-2%)" }}>
      <div className="row-between" style={{ marginBottom: "var(--space-2)", flexShrink: 0 }}>
        <h2 style={{ fontSize: "var(--font-size-lg)", margin: 0, marginLeft: "var(--space-3)" }}>Recent Matters</h2>
        <SeeAllLink href="/matters" iconOnly icon="chevron" />
      </div>
      {matters.length === 0 ? (
        <div className="text-secondary" style={{ padding: "5px var(--space-3)" }}>No recently viewed Matters yet.</div>
      ) : (
        <div className="active-matters-scroll">
          <div className="stack" style={{ gap: 0 }}>
            {matters.map((matter) => (
              <Link key={matter.id} href={`/matters?selected=${matter.id}`} className="recent-matter-row">
                <span className="matter-avatar matter-avatar-xs">{initials(matter.title)}</span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="active-matter-title">{matter.title}</div>
                  <div className="text-tertiary active-matter-meta">{clientNameById[matter.clientId] ?? "—"}</div>
                </div>
                <div className="text-tertiary active-matter-meta mono" style={{ flexShrink: 0 }}>{dueLabel(nextDeadlineById[matter.id], today)}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
