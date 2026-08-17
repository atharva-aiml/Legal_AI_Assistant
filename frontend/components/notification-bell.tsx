"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";

type Notification = { id: string; readAt: string | null };

const POLL_INTERVAL_MS = 60000;

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/notifications`, { credentials: "include" });
      if (!cancelled && res.ok) {
        const { notifications }: { notifications: Notification[] } = await res.json();
        setUnreadCount(notifications.filter((n) => n.readAt === null).length);
      }
    }

    load();
    const timer = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <Link
      href="/notifications"
      aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 36,
        height: 36,
        borderRadius: "var(--radius-md)",
        color: "var(--color-neutral-700)",
      }}
      className="nav-item"
    >
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 2.5c-3.2 0-5.5 2.4-5.5 5.8v3.2c0 .6-.2 1.4-.6 2l-1 1.6c-.6 1-.1 2.4 1.1 2.7 3.9 1 8.1 1 12 0 1.2-.3 1.7-1.7 1.1-2.7l-1-1.6c-.4-.6-.6-1.4-.6-2V8.3c0-3.4-2.3-5.8-5.5-5.8Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M9.5 20.5a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {unreadCount !== null && unreadCount > 0 && (
        <span
          style={{
            position: "absolute",
            top: 2,
            right: 2,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: 16,
            height: 16,
            padding: "0 3px",
            borderRadius: "var(--radius-full)",
            background: "var(--color-error-base)",
            color: "var(--color-text-on-brand)",
            fontSize: "10px",
            fontWeight: 600,
            border: "1.5px solid var(--color-bg-surface)",
          }}
        >
          {unreadCount > 9 ? "9+" : unreadCount}
        </span>
      )}
    </Link>
  );
}
