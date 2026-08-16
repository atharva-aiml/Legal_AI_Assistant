"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
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

export function NotificationsList({ initialNotifications }: { initialNotifications: Notification[] }) {
  const [notifications, setNotifications] = useState(initialNotifications);
  const [matterIdByDeadline, setMatterIdByDeadline] = useState<Record<string, string>>({});

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

  if (notifications.length === 0) {
    return <EmptyState title="No notifications yet" body="Reminders for upcoming and overdue Deadlines will show up here." />;
  }

  const sorted = [...notifications].sort((a, b) => b.createdAt.localeCompare(a.createdAt));

  return (
    <div className="stack">
      {sorted.map((n) => {
        const matterId = matterIdByDeadline[n.deadlineId];
        const isUnread = n.readAt === null;

        const content = (
          <div className="row-between">
            <div>
              <div style={{ fontWeight: isUnread ? 600 : 400 }}>{n.message}</div>
              <div className="text-tertiary text-sm">{formatTimestamp(n.createdAt)}</div>
            </div>
            {isUnread && <span className="badge-dot" style={{ color: "var(--color-info-base)", flexShrink: 0 }} aria-label="Unread" />}
          </div>
        );

        return matterId ? (
          <Link key={n.id} href={`/matters/${matterId}#deadlines`} onClick={() => markRead(n)} className="card">
            {content}
          </Link>
        ) : (
          <button
            key={n.id}
            onClick={() => markRead(n)}
            className="card"
            disabled={!isUnread}
            style={{ cursor: isUnread ? "pointer" : "default" }}
          >
            {content}
          </button>
        );
      })}
    </div>
  );
}
