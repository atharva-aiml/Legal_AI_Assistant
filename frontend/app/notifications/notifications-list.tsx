"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

type Notification = { id: string; deadlineId: string; message: string; readAt: string | null; createdAt: string };

// Explicit locale — this component hydrates client-side, and an implicit
// (`undefined`) locale can differ between the server's Node process and the
// browser, producing a real hydration mismatch (caught live during the
// V0.9 visual QA pass, not theoretical).
function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// I-43: local calendar-day comparison, same "compute a YYYY-MM-DD string
// from local time" convention already used for Deadlines (deadlines-list.tsx).
function localDateOnly(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function daysBeforeToday(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function NotificationRow({
  notification,
  matterId,
  onOpen,
}: {
  notification: Notification;
  matterId: string | undefined;
  onOpen: (n: Notification) => void;
}) {
  const isUnread = notification.readAt === null;
  const content = (
    <div className="row-between">
      <div>
        <div style={{ fontWeight: isUnread ? 600 : 400 }}>{notification.message}</div>
        <div className="text-tertiary text-sm">{formatTimestamp(notification.createdAt)}</div>
      </div>
      {isUnread && <span className="badge-dot" style={{ color: "var(--color-info-base)", flexShrink: 0 }} aria-label="Unread" />}
    </div>
  );

  return matterId ? (
    <Link href={`/matters?selected=${matterId}#panel-deadlines`} onClick={() => onOpen(notification)} className="card">
      {content}
    </Link>
  ) : (
    <button
      onClick={() => onOpen(notification)}
      className="card"
      disabled={!isUnread}
      style={{ cursor: isUnread ? "pointer" : "default" }}
    >
      {content}
    </button>
  );
}

export function NotificationsList({ initialNotifications }: { initialNotifications: Notification[] }) {
  const [notifications, setNotifications] = useState(initialNotifications);
  const [matterIdByDeadline, setMatterIdByDeadline] = useState<Record<string, string>>({});
  const [unreadOnly, setUnreadOnly] = useState(false); // I-45
  const [markingAll, setMarkingAll] = useState(false); // I-44

  useEffect(() => {
    let cancelled = false;
    const uniqueDeadlineIds = [...new Set(initialNotifications.map((n) => n.deadlineId))];

    Promise.all(
      uniqueDeadlineIds.map(async (deadlineId) => {
        const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/deadlines/${deadlineId}`, { credentials: "include" });
        if (!res.ok) return null;
        const deadline = await res.json();
        return [deadlineId, deadline.matterId] as const;
      })
    ).then((pairs) => {
      if (cancelled) return;
      const map: Record<string, string> = {};
      for (const pair of pairs) {
        if (pair) map[pair[0]] = pair[1];
      }
      setMatterIdByDeadline(map);
    });

    return () => {
      cancelled = true;
    };
  }, [initialNotifications]);

  async function markRead(notification: Notification) {
    if (notification.readAt) return;
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/notifications/${notification.id}/read`, {
      method: "PATCH",
      credentials: "include",
    });
    if (res.ok) {
      setNotifications((prev) => prev.map((n) => (n.id === notification.id ? { ...n, readAt: new Date().toISOString() } : n)));
    }
  }

  async function markAllRead() {
    setMarkingAll(true);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/notifications/read-all`, {
      method: "PATCH",
      credentials: "include",
    });
    setMarkingAll(false);
    if (res.ok) {
      const now = new Date().toISOString();
      setNotifications((prev) => prev.map((n) => (n.readAt === null ? { ...n, readAt: now } : n)));
    }
  }

  if (notifications.length === 0) {
    return <EmptyState title="No notifications yet" body="Reminders for upcoming and overdue Deadlines will show up here." />;
  }

  const hasUnread = notifications.some((n) => n.readAt === null);
  const sorted = [...notifications].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const visible = unreadOnly ? sorted.filter((n) => n.readAt === null) : sorted;

  // I-43: bucket the already-sorted, already-filtered array — no change to what was fetched.
  const today = localDateOnly(new Date().toISOString());
  const weekCutoff = daysBeforeToday(6);
  const buckets: { label: string; items: Notification[] }[] = [
    { label: "Today", items: [] },
    { label: "This week", items: [] },
    { label: "Earlier", items: [] },
  ];
  for (const n of visible) {
    const d = localDateOnly(n.createdAt);
    if (d === today) buckets[0].items.push(n);
    else if (d >= weekCutoff) buckets[1].items.push(n);
    else buckets[2].items.push(n);
  }

  return (
    <div className="stack-4">
      <div className="row-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
        <label className="row" style={{ gap: "var(--space-2)", cursor: "pointer" }}>
          <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
          Unread only
        </label>
        <Button variant="secondary" onClick={markAllRead} loading={markingAll} disabled={!hasUnread}>
          {markingAll ? "Marking…" : "Mark all as read"}
        </Button>
      </div>

      {visible.length === 0 ? (
        <div className="card text-secondary">No unread notifications.</div>
      ) : (
        buckets.map(
          (bucket) =>
            bucket.items.length > 0 && (
              <div key={bucket.label}>
                <h2 style={{ fontSize: "var(--font-size-lg)", margin: "0 0 var(--space-3)" }}>{bucket.label}</h2>
                <div className="stack">
                  {bucket.items.map((n) => (
                    <NotificationRow key={n.id} notification={n} matterId={matterIdByDeadline[n.deadlineId]} onOpen={markRead} />
                  ))}
                </div>
              </div>
            )
        )
      )}
    </div>
  );
}
